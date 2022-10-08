"""
    Telegram event handlers
"""
import logging
import sys
from typing import Dict

import telegram.error
from abridge_bot.celery import app  # event processing in async mode
from abridge_bot.settings import (
    DEBUG, 
    TELEGRAM_SUPPORT_CHAT, TELEGRAM_TOKEN, 
)
from telegram import Bot, BotCommand, Update
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, Dispatcher,
    MessageHandler, PollAnswerHandler, Updater
)
from telegram.ext.filters import Filters

from bot.handlers.admin import handlers as admin_handlers
from bot.handlers.chat import handlers as chat
from bot.handlers.utils import error
from bot.handlers.action import handlers as action_handlers



def setup_dispatcher(dp):
    # onboarding
    dp.add_handler(CommandHandler("start", chat.command_start))
    dp.add_handler(CommandHandler("account", chat.command_account))
    
    # admin commands
    dp.add_handler(CommandHandler("admin", admin_handlers.admin))
    dp.add_handler(CommandHandler("stats", admin_handlers.stats))
    dp.add_handler(CommandHandler('export_users',admin_handlers.export_users))
    
    # forward user question to support chat
    dp.add_handler(CommandHandler("support", chat.command_support))

    # proxy manegment commands
    dp.add_handler(MessageHandler(Filters.regex(r'^/prolong(/s)?.*'), action_handlers.prolong_command))
    dp.add_handler(CallbackQueryHandler(action_handlers.prolong_command_run, pattern=r'^запроспродлитьпрокси$'))
    dp.add_handler(MessageHandler(Filters.regex(r'^/check(/s)?.*'), action_handlers.check_command))
    dp.add_handler(MessageHandler(Filters.regex(r'^/change(/s)?.*'), action_handlers.change_command))

    # vpn action messages
    dp.add_handler(CallbackQueryHandler(action_handlers.create_new_vpn_order, pattern=r'^уменяестьприложение$'))
    dp.add_handler(CallbackQueryHandler(action_handlers.cant_scan_qr, pattern=r'^янемогуотсканироватьqrcode$'))
    dp.add_handler(CallbackQueryHandler(action_handlers.buy_traffic, pattern=r'^купитьгб$'))
    dp.add_handler(CallbackQueryHandler(action_handlers.create_new_vpn_order, pattern=r'^приобреститариф$'))
    dp.add_handler(CallbackQueryHandler(action_handlers.delete_peer, pattern=r'^удалитьподключение$'))

    # proxy action messages
    dp.add_handler(CallbackQueryHandler(action_handlers.buy_proxy, pattern=r'^купитьпрокси$'))
    dp.add_handler(CallbackQueryHandler(action_handlers.show_countrys, pattern=r'(ipv4)|(ipv6)|(общиеipv4)'))

    # payment action messages
    dp.add_handler(CallbackQueryHandler(callback=action_handlers.topup, pattern=r'(\d+\s₽)'))

    # recive all commands
    dp.add_handler(MessageHandler(Filters.command, chat.recive_command))

    # recive all messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & ~Filters.chat(chat_id=int(TELEGRAM_SUPPORT_CHAT)), chat.recive_message))

    # recive all callback
    dp.add_handler(CallbackQueryHandler(chat.recive_calback))

    # recive all pools
    dp.add_handler(PollAnswerHandler(chat.receive_poll_answer))

    # forward answers from admin support chat to user
    dp.add_handler(MessageHandler(Filters.chat(chat_id=int(TELEGRAM_SUPPORT_CHAT)), chat.forward_from_support))

    # handling errors
    dp.add_error_handler(error.send_stacktrace_to_tg_chat)
    return dp


def run_pooling():
    """ Run bot in pooling mode """
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp = setup_dispatcher(dp)

    bot_info = Bot(TELEGRAM_TOKEN).get_me()
    bot_link = f"https://t.me/" + bot_info["username"]
    print(f"Pooling of '{bot_link}' started")

    updater.start_polling()
    updater.idle()


# Global variable - best way I found to init Telegram bot
bot = Bot(TELEGRAM_TOKEN)
try:
    TELEGRAM_BOT_USERNAME = bot.get_me()["username"]
except telegram.error.Unauthorized:
    logging.error(f"Invalid TELEGRAM_TOKEN.")
    sys.exit(1)


@app.task(ignore_result=True)
def process_telegram_event(update_json):
    update = Update.de_json(update_json, bot)
    dispatcher.process_update(update)


def set_up_commands(bot_instance: Bot) -> None:
    langs_with_commands: Dict[str, Dict[str, str]] = {
        'en': {
            'start': 'Run bot 🚀',
            'account': 'My accaunt 👤',
            'topup': 'Top up my balance 💰',
            'referral': 'Referral program 🎁', 
            'problem': 'Have a problem ❓',
            'support': 'Text to support 👥',
        },
        'ru': {
            'start': 'Запустить бота 🚀',
            'account': 'Личный кабинет 👤',
            'topup': 'Пополнить баланс 💰',
            'referral': 'Реферальная программа 🎁',
            'problem': 'У меня вопрос/проблема ❓',
            'support': 'Написать в поддержку 👥',
        }
    }

    bot_instance.delete_my_commands()
    for language_code in langs_with_commands:
        bot_instance.set_my_commands(
            language_code=language_code,
            commands=[
                BotCommand(command, description) for command, description in langs_with_commands[language_code].items()
            ]
        )


# WARNING: it's better to comment the line below in DEBUG mode.
# Likely, you'll get a flood limit control error, when restarting bot too often
set_up_commands(bot)

n_workers = 1 if DEBUG else 4
dispatcher = setup_dispatcher(Dispatcher(
    bot, update_queue=None, workers=n_workers, use_context=True))
