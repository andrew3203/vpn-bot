import json
import redis
from abridge_bot.settings import VPN_MSG_NAMES, AVAILABLE_GBs, REDIS_URL
from django.db import models
from bot.models import User
from utils.models import CreateTracker
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from vpn.dispatcher import VPNConnector
from django.utils import timezone
from datetime import datetime, timedelta


# поменяться местами
class VpnServer(models.Model):
    country = models.CharField(
        'Страна',
        max_length=50
    )
    secret = models.CharField(
        'API KEY',
        max_length=500
    )
    link = models.CharField(
        'Ip addres',
        max_length=100
    )
    traffic = models.FloatField(
        'Трафик',
        default=0
    )
    public_key = models.CharField(
        'Publick key',
        max_length=500
    )

    class Meta:
        verbose_name = 'Сервер'
        verbose_name_plural = 'Серверы'

    def __str__(self):
        ip = self.link.split('//')[-1]
        return f'{self.country}, {ip}'

    def create_peer(self):
        vpn_connector = VPNConnector(self.secret, self.link)
        public_key = vpn_connector.create_peer()
        peer = Peer.objects.create(server=self, public_key=public_key)
        peer.save()
        return peer

    def delete_peer(self, public_key: str) -> bool:
        vpn_connector = VPNConnector(self.secret, self.link)
        res = vpn_connector.delete_peer(public_key)
        return res

    def update_traffic(self):
        vpn_connector = VPNConnector(self.secret, self.link)
        server_traffic = 0
        for peer in Peer.objects.filter(server=self):
            update = vpn_connector.get_peer(peer.public_key)
            new_bytes = update['total_receive_bytes'] + \
                update['total_transmit_bytes']
            peer.traffic += round(new_bytes / 1073741824, 6)
            peer.save()
            server_traffic += new_bytes

        self.traffic += round(server_traffic / 1073741824, 4)
        self.save()

    def save_peer_traffic(self, public_key):
        vpn_connector = VPNConnector(self.secret, self.link)
        update = vpn_connector.get_peer(public_key)
        new_bytes = update['total_receive_bytes'] + \
            update['total_transmit_bytes']
        self.traffic += round(new_bytes / 1073741824, 6)
        self.save()


class Peer(CreateTracker):
    server = models.ForeignKey(
        VpnServer,
        verbose_name='Сервер',
        on_delete=models.CASCADE,
    )
    public_key = models.CharField(
        'Publick key',
        max_length=500
    )
    traffic = models.FloatField(
        'Трафик',
        default=0
    )

    class Meta:
        verbose_name = 'Пир'
        verbose_name_plural = 'Пиры'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.server} - {self.pk}'
    
    def get_qr(self):
        secret, link = self.server.secret, self.server.link
        vpn_connector = VPNConnector(secret, link)
        return vpn_connector.get_peer_qr(self.public_key)

    def get_conf(self):
        secret, link = self.server.secret, self.server.link
        vpn_connector = VPNConnector(secret, link)
        return vpn_connector.get_peer_conf(self.public_key)


class Tariff(models.Model):
    name = models.CharField(
        'Название',
        max_length=200,
        unique=True
    )
    traffic_lim = models.FloatField(
        'Кол-во гб',
        default=10
    )
    price = models.FloatField(
        'Цена',
        default=299
    )
    period = models.IntegerField(
        'Период (дни)',
        default=31
    )
    peers_lim = models.IntegerField(
        'Кол-во подклчений',
        default=10
    )

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'
        ordering = ['-price']

    def __str__(self):
        return f'{self.name}'


class VpnOrder(CreateTracker):
    user = models.OneToOneField(
        User,
        verbose_name='Владалец',
        on_delete=models.SET_NULL, null=True
    )
    tariff = models.ForeignKey(
        Tariff,
        verbose_name='Тариф',
        on_delete=models.SET_NULL, null=True
    )
    peers = models.ManyToManyField(
        Peer,
        verbose_name='Подключения',
    )
    auto_prolong = models.BooleanField(
        'Продлевать автоматически',
        default=True
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
    
    def set_user_info(self) -> str:
        r = redis.from_url(REDIS_URL)
        user_id = self.user.user_id
        data = {
            'tariff_name': self.tariff.name,
            'country': self.peers.first().server.country
        }
        r.set(f'{user_id}_vpn_data', json.dumps(data))
            
    def check_traffic(self) -> str:
        traffic = 0
        msg_dict = dict(VPN_MSG_NAMES)
        traffic = sum(list(self.peers.all().values_list('tariff', flat=True)))

        now = timezone.now()
        end_date = self.created_at + timedelta(days=self.tariff.period)
        if end_date < now and self.auto_prolong:
            if self.user.balance - self.tariff.price >=0:
                 self.user.balance -= self.tariff.price
                 return msg_dict['order_auto_prolonged']
            self.active = False
            self.save()
            return msg_dict['order_cant_updated']
        elif end_date < now:
            self.active = False
            self.save()
            return msg_dict['order_cenceled']
        elif end_date - now < timedelta(days=1):
            return msg_dict['comes_to_the_end']


        if round(self.tariff.traffic_lim - traffic, 4) <= 0.5000:
            return msg_dict['traffic_05']
        elif round(self.tariff.traffic_lim - traffic, 4) < 0.0001:
            self.active = False
            self.save()
            return msg_dict['traffic_0']

        return None

    @staticmethod
    def add_traffic(user_id: int, gb_amount: int):
        user = User.objects.get(user_id=user_id)
        order = VpnOrder.objects.filter(user=user).first()
        msg_dict = dict(VPN_MSG_NAMES)
        if order is None:
            return msg_dict['have_no_orders']
        
        price = AVAILABLE_GBs[gb_amount]

        if user.balance - price < 0:
            return 'Недостаточно средств'
        

        user.balance -= price
        user.save

        new_traffic_lim = gb_amount + order.tariff.traffic_lim
        order.tariff = Tariff.objects.get_or_create(
            traffic_lim=new_traffic_lim)
        order.save()
        if order.active:
            return 'Покупка ГБ успешна'
        else:
            return 'Покупка ГБ успешна 1'

    @staticmethod
    def create_or_change(user_id: int, tariff_name: str, country: str) -> tuple:
        user = User.objects.get(user_id=user_id)
        tariff = Tariff.objects.filter(name=tariff_name).first()

        prev_order = VpnOrder.objects.filter(user__user_id=user_id).first()
        if prev_order:
            if prev_order.tariff == tariff:
                msg_text = 'У вас прежний тариф'
                return prev_order, msg_text
            prev_order.tariff = tariff
            order.set_user_info()
            prev_order.save()
            msg_text = 'Тариф изменен'
            return prev_order, msg_text
        elif user.balance - tariff.price < 0:
            msg_text = 'Не хватает средств'
            return None, msg_text

        user.balance -= tariff.price; user.save()
        server = VpnServer.objects.filter(country=country).first()
        peer = server.create_peer()
        order = VpnOrder.objects.create(user=user, tariff=tariff)
        order.save()
        order.peers.add(peer)
        order.save()
        order.set_user_info()
        msg_text = ''
        return order, msg_text

    @staticmethod
    def change_peer_of_order(user_id: int, country: str):
        order = VpnOrder.objects.get(user__user_id=user_id)
        # TODO потом их будет больше, надо балансировать нагрузку будет
        server = VpnServer.objects.filter(country=country).first()
        for peer in order.peers.all():
            peer.delete()
        peer = server.create_peer()
        order.peers.add(peer)
        order.save()

    @staticmethod
    def add_peer_to_order(user_id: int, country: str):
        order = VpnOrder.objects.get(user__user_id=user_id)
        # TODO потом их будет больше, надо балансировать нагрузку будет
        server = VpnServer.objects.filter(country=country).first()
        peer = server.create_peer()
        order.peers.add(peer)
        order.save()
    
    @staticmethod
    def get_user_info(user_id: int) -> str:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        data = r.get(f'{user_id}_vpn_data')
        if data:
             data = json.loads(data)
             created = False
        else:
            data = {'tariff_name': 'Пробный', 'country': 'DE'}
            created = True
            
        return data, created



@receiver(post_save, sender=VpnOrder)
def remove_user_states(sender, instance, **kwargs):
    if instance.active == False:
        for peer in instance.peers.all():
            peer.delete()


@receiver(post_delete, sender=Peer)
def remove_user_states(sender, instance, **kwargs):
    instance.server.save_peer_traffic(instance.public_key)
    instance.server.delete_peer(instance.public_key)
