from abridge_bot.celery import app
from celery.utils.log import get_task_logger

from proxy.models import *
from bot.models import User
from proxy.dispatcher import proxy_connector
from bot.tasks import send_delay_message
from bot.handlers.action import static_text

logger = get_task_logger(__name__)



@app.task(ignore_result=True)
def deactivate_order(order_id):
    order = ProxyOrder.objects.get(pk=order_id)
    order.prolong_order = False; order.active = False
    order.save()

    proxy_ids = list(order.proxy.all().values_list('proxy_id', flat=True))
    proxy_connector.delete(','.join(proxy_ids))
    Proxy.objects.filter(proxy_id__in=proxy_ids).delete()
    send_delay_message.delay(user_id=order.user.user_id, msg_name='Прокси удален')  


@app.task(ignore_result=True)
def run_auto_prolong_task(order_id):
    msg_name, user_id = ProxyOrder.prolong_order(order_id)
    send_delay_message.delay(user_id=user_id, msg_name=msg_name)


@app.task(ignore_result=True)
def prolong_orders_task(order_ids, period):
    for order_id in order_ids:
        msg_name, user_id = ProxyOrder.prolong_order(int(order_id), period)
        send_delay_message.delay(user_id=user_id, msg_name=msg_name)

@app.task(ignore_result=True)
def ckeck_orders_task(order_ids):
    msg_name = 'Результат проверки'
    for order_id in order_ids:
        user_id = ProxyOrder.check_order(int(order_id))
        send_delay_message.delay(user_id=user_id, msg_name=msg_name)


@app.task(ignore_result=True)
def change_order_task(order_ids):
    msg_name = 'Результат изменения типа'
    for order_id in order_ids:
        user_id = ProxyOrder.change_order(int(order_id))
        send_delay_message.delay(user_id=user_id, msg_name=msg_name)


@app.task(ignore_result=True)
def buy_proxy_task(user_id):
    args = list(map(lambda x: x.lower().replace(' ', ''), static_text.proxy_choose_msg_names))
    args = User.pop_choices(user_id, *args)
    kwargs = dict(list(zip(static_text.proxy_order_fields, args)))
    msg_text = ProxyOrder.create_new_order(user_id=user_id, **kwargs)
    send_delay_message.delay(user_id=user_id, msg_name=msg_text)  