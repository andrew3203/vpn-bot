from django.db import models
from utils.models import CreateUpdateTracker
from datetime import datetime, timedelta
from datetime import timedelta
from django.db.models.signals import  post_save
from django.dispatch import receiver
import redis
import json
from abridge_bot.settings import REDIS_URL
from proxy.dispatcher import proxy_connector
from bot.handlers.utils.utils import admin_logs_message
from bot.handlers.admin.static_text import proxy_balance, balance_error
from proxy.tasks import deactivate_order, run_auto_prolong_task

from bot.models import User


class ProxyOrder(CreateUpdateTracker):
    user = models.ForeignKey(
        User,
        verbose_name='Владалец',
        on_delete=models.SET_NULL, null=True
    )
    date_end = models.DateTimeField(
        'Время окончания'
    )
    proxy_country = models.CharField(
        'Страна',
        max_length=2
    )
    proxy_version = models.IntegerField(
        'Версия',
    )
    proxy_type = models.CharField(
        'Тип',
        max_length=50
    )
    auto_prolong = models.BooleanField(
        'Продлевать автоматически',
        default=False
    )
    active = models.BooleanField(
        'Активный',
        default=True
    )
    refounded = models.BooleanField(
        'Деньги возвращены',
        default=True
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.tariff}'

    def get_keywords(self) -> dict:
        keywords = {}
        all_proxy = Proxy.objects.filter(order=self)
        proxy_list = '\n'.join([f'<code>{p}</code>' for p in all_proxy])
        keywords['proxy_list'] = proxy_list
        keywords['proxy_date_end'] = self.date_end
        keywords['proxy_version'] = f'IPv{self.proxy_version}'
        keywords['proxy_type'] = self.proxy_type.upper()
        keywords['proxy_country'] = self.proxy_country.upper()
        keywords['proxy_auto_prolong'] = 'Да' if self.auto_prolong else 'Нет'
        return keywords

    def set_keywords(self):
        r = redis.from_url(REDIS_URL)
        key = f'{self.user.user_id}_proxy_keywords'
        proxy_keywords = self.get_keywords()
        r.set(key, value=json.dumps(proxy_keywords, ensure_ascii=False))

    @staticmethod
    def create_new_order(
        user_id: int, version: int, 
        country: str,  period: int, ptype: str, 
        count: str, auto_prolong: bool = False
    ) -> str:
        resp = proxy_connector.get_price(period=period, version=version, count=count)
        accautn_balance, price = resp['balance'], resp['price']

        if accautn_balance - price >= 0:
            u = User.objects.get(user_id=user_id)
            if u.balance - price >= 0:
                u.balance -= price; u.save()
                admin_logs_message(
                    proxy_balance, accautn_balance=accautn_balance-price, 
                    count=count, price=price, version=version
                )
                proxy_list = proxy_connector.buy(
                    count=count, period=period, country=country, version=version
                )['list'].values()
                order = ProxyOrder.objects.create(
                    user=u, date_end=datetime.strptime(proxy_list[0]['date_end'], "%Y-%m-%d H:M:S") ,
                    proxy_version=version, proxy_type=ptype, proxy_country=country
                )
                for p in proxy_list:
                    new_proxy = Proxy.objects.create(
                        proxy_id=p['id'],
                        proxy=f"{p['host']}:{p['port']}:{p['user']}:{p['pass']}"
                    )
                    new_proxy.save()
                    order.proxy.add(new_proxy)
                order.auto_prolong = auto_prolong
                order.save()
                return 'Прокси куплены'
            return 'Недостаточно средств'
        return 'На акаунте нету денег'
    
    @staticmethod
    def prolong_order(order_id):
        order = ProxyOrder.objects.get(pk=order_id)
        
        proxies = order.proxy.all()
        count = proxies.count()
        period = (order.date_end - order.created_at).days

        price = proxy_connector.get_price(
            period=period,
            version=order.proxy_version, count=count
        )['price']
        accautn_balance = proxy_connector.get_status()['balance']

        u = order.user
        if u.balance - price >= 0:

            if accautn_balance - price >= 0:
                u.balance -= price; u.save()
                admin_logs_message(
                    proxy_balance, accautn_balance=accautn_balance, 
                    count=count, price=price, version=order.proxy_version
                )
                proxy_ids = list(proxies.values_list('proxy_id', flat=True))
                proxy_connector.prolong(period=period, ids=','.joint(proxy_ids))
                order.date_end += timedelta(days=period); order.save()
                return 'Прокси куплены', u.user_id
            else:
                admin_logs_message(
                    balance_error, accautn_balance=accautn_balance, 
                    user_id=u.user_id, price=price
                )
                return 'На акаунте нету денег', u.user_id

        order.active = False
        order.save()
        return 'Недостаточно средств', u.user_id

   
class Proxy(CreateUpdateTracker):
    order = models.ForeignKey(
        ProxyOrder,
        verbose_name='Заказ',
        on_delete=models.CASCADE,
    )
    proxy_id = models.PositiveBigIntegerField(
        'Прокси id',
        primary_key=True
    )
    proxy = models.CharField(
        'Прокси',
        help_text='IP : PORT : USER : PASSWORD',
        max_length=500
    )

    class Meta:
        verbose_name = 'Прокси'
        verbose_name_plural = 'Прокси'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.proxy}'
    
    @property
    def user(self):
        return self.order.user

    @property
    def country(self):
        return self.order.proxy_country
    
    @property
    def ptype(self):
        return self.order.proxy_type

    @property
    def version(self):
        return self.order.proxy_version

    @property
    def date_end(self):
        return self.order.date_end


@receiver(post_save, sender=ProxyOrder)
def set_proxy_cash(sender, instance, created, **kwargs):
    if instance.active:
        instance.set_keywords()

        if created:
            end_date = instance.date_end
            kwargs = {'order_id': instance.pk}
            if instance.auto_prolong:
                run_auto_prolong_task.apply_async(kwargs=kwargs, eta=end_date)
            else:
                deactivate_order.apply_async(kwargs=kwargs, eta=end_date+timedelta(hours=10))
    else:
        r = redis.from_url(REDIS_URL)
        r.delete(f'{instance.user.user_id}_proxy_keywords')