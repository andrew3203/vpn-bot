import json
import logging
from django.views import View
from django.http import JsonResponse, HttpResponse
from yookassa.domain.notification import WebhookNotification
from payments.models import Payment
from bot.tasks import send_delay_message


logger = logging.getLogger(__name__)


class YooPaymentEventView(View):

    def post(self, request, *args, **kwargs):
        event_json = json.loads(request.body)
        try:
            notification_object = WebhookNotification(event_json)
        except Exception as e:
            logger.error(e)

        payment_id = notification_object.payment_method.id
        event = notification_object.event

        msg_name, user_id = Payment.yoo_process_event(payment_id, event)
        send_delay_message.delay(user_id=user_id, msg_name=msg_name)
        return HttpResponse(status=200)
    
    def get(self, request, *args, **kwargs): 
        return JsonResponse({"ok": "Method is working"})
