import imp
from bot.handlers.chat.handlers import recive_calback
from bot.handlers.utils.info import extract_user_data_from_update
from telegram import Update
from telegram.ext import CallbackContext
import redis
from abridge_bot.settings import REDIS_URL
from bot.models import User
from vpn.models import Order, Peer
from proxy.models import ProxyOrder
from proxy.dispatcher import get_markup_countries
from bot.handlers.utils import utils
from payment.models import Payment
from bot.handlers.action import static_text


def _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context):
    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        context=context,
        user_id=user_id,
        prev_message_id=prev_message_id
    )
    User.set_message_id(user_id, prev_msg_id)
    utils.send_logs_message(
        msg_text=msg_text,
        user_keywords=next_state['user_keywords'],
        prev_state=prev_state
    )


def create_new_vpn_order(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    qr_photo = None

    r = redis.from_url(REDIS_URL, decode_responses=True)
    if not r.get(f'{user_id}_vpn_status'):
        msg_text = update.callback_query.data
        k1 = 'выбратьстрану'
        k2 = 'сменитьтариф'
        country, tariff_name = User.pop_choices(user_id, k1, k2)
        order, created, changed = Order.create_or_change(
            user_id=user_id,
            country=country or 'DE',
            tariff_name=tariff_name or 'Пробный',
        )
        if order:
            if created and not changed:
                qr_photo = order.peers.all().first().get_qr()
                r.set(f'{user_id}_vpn_status', value=order.tariff.tariff_key)
            elif not created and changed:
                msg_text = 'Тариф изменен'
                r.set(f'{user_id}_vpn_status', value=order.tariff.tariff_key)
            else:
                msg_text = 'У вас прежний тарииф'
        else:
            msg_text = 'Не хватает средств'

    else:
        msg_text = 'У вас есть уже VPN'

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(
        user_id, msg_text)
    if qr_photo:
        photos = next_state.get("photos", [])
        next_state['photos'] = [qr_photo] + photos
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)


def buy_traffic(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    r = redis.from_url(REDIS_URL, decode_responses=True)
    if not r.get(f'{user_id}_vpn_status'):
        msg_text = 'У вас нет VPN'
    else:
        gb_amount = User.pop_choices(user_id, 'купитьгигобайты')
        gb_amount = int(gb_amount[0][:-2]),
        msg_text = Order.add_traffic(user_id=user_id, gb_amount=gb_amount)

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(
        user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)


def delete_peer(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    r = redis.from_url(REDIS_URL, decode_responses=True)
    if not r.get(f'{user_id}_vpn_status'):
        msg_text = 'У вас нет VPN'
    else:
        peer_id = User.pop_choices(user_id, 'моиподключения')
        peer_id = int(peer_id[0].split(' - ')[-1])
        Peer.objects.get(pk=peer_id).delete()
        msg_text = 'Подключение удалено'

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(
        user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)


def cant_scan_qr(update: Update, context: CallbackContext) -> None:
    recive_calback(update, context)
    user_id = extract_user_data_from_update(update)["user_id"]
    order = Order.objects.get(user__user_id=user_id)
    for peer in order.peers.all():
        context.bot.send_document(
            user_id,
            document=peer.get_conf(),
            caption=str(peer)
        )


def buy_proxy(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    args = list(map(lambda x: x.lower().strip(),
                static_text.proxy_choose_msg_names))
    args = User.pop_choices(user_id, *args)
    kwargs = dict(list(zip(static_text.proxy_order_fields, args)))
    msg_text = ProxyOrder.create_new_order(user_id=user_id, **kwargs)
    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)


def show_countrys(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    update.callback_query.answer()
    msg_text = update.callback_query.data
    prev_state, next_state, prev_message_id = User.get_prev_next_states(
        user_id, msg_text)
    next_state['markup'] = get_markup_countries()
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)


def topup(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.callback_query.data
    cnfrm_url = Payment.yoo_make_payment(
        price=int(msg_text[:-1]), user_id=user_id)
    update.callback_query.answer()
    msg_text = update.callback_query.data
    prev_state, next_state, prev_message_id = User.get_prev_next_states(
        user_id, msg_text)
    next_state['markup'] = [[(c[0], cnfrm_url) for c in r]
                            for r in next_state['markup']]
    _send_msg_and_log(user_id, msg_text, prev_state,
                      next_state, prev_message_id, context)
