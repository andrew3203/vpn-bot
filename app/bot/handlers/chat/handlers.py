import datetime
from email import message
import logging
import re
from django.utils import timezone

from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot.models import User, Poll
from bot.handlers.utils import utils
from bot.handlers.utils.info import extract_user_data_from_update
from bot.tasks import send_delay_message, check_deep_link
from wg_vpn_bot.settings import PROGREV_NAMES


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
            


def command_balance(update: Update, context: CallbackContext) -> None: # TODO
    u, _ = User.get_user_and_created(update, context)
    user_balance = utils.get_user_info(u.user_id, u.deep_link)
    u.update_info(user_balance)

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


def recive_message(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)["user_id"]
    msg_text = update.message.text

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
        msg_text = answer_text.lower().replace(' ', '')

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
