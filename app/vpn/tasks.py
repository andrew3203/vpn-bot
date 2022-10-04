from abridge_bot.celery import app
from celery.utils.log import get_task_logger
from bot.tasks import send_delay_message
from vpn.models import VpnServer, VpnOrder
from celery import group
from django_celery_beat.models import IntervalSchedule, PeriodicTask

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def _update_traffic_task(server_id):
    server = VpnServer.objects.get(pk=server_id)
    server.update_traffic()
    logger.info(f'Server {server} was updated')


@app.task(ignore_result=True)
def _check_traffic_task(order_id):
    order = VpnOrder.objects.get(pk=order_id)
    msg_name = order.check_traffic()
    logger.info(f'VpnOrder {order} to was checked')
    if msg_name:
        send_delay_message.delay(user_id=order.user.user_id, msg_name=msg_name)
        logger.info(f'Sent message {msg_name} to {order.user.user_id}')


@app.task(ignore_result=True)
def get_updates():
    server_ids = VpnServer.objects.all().values_list('pk', flat=True)
    tasks = [_update_traffic_task.s(s_id) for s_id in server_ids]
    if len(tasks) > 0:
        group(tasks)()

    order_ids = VpnOrder.objects.filter(active=True).values_list('pk', flat=True)
    tasks1 = [_check_traffic_task.s(o_id) for o_id in order_ids]
    if len(tasks1) > 0:
        group(tasks1)()


every_10_minutes, _ = IntervalSchedule.objects.get_or_create(
    every=10, period=IntervalSchedule.MINUTES,
)
every_30_minutes, _ = IntervalSchedule.objects.get_or_create(
    every=30, period=IntervalSchedule.MINUTES,
)
PeriodicTask.objects.update_or_create(
    task="vpn.tasks.get_updates",
    name="get_updates",
    defaults=dict(
        interval=every_30_minutes,
        expire_seconds=60, 
    ),
)