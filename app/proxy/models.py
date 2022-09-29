from django.db import models
from utils.models import CreateUpdateTracker, nb
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import redis
import json
from abridge_bot.settings import REDIS_URL
import humanize
from .dispatcher import proxy_connector

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
        keywords = {}
        keywords =  {
            self.proxy_id: ['proxy_id'],
            self.proxy: ['proxy'],
            self.date_end: ['date_end'],
            f'IPv{self.version}': ['version'],
            self.country: ['country'],
            time_left: ['time_left'],
        }
        return keywords

    def update_keywords(self):
        r = redis.from_url(REDIS_URL, decode_responses=True)
        key = f'{self.user.user_id}_proxy_keywords'
        proxy_keywords = r.get(key)
        if proxy_keywords:
            proxy_keywords = json.loads(proxy_keywords)
        else:
            proxy_keywords = []
        
        proxy_keywords.append(self.get_keywords())
        r.set(key, value=json.dumps(proxy_keywords, ensure_ascii=False))
    
    def set_keywords(self):
        r = redis.from_url(REDIS_URL, decode_responses=True)
        key = f'{self.user.user_id}_proxy_keywords'
        proxy_keywords = [self.get_keywords()]
        
        r.set(key, value=json.dumps(proxy_keywords, ensure_ascii=False))   
        

    @staticmethod
    def update_info(user_id):
        #ids = ','.join(list(proxy.values_list('proxy_id', flat=True)))
        # if len(ids) > 1:
        #    resp = proxy_connector.get_proxy(descr=user_id)
        #    proxy_list = resp.get('list')
        now = timezone.now() 
        timedelta(days=1)
        proxy_list = ''
        delta = proxy.date_end - now
        for proxy in Proxy.objects.filter(user__user_id=user_id):
            if delta > timedelta(hours=8):
                proxy_connector.delete(ids=f'{proxy.proxy_id}')
                proxy.delete()
            else:
                humanize.i18n.activate("ru_RU")
                time_left =  humanize.precisedelta(delta) if proxy.date_end > now else humanize.naturaltime(delta)
                proxy_list += f'ID: {proxy.pk}, Версия: IPv{proxy.version}, Тип: {proxy.ptype.upper()}, Осталось: {time_left}\n'
                proxy_list += f'<code>{proxy.proxy}</code>\n'
        
        r = redis.from_url(REDIS_URL)
        key = f'{user_id}_proxy_keywords'
        r.set(key, value=json.dumps({'proxy_list': proxy_list}, ensure_ascii=False))

        
        
       
            
        return {}


    @staticmethod
    def make_cashes():
        cash = {}
        for proxy in Proxy.objects.all():
            cash = {**cash, **proxy.make_cash()}
        return cash
    

def balance_check():
    pass
    

@receiver(post_save, sender=Proxy)
def set_proxy_cash(sender, instance, **kwargs):
    instance.set_keywords() 


@receiver(post_delete, sender=Proxy)
def del_proxy_cash(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    r.delete(f'{instance.user.user_id}_proxy_keywords') 