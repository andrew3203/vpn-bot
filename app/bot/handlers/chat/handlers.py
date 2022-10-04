import datetime
import re

from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot.models import User, Poll
from proxy.models import Proxy
from bot.handlers.utils import utils
from bot.handlers.utils.info import extract_user_data_from_update
from bot.tasks import send_delay_message, check_deep_link
from abridge_bot.settings import PROGREV_NAMES, TELEGRAM_SUPPORT_CHAT



def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)
    if created and u.deep_link:
        utils.send_logs_message(
            msg_text='Новый пользователь!!', 
            user_keywords=u.get_keywords(), 
            prev_state=None
        )
        msg_dict = dict(PROGREV_NAMES)
        now = timezone.now()
        send_delay_message.apply_async(
            kwargs={'user_id': u.user_id, 'msg_name': msg_dict['progrev_1']}, 
            eta=now+datetime.timedelta(days=1)
        )

        check_deep_link.delay(user_id=u.user_id,  deep_link=u.deep_link)
    
    recive_command(update, context)
            

def command_account(update: Update, context: CallbackContext) -> None: # TODO
    u, _ = User.get_user_and_created(update, context)
    update_proxy_info = Proxy.update_info(u.user_id)
    u.update_info(update_proxy_info)

    recive_command(update, context)


def recive_command(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.message.text.replace('/', '') 
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

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


def _forward_to_support(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    li = f'<a href="https://bridge-vpn.store/admin/bot/user/{u.user_id}/change/">' \
        f'{u.first_name} ({u.user_id})</a>\n' \
        f'{u.balance}\n{u.cashback_balance}'

    text = f"{update.message.text}\n\n{li}"
    context.bot.send_message(
        chat_id=int(TELEGRAM_SUPPORT_CHAT),
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    

def recive_message(update: Update, context: CallbackContext) -> None:
    if context.user_data and context.user_data.pop('ask_support', False):
        _forward_to_support(update, context)
        msg_text = 'Отправил вопрос в поддержку'
    else:
        msg_text = update.message.text

    user_id = extract_user_data_from_update(update)["user_id"]
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

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


def recive_calback(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.callback_query.data

    update.callback_query.answer()
    prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, msg_text)

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


def receive_poll_answer(update: Update, context) -> None:
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    if len(answer.option_ids) > 0:
        answer_text = answered_poll['questions'][answer.option_ids[0]]
        context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
        Poll.update_poll(answered_poll["poll_id"], answer=answer_text)
        user_id = answered_poll['chat_id']

        prev_state, next_state, prev_message_id = User.get_prev_next_states(user_id, answer_text)

        prev_msg_id = utils.send_message(
            prev_state=prev_state,
            next_state=next_state,
            context=context,
            user_id=user_id,
            prev_message_id=prev_message_id
        )
        User.set_message_id(user_id, prev_msg_id)
        utils.send_logs_message(
            msg_text=answer_text, 
            user_keywords=next_state['user_keywords'], 
            prev_state=prev_state
        )


def command_support(update: Update, context: CallbackContext) -> None:
    context.user_data['ask_support'] = True
    recive_command(update, context)


def forward_from_support(update: Update, context: CallbackContext) -> None:
    replay_msg = update.message.reply_to_message
    text = replay_msg.text

    regex = "\(\d+\)"
    match = re.findall(regex, text)
    chat_id = int(re.sub('\(|\)', '', match[0]))

    context.bot.send_message(
        chat_id=int(chat_id),
        text=f'Ответ от поддержки:\n\n{update.message.text}',
        parse_mode=ParseMode.HTML,
    )
    update.effective_chat.send_message(
        text='Cообщение отправлено',
    )

