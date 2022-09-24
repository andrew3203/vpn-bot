import re
import telegram
from telegram import Update
from telegram.ext import CallbackContext
from bot.handlers.chat.handlers import recive_command

from .manage_data import CONFIRM_DECLINE_BROADCAST, CONFIRM_BROADCAST
from .keyboards import keyboard_confirm_decline_broadcasting
from .static_text import *
from bot.models import User
from bot.tasks import broadcast_message
from bot.handlers.broadcast_message.utils import _send_message

from wg_vpn_bot.settings import TELEGRAM_SUPPORT_CHAT


def broadcast_command_with_message(update: Update, context: CallbackContext):
    """ Type /broadcast <some_text>. Then check your message in HTML format and broadcast to users."""
    u = User.get_user(update, context)

    if not u.is_admin:
        update.message.reply_text(
            text=broadcast_no_access,
        )
    else:
        if update.message.photo:
            text = update.message.caption
        else:
            text = update.message.text

        if text == broadcast_command:
            # user typed only command without text for the message.
            update.message.reply_text(
                text=broadcast_wrong_format,
                parse_mode=telegram.ParseMode.HTML,
            )
            return

        text = f"{text.replace(f'{broadcast_command} ', '')}"
        markup = keyboard_confirm_decline_broadcasting()

        try:
            update.message.reply_text(
                text=text,
                parse_mode=telegram.ParseMode.HTML,
                reply_markup=markup,
            )
        except telegram.error.BadRequest as e:
            update.message.reply_text(
                text=error_with_html.format(reason=e),
                parse_mode=telegram.ParseMode.HTML,
            )


def broadcast_decision_handler(update: Update, context: CallbackContext) -> None:
    # callback_data: CONFIRM_DECLINE_BROADCAST variable from manage_data.py
    """ Entered /broadcast <some_text>.
        Shows text in HTML style with two buttons:
        Confirm and Decline
    """
    broadcast_decision = update.callback_query.data[len(CONFIRM_DECLINE_BROADCAST):]

    entities_for_celery = update.callback_query.message.to_dict().get('entities')
    entities, text = update.callback_query.message.entities, update.callback_query.message.text

    if broadcast_decision == CONFIRM_BROADCAST:
        admin_text = message_is_sent
        user_ids = list(User.objects.all().values_list('user_id', flat=True))

        # send in async mode via celery
        broadcast_message.delay(
            user_ids=user_ids,
            text=text,
            entities=entities_for_celery,
        )
    else:
        context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=declined_message_broadcasting,
        )
        admin_text = text

    context.bot.edit_message_text(
        text=admin_text,
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        entities=None if broadcast_decision == CONFIRM_BROADCAST else entities,
    )


def support_command_with_message(update: Update, context: CallbackContext):
    if update.message.text == support_command:
        recive_command(update, context)
        #update.effective_chat.send_message(
        #    text=update.message.chat_id
        #)
        return

    u = User.get_user(update, context)
    li = f'<a href="http://bot.wg_vpn_bot.ru/admin/bot/user/{u.user_id}/change/">{u.first_name} {u.last_name} ({u.user_id})</a>\n{u.company}\n{u.phone}\n{u.owner}'
    text = f"{update.message.text.replace(f'{support_command} ', '')}\n\n{li}"
    context.bot.send_message(
        chat_id=int(TELEGRAM_SUPPORT_CHAT),
        text=text,
        parse_mode=telegram.ParseMode.HTML,
        disable_web_page_preview=True
    )

    update.effective_chat.send_message(
        text='Ваше сообщение отправлено',
    )
