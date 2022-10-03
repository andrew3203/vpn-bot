from abridge_bot.celery import app
from celery.utils.log import get_task_logger

from proxy.models import *
from proxy.dispatcher import proxy_connector
from bot.tasks import send_delay_message

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
