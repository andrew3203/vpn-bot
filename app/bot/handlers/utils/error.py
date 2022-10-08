import logging
import traceback
import html

import telegram
from telegram import Update
from telegram.ext import CallbackContext

from abridge_bot.settings import TELEGRAM_LOGS_CHAT_ID
from bot.models import User
from bot.handlers.utils import utils


def send_stacktrace_to_tg_chat(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    logging.error("Exception while handling an update:", exc_info=context.error)
    
    next_state, prev_message_id = User.get_broadcast_next_states(u.user_id, message_id=36)
    message_id = utils.send_broadcast_message(
        next_state, u.user_id, prev_message_id
    )
    User.set_message_id(u.user_id, message_id)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    message = (
        f'Возникло исключение при обработке обновления\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )
    admin_message = f"⚠️⚠️⚠️ for {u.tg_str}:\n{message}"[:4090]
    if TELEGRAM_LOGS_CHAT_ID:
        context.bot.send_message(
            chat_id=TELEGRAM_LOGS_CHAT_ID,
            text=admin_message,
            parse_mode=telegram.ParseMode.HTML,
        )
    else:
        logging.error(admin_message)
