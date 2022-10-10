from django.db import models
from utils.models import CreateUpdateTracker
from datetime import datetime, timedelta
from datetime import timedelta
from django.db.models.signals import  post_save
from django.dispatch import receiver
import redis
import json
import time
from abridge_bot.settings import REDIS_URL, PERSENT
from proxy.dispatcher import (
    proxy_connector,
    ipv4_price, ipv6_price, ipv4_shared_price
)
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
    price = models.FloatField(
        'Цена',
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
        keywords['ipv4_price'] = ipv4_price * PERSENT
        keywords['ipv6_price'] = ipv6_price * PERSENT
        keywords['ipv4_shared_price'] = ipv4_shared_price * PERSENT
        keywords['proxy_list'] = proxy_list
        keywords['proxy_date_end'] = self.date_end
        keywords['proxy_version'] = f'IPv{self.proxy_version}'
        keywords['proxy_type'] = self.proxy_type.upper()
        keywords['proxy_country'] = self.proxy_country.upper()
        keywords['proxy_auto_prolong'] = 'Да' if self.auto_prolong else 'Нет'
        return keywords

    def set_keywords(self, **kwarks):
        r = redis.from_url(REDIS_URL)
        key = f'{self.user.user_id}_proxy_keywords'
        proxy_keywords = self.get_keywords()
        ads = {ads[v]: [f'k'] for k, v in kwarks.items()}  
        proxy_keywords = {**proxy_keywords, **ads}
        r.set(key, value=json.dumps(proxy_keywords, ensure_ascii=False))
    
    @staticmethod
    def update_info(user_id):
        return {}

    @staticmethod
    def create_new_order(
        user_id: int, version: int, 
        country: str,  period: int, ptype: str, 
        count: str, auto_prolong: bool = False
    ) -> str:
        _translate = {'ipv4': 4, 'ipv6': 6, 'https': 'http', 'socks5': 'socks'}
        resp = proxy_connector.get_price(period=period, version=version, count=count)
        accautn_balance, price = float(resp['balance']), float(resp['price'])

        if accautn_balance - price >= 0:
            u = User.objects.get(user_id=user_id)
            price *= PERSENT
            if u.balance - price >= 0:
                u.balance -= price; u.save()
                admin_logs_message(
                    proxy_balance, accautn_balance=accautn_balance-price, 
                    count=count, price=price, version=version
                )
                version,  ptype= _translate[version], _translate[ptype]
                proxy_list = proxy_connector.buy(
                    count=count, period=period, country=country, version=version, type=ptype
                )['list'].values()
                order = ProxyOrder.objects.create(
                    user=u, date_end=datetime.strptime(proxy_list[0]['date_end'], "%Y-%m-%d H:M:S") ,
                    proxy_version=version, proxy_type=ptype, proxy_country=country, price=price
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
    def prolong_order(order_id, period):
        order = ProxyOrder.objects.get(pk=order_id)
        proxies = order.proxy.all()
        count = proxies.count()
        resp = proxy_connector.get_price(period=period, version=order.proxy_version, count=count)
        accautn_balance, price = resp['balance'], resp['price']

        u = order.user
        price *= PERSENT
        if u.balance - price >= 0:
            if accautn_balance - price/PERSENT >= 0:
                u.balance -= price; u.save()
                admin_logs_message(
                    proxy_balance, accautn_balance=accautn_balance, 
                    count=count, price=price, version=order.proxy_version
                )
                proxy_ids = list(proxies.values_list('proxy_id', flat=True))
                proxy_connector.prolong(period=period, ids=','.joint(proxy_ids))
                order.date_end += timedelta(days=period); order.save()
                order.set_keywords()
                return 'Прокси продлены', u.user_id
            else:
                admin_logs_message(
                    balance_error, accautn_balance=accautn_balance, 
                    user_id=u.user_id, price=price
                )
                return 'На акаунте нету денег', u.user_id

        order.active = False
        order.save()
        return 'Недостаточно средств', u.user_id

    @staticmethod
    def check_order(order_id):
        order = ProxyOrder.objects.get(pk=order_id)
        proxys = order.proxy.all()
        ans = ''
        for p in proxys:
            res = proxy_connector.check(ids=str(p.proxy_id))
            status = 'OK 🟢' if res['proxy_status'] else 'Сlosed 🔴'
            ans += f'{p} - {status}\n'
            time.sleep(0.2)
        order.set_keywords(proxy_check_result=ans)
        return order.user.user_id
    
    @staticmethod
    def change_order(order_id):
        order = ProxyOrder.objects.get(pk=order_id)
        proxy_ids = ','.join(list(order.proxy.all().values_list('proxy_id', flat=True)))
        prtpy = 'socks' if order.proxy_type == 'HTTPs' else 'http'
        res = proxy_connector.set_type(ids=proxy_ids, type=prtpy)
        ans = 'Обнавлен 🟢' if res['status'] else 'Ошибка 🔴'
        new_type = f'{prtpy.upper()}s' if prtpy[-1] == 'p' else f'{prtpy.upper()}5'
        order.set_keywords(proxy_type_result=ans, new_ptype=new_type)
        return order.user.user_id



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