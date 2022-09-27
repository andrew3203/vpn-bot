from django.db import models
from utils.models import CreateUpdateTracker, nb
from django.utils import timezone
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import redis
import json
from wg_vpn_bot.settings import REDIS_URL
import humanize

from bot.models import User


class Proxy(CreateUpdateTracker):
    user = models.ForeignKey(
        User,
        verbose_name='Владалец',
        on_delete=models.SET_NULL, null=True
    )
    proxy_id = models.PositiveBigIntegerField(
        'Прокси id',
        primary_key=True
    )
    proxy = models.TextField(
        'Прокси',
        help_text='IP : PORT : USER : PASSWORD',
        max_length=500
    )
    date_end = models.DateTimeField(
        'Время окончания'
    )
    version = models.IntegerField(
        'Версия',
    )
    ptype = models.CharField(
        'Тип',
        max_length=50
    )
    country = models.CharField(
        'Страна',
        max_length=2
    )

    class Meta:
        verbose_name = 'Прокси'
        verbose_name_plural = 'Прокси'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.proxy}'
    
    def get_keywords(self):
        now = timezone.now()
        humanize.i18n.activate("ru_RU")
        if self.date_end > now:
            time_left =  humanize.precisedelta(self.date_end - now)
        else:
            time_left =  humanize.naturaltime(self.date_end - now)
        keywords =  {
            self.proxy_id: ['proxy_id'],
            self.proxy: ['proxy'],
            self.date_end: ['date_end'],
            f'IPv{self.version}': ['version'],
            self.country: ['country'],
            time_left: ['time_left']

        }
        return keywords

    def update_info(self, new_data):
        pass

    def set_keywords(self):
        r = redis.from_url(REDIS_URL)
        r.set(
            f'{self.user_id}_keywords', 
            value=json.dumps(self.get_keywords(), ensure_ascii=False)
        )
    
    def make_cash(self):
        cash = {}
        cash[f'proxy_{self.proxy_id}'] = {
            'proxy_id': self.proxy_id,
            'proxy': self.proxy,
            'date_end': self.date_end,
            'version': self.version,
            'country': self.country,
            'user_id': self.user.user_id
        }
        return cash

    @staticmethod
    def make_cashes():
        cash = {}
        for proxy in Proxy.objects.all():
            cash = {**cash, **proxy.make_cash()}
        return cash
    

@receiver(post_save, sender=Proxy)
def set_proxy_cash(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    cash = instance.make_cash() 
    r.mset(cash)


@receiver(post_delete, sender=Proxy)
def del_proxy_cash(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    r.delete(f'proxy_{instance.proxy_id}') 