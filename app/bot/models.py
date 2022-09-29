from __future__ import annotations
from random import randint
import cyrtranslit
import emoji
from django.db.models import F

from typing import Union, Optional, Tuple
import re
import json
from datetime import datetime, timedelta

from django.db import models
from django.db.models import QuerySet, Manager
from telegram import Update
from telegram.ext import CallbackContext

from abridge_bot.settings import MSG_PRIMARY_NAMES, REDIS_URL
from abridge_bot.settings import DEEP_CASHBACK_PERCENT, USER_CASHBACK_PERCENT
from bot.handlers.utils.info import extract_user_data_from_update
from utils.models import CreateUpdateTracker, CreateTracker, nb, GetOrNoneManager

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import redis



class AdminUserManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_admin=True)


class User(CreateUpdateTracker):
    user_id = models.PositiveBigIntegerField(
        'Телеграм id',
        primary_key=True
    )
    username = models.CharField(
        'Username',
        max_length=32, **nb
    )
    first_name = models.CharField(
        'Имя',
        max_length=256, **nb
    )
    last_name = models.CharField(
        'Фаммилия',
        max_length=256, **nb
    )
    language_code = models.CharField(
        'Язык',
        max_length=8,
        help_text="Язык приложения телеграм", **nb
    )
    deep_link = models.CharField(
        'Person code',
        max_length=64, **nb
    )
    is_blocked_bot = models.BooleanField(
        'Бот в блоке',
        default=False
    )
    is_admin = models.BooleanField(
        'Админ',
        default=False
    )
    balance = models.FloatField(
        'Баланс',
        default=0
    )
    cashback_balance = models.FloatField(
        'Кешбек',
        default=0
    )

    objects = GetOrNoneManager()  # user = User.objects.get_or_none(user_id=<some_id>)
    admins = AdminUserManager()  # User.admins.all()

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']

    def __str__(self):
        return f'@{self.username}' if self.username is not None else f'{self.user_id}'

    def get_keywords(self):
        coders = []
        if self.first_name is None:
            coders.append('first_name')
        if self.last_name is None:
            coders.append('last_name')
        if self.username is None:
            coders.append('username')

        deep_user = ''
        if self.deep_link:
            deep_user = User.objects.get(user_id=self.deep_link).to_str()
        else:
            coders.append('deep_user')
        keywords =  {
            self.user_id: ['user_id'],
            deep_user: ['deep_user'],
            self.last_name: ['last_name'],
            self.first_name: ['first_name'],
            self.username: ['username'],
            self.balance: ['balance'],
            self.cashback_balance: ['cashback_balance'],
            DEEP_CASHBACK_PERCENT * 100: ['DEEP_CASHBACK_PERCENT'],
            USER_CASHBACK_PERCENT * 100: ['USER_CASHBACK_PERCENT'],
            '': coders
        }
        return keywords
    
    def to_str(self):
        name = self.first_name or f'@{self.username}' or self.last_name or f'{self.user_id}'
        return f'{name}'

    def update_info(self, new_data):
        pass
    
    def set_keywords(self):
        r = redis.from_url(REDIS_URL)
        r.set(
            f'{self.user_id}_keywords', 
            value=json.dumps(self.get_keywords(), ensure_ascii=False)
        )

    @staticmethod
    def get_state(user_id):
        r = redis.from_url(REDIS_URL, decode_responses=True)

        if r.exists(user_id):
            message_id = json.loads(r.get(user_id))
            return json.loads(r.get(message_id))

        return None
    
    @staticmethod
    def set_message_id(user_id, message_id):
        if message_id:
            r = redis.from_url(REDIS_URL)
            r.set(f'{user_id}_prev_message_id', value=message_id)
    
    @staticmethod
    def unset_prew_message_id(user_id):
        r = redis.from_url(REDIS_URL,  decode_responses=True)
        message_id = r.get(f'{user_id}_prev_message_id')
        r.delete(f'{user_id}_prev_message_id')
        return message_id

    @staticmethod
    def get_prev_next_states(user_id, msg_text_key):
        r = redis.from_url(REDIS_URL, decode_responses=True)
        msg_text_key = Message.encode_msg_name(msg_text_key)

        if r.exists(user_id):
            message_id = json.loads(r.get(user_id))
            prev_state = json.loads(r.get(message_id))
            next_state_id = prev_state['ways'].get(msg_text_key, r.get('error'))

        else:
            prev_state = None
            next_state_id = r.get('start')
        
        Message.objects.filter(id=next_state_id).update(clicks=F('clicks') + 1)

        raw = r.get(next_state_id)
        next_state = json.loads(raw)
        next_state['user_keywords'] = User._load_keywords(r, user_id)
        r.setex(user_id, timedelta(hours=35), value=next_state_id)

        prev_message_id = r.get(f'{user_id}_prev_message_id')

        return prev_state, next_state, prev_message_id
    
    @staticmethod
    def _load_keywords(r, user_id):
        user_keywords = json.loads(r.get(f'{user_id}_keywords'))

        vpn_keywords = r.get(f'{user_id}_vpn_keywords')
        vpn_keywords = json.loads(vpn_keywords) if vpn_keywords else {}

        proxy_keywords = r.get(f'{user_id}_proxy_keywords')
        proxy_keywords = json.loads(proxy_keywords) if proxy_keywords else {}
        keywords = {**user_keywords, **vpn_keywords, **proxy_keywords}
        return keywords
        
    
    @staticmethod
    def get_broadcast_next_states(user_id, message_id):
        r = redis.from_url(REDIS_URL, decode_responses=True)

        next_state = json.loads(r.get(message_id))
        next_state_id = message_id

        next_state['user_keywords'] = User._load_keywords(r, user_id)
        r.setex(user_id, timedelta(hours=35), value=next_state_id)

        prev_message_id = r.get(f'{user_id}_prev_message_id')

        return next_state, prev_message_id

    @staticmethod
    def set_state(user_id, message_id):
        r = redis.from_url(REDIS_URL)
        r.setex(user_id, timedelta(hours=34), value=message_id)

    @classmethod
    def get_user_and_created(cls, update: Update, context: CallbackContext) -> Tuple[User, bool]:
        """ python-telegram-bot's Update, Context --> User instance """
        data = extract_user_data_from_update(update)
        u, created = cls.objects.update_or_create(
            user_id=data["user_id"], defaults=data)

        if created:
            # Save deep_link to User model
            if context is not None and context.args is not None and len(context.args) > 0:
                payload = context.args[0]
                # you can't invite yourself
                u.deep_link = payload
                u.save()

        return u, created

    @classmethod
    def get_user(cls, update: Update, context: CallbackContext) -> User:
        u, _ = cls.get_user_and_created(update, context)
        return u

    @classmethod
    def get_user_by_username_or_user_id(cls, username_or_user_id: Union[str, int]) -> Optional[User]:
        """ Search user in DB, return User or None if not found """
        username = str(username_or_user_id).replace("@", "").strip().lower()
        if username.isdigit():  # user_id
            return cls.objects.filter(user_id=int(username)).first()
        return cls.objects.filter(username__iexact=username).first()

    @property
    def invited_users(self) -> QuerySet[User]:
        return User.objects.filter(deep_link=str(self.user_id), created_at__gt=self.created_at)

    @property
    def tg_str(self) -> str:
        if self.username:
            return f'@{self.username}'
        return f"{self.first_name} {self.last_name}" if self.last_name else f"{self.first_name}"



def user_directory_path(instance, filename):
    base = 'abcdefghijklomopqrstuvwsynz'
    pre = ''.join([base[randint(0, 25)] for _ in range(3)])
    name = instance.name.replace(' ', '-')
    new_filename = cyrtranslit.to_latin(name, 'ru')
    new_filename = f"{new_filename}__{pre}.{filename.split('.')[-1]}".lower()
    return f'messages/{new_filename}'


class File(CreateTracker):
    name = models.CharField(
        'Название',
        max_length=120,
    )
    tg_id = models.CharField(
        'Телеграм id',
        max_length=100, default=None, **nb
    )
    file = models.FileField(
        'Файл, видео',
        upload_to=user_directory_path,
        null=True
    )

    class Meta:
        verbose_name = 'Медиа файл'
        verbose_name_plural = 'Медиа файлы'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name}'


class MessageType(models.TextChoices):
    SIMPLE_TEXT = 'SIMPLE_TEXT', 'Простой текст'
    POLL = 'POLL', 'Опрос'
    KEYBOORD_BTN = 'KEYBOORD_BTN', 'Кнопка'
    FLY_BTN = 'FLY_BTN', 'Чат. Кнопка'


class Message(CreateUpdateTracker):
    name = models.CharField(
        'Название',
        max_length=40,
    )
    text = models.TextField(
        'Текст',
        max_length=4096,
        help_text='Размер текста не более 4096 символов. Если вы используете кнопки, то их кол-во должно быть равно кол-ву сообщений выбранных ниже. Название кнопки должно совпадать с названием сообщения, к которому оно ведет.'
    )
    message_type = models.CharField(
        'Тип Сообщения',
        max_length=25,
        choices=MessageType.choices,
        default=MessageType.SIMPLE_TEXT,
    )
    clicks = models.IntegerField(
        'Кол-во кликов',
        default=0,
        blank=True
    )
    files = models.ManyToManyField(
        File,
        blank=True,
        verbose_name='Картинки, Видео, Файлы'
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name}'

    @staticmethod
    def encode_msg_name(name):
        name = emoji.replace_emoji(name, replace='')
        return name.lower().replace(' ', '')

    def _gen_msg_dict(self):
        messages = {}
        for msg_name, msg_id in Message.objects.all().values_list('name', 'id'):
            messages[self.encode_msg_name(msg_name)] = msg_id
        return messages

    def parse_message(self) -> dict:
        msg_dict = self._gen_msg_dict()
        regex = r"(\[[^\[\]]+\]\([^\(\)]+\)\s*\n)|(\[[^\[\]]+\]\s*\n)|(\[[^\[\]]+\]\([^\(\)]+\))|(\[[^\[\]]+\])"
        # group 1 - элемент кнопки с сылкой (с \n)
        # group 2 - обычный элемент кнопки опроса (с \n)

        # group 3 - элемент кнопки с сылкой (без \n)
        # group 4 - обычный элемент кнопки опроса (без \n)
        self.text = re.sub('\\r', '', self.text)
        matches = re.finditer(regex, self.text, re.MULTILINE)

        markup = [[]]
        ways = {}
        end_text = 100000
        for match in matches:
            group = match.group()
            end_text = min(end_text, match.start())
            groupNum = 1 + list(match.groups()).index(group)
            if groupNum in (1, 3):
                btn, link = group.split('](')
                btn = btn[1:]
                link = re.sub('(\)\s*)|([\)\n])', '', link)
            else:
                btn = re.sub('(\]\s*)|([\[\]\n])', '', group)
                link = None

            markup[-1].append((btn, link))
            if groupNum in (1, 2):
                markup.append([])

            if groupNum in (2, 4):
                btn_query_name = self.encode_msg_name(btn)
                ways[btn_query_name] = msg_dict[btn_query_name]

        res = {
            'message_type': self.message_type,
            'text': self.text[:end_text],
            'markup': markup,
            'ways': ways
        }
        if self.message_type == MessageType.POLL:
            poll = Poll.objects.filter(message=self).first()
            if poll is None:
                poll = Poll.objects.create(message=self)
                poll.answers = ': 0\n'.join([m[0][0] for m in markup]) + ': 0\n'
                poll.save()
            res['poll_id'] = poll.pk
        return res

    
    def make_cash(self):
        common_ways = {}
        for k, msg_name in MSG_PRIMARY_NAMES:
            m = Message.objects.filter(name=msg_name).first()
            common_ways[k] = m.id if m else 1

        cash = {}
        cash['start'] = common_ways['start']
        cash['error'] = common_ways.pop('error')

        data = self.parse_message()
        cash[self.id] = json.dumps({
            'poll_id': data.get('poll_id', ''),
            'text': data['text'],
            'ways': {**common_ways, **data['ways']},
            'markup': data['markup'] if data['markup'] else '',
            'message_type': data['message_type'],
            'photos': [f.file.path for f in self.files.all()]
        }, ensure_ascii=False)
        return cash

    @staticmethod
    def make_cashes():
        common_ways = {}
        for k, msg_name in MSG_PRIMARY_NAMES:
            m = Message.objects.filter(name=msg_name).first()
            common_ways[k] = m.id if m else 1

        cash = {}
        cash['start'] = common_ways['start']
        cash['error'] = common_ways.pop('error')

        for m in Message.objects.all():
            data = m.parse_message()
            cash[m.id] = json.dumps({
                'poll_id': data.get('poll_id', ''),
                'text': data['text'],
                'ways': {**common_ways, **data['ways']},
                'markup': data['markup'],
                'message_type': data['message_type'],
                'photos': [f.file.path for f in m.files.all()]
            }, ensure_ascii=False)

        return cash


class Poll(CreateUpdateTracker):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='Сообщение'

    )
    answers = models.TextField(
        max_length=500,
        verbose_name='Ответы',
        blank=True, null=True
    )

    class Meta:
        verbose_name = 'Результат опроса'
        verbose_name_plural = 'Результаты опросов'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Ответы на опрос: {self.message.name}'
    
    @staticmethod
    def update_poll(poll_id, answer):
        poll = Poll.objects.get(pk=poll_id)
        res = ''
        for ans in poll.answers.split('\n')[:-1]:
            ans_name, num = ans.split(': ')
            num = int(num) + 1 if ans_name == answer else num
            res += f'{ans_name}: {num}\n'
        poll.answers = res
        poll.save()


class Broadcast(CreateTracker):
    name = models.CharField(
        'Название',
        max_length=20,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True
    )
    users = models.ManyToManyField(
        User,
        blank=True,
    )
    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name}'

    def get_users(self):
        ids1 = self.users.values_list('user_id', flat=True)
        ids2 = self.group.users.values_list('user_id', flat=True)
        return list(set(ids1+ids2))


@receiver(post_save, sender=Message)
def set_message_states(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    cash = Message.make_cashes() #instance.make_cash()
    r.mset(cash)
 
@receiver(post_delete, sender=Message)
def remove_message_states(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    r.delete(instance.id) # TODO: check remove

@receiver(post_save, sender=User)
def set_user_keywords(sender, instance, **kwargs):
    instance.set_keywords()


@receiver(post_delete, sender=User)
def remove_user_states(sender, instance, **kwargs):
    r = redis.from_url(REDIS_URL)
    r.delete(f'{instance.user_id}') 
    r.delete(f'{instance.user_id}__keywords') 
    r.delete(f'{instance.user_id}_registration') 
    r.delete(f'{instance.user_id}_prev_message_id') 
    