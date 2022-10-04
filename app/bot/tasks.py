"""
    Celery tasks. Some of them will be launched periodically from admin panel via django-celery-beat
"""
import time
from typing import Union, List, Optional, Dict
import telegram
import redis
from django.db.models import F
from celery.utils.log import get_task_logger
from abridge_bot.celery import app
from abridge_bot.settings import REDIS_URL, PROGREV_NAMES
from bot.handlers.utils import utils
from bot import models
from bot.handlers.broadcast_message.utils import (
    _send_message, _from_celery_entities_to_entities, 
    _from_celery_markup_to_markup
)

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def broadcast_message(
    user_ids: List[Union[str, int]],
    text: str,
    entities: Optional[List[Dict]] = None,
    reply_markup: Optional[List[List[Dict]]] = None,
    sleep_between: float = 0.4,
    parse_mode=telegram.ParseMode.HTML,
) -> None:
    """ It's used to broadcast message to big amount of users """
    logger.info(f"Going to send message to {len(user_ids)} users")

    entities_ = _from_celery_entities_to_entities(entities)
    reply_markup_ = _from_celery_markup_to_markup(reply_markup)
    for user_id in user_ids:
        try:
            _send_message(
                user_id=user_id,
                text=text,
                entities=entities_,
                reply_markup=reply_markup_,
                parse_mode=parse_mode
            )
            logger.info(f"Broadcast message was sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}, reason: {e}")
        time.sleep(max(sleep_between, 0.1))

    logger.info("Broadcast finished!")

@app.task(ignore_result=True)
def broadcast_message2(
    users: List[Union[str, int]],
    message_id: str,
    sleep_between: float = 0.3,
) -> None:
    logger.info(f"- - - - - Going to send {len(users)} messages - - - - -")

    sent_am = 0
    for user_id  in users:
        next_state, prev_message_id = models.User.get_broadcast_next_states(user_id, message_id)
        prev = utils.send_broadcast_message(
            next_state=next_state,
            user_id=user_id,
            prev_message_id=prev_message_id
        )
        sent_am = sent_am + 1 if prev else sent_am
        models.User.unset_prew_message_id(user_id)
        logger.info(f"Sent message to {user_id}!")
        time.sleep(max(sleep_between, 0.1))

    logger.info("Broadcast finished!")
    list_am = len(users); block = list_am - sent_am
    utils.admin_logs_message(f'<b>Рассылка на {sent_am}/{list_am} завершена!</b>\nВ блоке {block} клиентов.')

@app.task(ignore_result=True)
def update_photo(queue):
    r = redis.from_url(REDIS_URL)
    cash = models.Message.make_cashes()
    r.mset(cash)
    print('set_messages_states')


@app.task(ignore_result=True)
def send_delay_message(user_id, msg_name):
    prev_state, next_state, prev_message_id = models.User.get_prev_next_states(user_id, msg_name)

    prev_msg_id = utils.send_message(
        prev_state=prev_state,
        next_state=next_state,
        user_id=user_id,
        context=None,
        prev_message_id=prev_message_id
    )
    models.User.set_message_id(user_id, prev_msg_id)

@app.task(ignore_result=True)
def check_deep_link(user_id, deep_link):
    user_ids = list(models.User.objects.all().values_list('user_id', flat=True))
    msg_dict = dict(PROGREV_NAMES)
    if deep_link not in user_ids:
        models.User.objects.filter(user_id=user_id).update(deep_link=None)
        send_delay_message.delay(user_id, msg_name=msg_dict['user_invalid_deep_link'])
        return False
    else:
        send_delay_message.delay(deep_link, msg_name=msg_dict['user_valid_deep_link'])
        send_delay_message.delay(user_id, msg_name=msg_dict['deep_valid_deep_link'])
        return True


@app.task(ignore_result=True)
def update_message_countors(message_id, user_id):
    count = models.Message.count_unique_users(message_id, user_id)
    models.Message.objects.filter(id=message_id).update(
        clicks=F('clicks') + 1,
        unique_clicks=count
    )