"""
Django settings for abridge_bot project.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
from pathlib import Path
import logging
import sys


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY")

DEBUG = int(os.environ.get("DEBUG", default=0))

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 3rd party apps
    'django_celery_beat',
    'debug_toolbar',
    'django_cleanup.apps.CleanupConfig',

    # local apps
    'bot.apps.BotConfig',
    'payment.apps.PaymentConfig',
    'proxy.apps.ProxyConfig',
    'vpn.apps.VPNConfig',
    'zlending.apps.ZLendingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    'corsheaders.middleware.CorsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',

    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'abridge_bot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'abridge_bot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("SQL_DATABASE", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "password"),
        "HOST": os.environ.get("SQL_HOST", "localhost"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

# CELERY
REDIS_URL = os.environ.get('REDIS_URL', 'redis://vpn_bot_redis:6379')
BROKER_URL = REDIS_URL
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = 'default'

DEFAULT_AUTO_FIELD='django.db.models.AutoField' 


# TELEGRAM
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_LOGS_CHAT_ID = os.environ.get("TELEGRAM_LOGS_CHAT_ID")
TELEGRAM_SUPPORT_CHAT = os.environ.get("TELEGRAM_SUPPORT_CHAT")


# REQUARIED MESSAGE NAMES
MSG_PRIMARY_NAMES = [
    ('start', 'Старт'), # requaried
    ('account', 'Личный кабинет'),
    ('topup', 'Пополнить баланс'),
    ('referral', 'Реферальная программа'),
    ('problem', 'У меня вопрос/проблема'),
    ('support', 'Написать в поддержку'),
    ('error', 'Ошибка'), # requaried
]
PROGREV_NAMES = [
    ('progrev_1', 'Прогрев 1'),
    ('deep_valid_deep_link', 'Новый пользователь по ссылке'),
    ('user_valid_deep_link', 'Верня ссылка приграшение'),
    ('user_invalid_deep_link', 'Неверная ссылка-приглашение'),
]
YOO_MSG_NAMES = [
    ('payment.succeeded', 'Платеж прошел успешно'),
    ('payment.canceled', 'Платеж отменен'),
    ('refund.succeeded', 'Платеж возвращен'),
    ('payment_error', 'Ошибка платежа'),
    ('deep_cashback', 'Бонусный кешбек'),
    ('user_cashback', 'Бонусный процент'),
]
VPN_MSG_NAMES = [
    ('traffic_05', 'У вас осталось меньше 0.5 ГБ'),
    ('traffic_0', 'У вас закончисля трафик'),
    ('order_auto_prolonged', 'Ваш заказ автоматически продлен'),
    ('order_cant_updated', 'Не получилось продлить заказ'),
    ('order_cenceled', 'Ваш заказ закрыт'),
    ('comes_to_the_end', 'Прошел месяц с покупки'),
    ('have_no_orders', 'У вас нету заказов'),
]
PROXY_NAMES = [
    ('Прокси куплены'.lower().replace(' ', ''), 'Прокси куплены'),
    ('Недостаточно средств'.lower().replace(' ', ''), 'Недостаточно средств'),
    ('На акаунте нету денег'.lower().replace(' ', ''), 'На акаунте нету денег')
]
MSG_PRIMARY_NAMES +=PROGREV_NAMES
MSG_PRIMARY_NAMES +=YOO_MSG_NAMES
MSG_PRIMARY_NAMES +=VPN_MSG_NAMES
MSG_PRIMARY_NAMES +=PROXY_NAMES


# PAYMENT SETTINGS
DEEP_CASHBACK_PERCENT = 0.05 # bonus cashback for invitor
USER_CASHBACK_PERCENT = 0.10 # bonus cashback for invited user
AVAILABLE_TOUPS = [100, 200, 500, 1000, 5000]

# VPN GBs
AVAILABLE_GBs = {
    1: 79,
    3: 249,
    5: 349
}

#PROXY Commision
PERSENT = 1.20

# PROXY API
PROXY_API_KEY = os.environ.get("PROXY_API_KEY")


# YOOKASSA API
YOO_ACCAOUNT_ID = os.environ.get("YOO_ACCAOUNT_ID")
YOO_SECRET_KEY = os.environ.get("YOO_SECRET_KEY")
YOO_RETURN_UTL = os.environ.get("YOO_RETURN_UTL", default='https://bridge-vpn.store')