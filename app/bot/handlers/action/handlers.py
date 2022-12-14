from bot.models import Message
from bot.handlers.chat.handlers import recive_calback
from bot.handlers.utils.info import extract_user_data_from_update
from telegram import Update
from telegram.ext import CallbackContext
from bot.models import User
from vpn.models import VpnOrder, Peer
from proxy.dispatcher import get_markup_countries
from bot.handlers.utils import utils
from payment.models import Payment
from bot.handlers.action import static_text
from proxy import tasks
import re


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

    info, created = VpnOrder.get_user_info(user_id)
    k1 = 'выбратьстрану'; k2 = 'сменитьтариф'
    country, tariff_name = User.pop_choices(user_id, k1, k2)
    if country and created:
        tariff_name = info['tariff_name']
    elif created or info['tariff_name'] == 'Пробный':
        country, tariff_name = info['country'], info['tariff_name']

    country = Message.encode_msg_name(country)
    order, msg_text = VpnOrder.create_or_change(
        user_id=user_id,
        country=country, tariff_name=tariff_name
    )
    update.callback_query.answer(msg_text)
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    if order:
        qr_photo = order.peers.first().get_qr()
        photos = next_state.get("photos", [])
        next_state['photos'] = [qr_photo] + photos
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def buy_traffic(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    args = User.pop_choices(user_id, 'купитьгигобайты')
    gb_amount = int(re.findall('\d+', args[0])[0])
    msg_text = VpnOrder.add_traffic(user_id=user_id, gb_amount=gb_amount)
    update.callback_query.answer(msg_text)
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def delete_peer(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    info = VpnOrder.get_user_info(user_id)
    if info in None:
        msg_text = 'У вас нет VPN'
    else:
        peer_id = User.pop_choices(user_id, 'моиподключения')
        peer_id = int(peer_id[0].split(' - ')[-1])
        Peer.objects.get(pk=peer_id).delete()
        msg_text = 'Подключение удалено'

    update.callback_query.answer(msg_text)
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def cant_scan_qr(update: Update, context: CallbackContext) -> None:
    recive_calback(update, context)
    user_id = extract_user_data_from_update(update)["user_id"]
    order = VpnOrder.objects.get(user__user_id=user_id)
    for peer in order.peers.all():
        context.bot.send_document(
            user_id,
            document=peer.get_conf(),
            filename=f'{peer.server.country.upper()}-bridge.conf',
            caption='Высылаю файл для подключения. Выбирете "импорт тунеля из файла", чтобы подключить данный тунель!'
        )


def buy_proxy(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    tasks.buy_proxy_task.delay(user_id=user_id)
    msg_text = update.callback_query.data
    update.callback_query.answer('Запрос принят')
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def show_countrys(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    update.callback_query.answer()
    msg_text = update.callback_query.data
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    args = User.get_choices(user_id, static_text.proxy_version_name.lower().replace(' ', ''))
    next_state['markup'] = get_markup_countries(version=args[0])
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def topup(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.callback_query.data
    price = int(re.findall('\d+', msg_text)[0])
    cnfrm_url = Payment.yoo_make_payment(price=price, user_id=user_id)
    update.callback_query.answer('Платеж сформирован')
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    next_state['markup'] = [[(c[0], cnfrm_url) for c in r]for r in next_state['markup']]
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def prolong_command(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    order_ids = re.findall('\d+', update.message.text)
    if len(order_ids) > 1:
        context.user_data['period'] = int(order_ids.pop(-1))
        context.user_data['order_ids'] = order_ids
        msg_text = 'Запрос продлить прокси'
    else:
        msg_text = 'Ошибка ввода'
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def prolong_command_run(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    period = context.user_data.pop('period')
    order_ids = context.user_data.pop('order_ids')
    tasks.prolong_orders_task.delay(order_ids, period)
    msg_text = 'Запрос отправлен'
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def check_command(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    order_ids = re.findall('\d+', update.message.text)
    if len(order_ids) > 0:
        tasks.ckeck_orders_task.delay(order_ids)
        msg_text = 'Запрос отправлен'
    else:
        msg_text = 'Ошибка ввода'
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


def change_command(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    order_ids = re.findall('\d+', update.message.text)
    if len(order_ids) > 0:
        tasks.change_order_task.delay(order_ids)
        msg_text = 'Запрос отправлен'
    else:
        msg_text = 'Ошибка ввода'
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)

def invite_friends(update: Update, context: CallbackContext) -> None:
    recive_calback(update, context)
    msg_text = 'Сообщение для друга'
    user_id = extract_user_data_from_update(update)["user_id"]
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)