from django.db import models
from utils.models import CreateTracker
from bot.models import User
import uuid
from yookassa import Configuration, Payment
from abridge_bot.settings import (
    YOO_ACCAOUNT_ID, YOO_SECRET_KEY, YOO_RETURN_UTL,
    DEEP_CASHBACK_PERCENT, USER_CASHBACK_PERCENT,
    YOO_MSG_NAME
)
from bot.tasks import send_delay_message



class Payment(CreateTracker):
    price = models.FloatField(
        'Сумма'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, null=True
    )
    paid = models.BooleanField(
        'Оплачен',
        default=False
    )
    refounded = models.BooleanField(
        'Возврашен',
        default=False
    )
    canceled = models.BooleanField(
        'Отменен',
        default=False
    )
    notes = models.TextField(
        'Доп. инфа',
        max_length=300,
        default='', blank=True
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ №{self.pk}. {self.user}, {self.price}"

    def yoo_topup(self) -> str:
        Configuration.account_id = YOO_ACCAOUNT_ID
        Configuration.secret_key = YOO_SECRET_KEY

        payment_name = self.__str__()

        payment = Payment.create({
            "amount": {
                "value": self.price,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": YOO_RETURN_UTL
            },
            "capture": True,
            "description": payment_name
        }, uuid.uuid4())
        self.notes = payment.id
        self.save()
        return payment.confirmation.confirmation_url
    
    @staticmethod
    def yoo_make_payment(user_id, price) -> str:
        payment = Payment.objects.create(
            user=User.objects.get(user_id=user_id),
            price = price
        )
        return payment.topup()
    
    def sucsess(self):
        self.user.balance += self.price
        flag = False
        if self.user.deep_link:
            deep_user = User.objects.get(user_id=self.user.deep_link)
            if deep_user.cashback_balance == 0:
                deep_user.balance += self.price * DEEP_CASHBACK_PERCENT
                deep_user.cashback_balance +=  self.price * DEEP_CASHBACK_PERCENT
                deep_user.save()
                msg_dict = dict(YOO_MSG_NAME)
                send_delay_message.delay(deep_user.user_id, msg_dict['deep_cashback'])

                self.user.balance += self.price * USER_CASHBACK_PERCENT
                

        self.paid = True
        self.save()
        if flag:
            send_delay_message.apply_async(
                kwargs={'user_id': self.user.user_id, 'msg_name': msg_dict['user_cashback']}, 
                countdown=5
            )
    
    def refound(self):
        self.refounded = True
        self.user.balance -= self.price
        self.user.save()
        self.save()

    def cancel(self):
        self.canceled = True
        self.save()

    @staticmethod
    def yoo_process_event(yoo_payment_id, event):
        payment = Payment.objects.get(notes=yoo_payment_id)
        msg_code = dict(YOO_MSG_NAME)
        if event == 'payment.succeeded':
            payment.sucsess()
            msg_name = msg_code[event]
        elif event == 'payment.canceled':
            payment.cancel()
            msg_name = msg_code[event]
        elif event == 'refund.succeeded':
            payment.refound()
            msg_name = msg_code[event]
        else:
            msg_name = msg_code['payment_error']
        
        return msg_name, payment.user.user_id

