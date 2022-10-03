from bot.handlers.chat.handlers import recive_calback, recive_command, recive_message
from bot.handlers.utils.info import extract_user_data_from_update
from telegram import Update
from telegram.ext import CallbackContext
import redis 
from abridge_bot.settings import REDIS_URL
from bot.models import User
from vpn.models import Order, Peer
from proxy.models import ProxyOrder
from bot.handlers.utils import utils
import json

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
        choices_kw = json.loads(r.get(f'{user_id}_choices')) 
        k1 = 'выбратьстрану'; k2 = 'сменитьтариф'
        order, created, changed = Order.create_or_change(
            user_id = user_id, 
            country = choices_kw.get(k1, default='DE'),
            tariff_name = choices_kw.get(k2, default='Пробный'), 
        )
        if order:
            if created and not changed:
                qr_photo = order.peers.all().first().get_qr()
            elif not created and changed:
                msg_text = 'Тариф изменен'
            else:
                 msg_text = 'У вас прежний тарииф'
        else:
            msg_text = 'Не хватает средств'   
        r.delete(f'{user_id}_choices')

    else:
        msg_text = 'У вас есть уже VPN'
    
    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    if qr_photo:
        photos = next_state.get("photos", [])
        next_state['photos'] = [qr_photo] + photos
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)

def buy_traffic(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    r = redis.from_url(REDIS_URL, decode_responses=True)
    if not r.get(f'{user_id}_vpn_status'):
        msg_text = 'У вас нет VPN'
    else:
        choices_kw = json.loads(r.get(f'{user_id}_choices')) 
        k1 = 'купитьгигобайты'
        gb_amount = int(choices_kw.get(k1)[:-2]), 
        msg_text = Order.add_traffic(user_id=user_id, gb_amount=gb_amount)
        r.delete(f'{user_id}_choices')
    
    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)
        

def delete_peer(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    r = redis.from_url(REDIS_URL, decode_responses=True)
    if not r.get(f'{user_id}_vpn_status'):
        msg_text = 'У вас нет VPN'
    else:
        choices_kw = json.loads(r.get(f'{user_id}_choices')) 
        k1 = 'моиподключения'
        peer_id = int(choices_kw.get(k1).split(' - ')[-1])
        Peer.objects.get(pk=peer_id).delete()
        msg_text = 'Подключение удалено'
        r.delete(f'{user_id}_choices')

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)


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
    r = redis.from_url(REDIS_URL, decode_responses=True)
    choices_kw = json.loads(r.get(f'{user_id}_choices')) 
    msg_text = ProxyOrder.create_new_order(
        user_id=user_id, 
        version=choices_kw.get('Выбрать версию ip'.lower().strip()),
        country=choices_kw.get( 'Выбрать страну прокси'.lower().strip()),
        ptype=choices_kw.get('Выбрать тип прокси'.lower().strip()),
        count=choices_kw.get('Выбрать кол-во прокси'.lower().strip()),
        priod=choices_kw.get('Выбрать срок прокси'.lower().strip())
    )
    r.delete(f'{user_id}_choices')
    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)
    _send_msg_and_log(user_id, msg_text, prev_state, next_state, prev_message_id, context)
