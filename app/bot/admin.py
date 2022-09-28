from curses.ascii import US
from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from bot.models import User
from abridge_bot.settings import DEBUG
from bot.handlers.utils import utils
from django.contrib.auth.models import Group 
from django.urls import reverse
from bot import models
from bot import forms
from bot.tasks import broadcast_message2
from django_celery_beat.models import (
    IntervalSchedule,
    CrontabSchedule,
    SolarSchedule,
    ClockedSchedule,
    PeriodicTask,
)




admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)

admin.site.unregister(Group)

admin.site.site_header = 'Bridge VPN Bot Админ панель'
admin.site.index_title = 'Bridge VPN Bot Администратор'
admin.site.site_title = 'Admin'


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'user_id', 'first_name', 'last_name', 'balance', 'cashback_balance',
        'deep_link', 'created_at', 'updated_at',
    ]
    list_filter = ["is_blocked_bot", 'is_admin']
    search_fields = ('username', 'user_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user_id",),
                ('deep_link',),
                ('username', 'language_code'),
                ('first_name', 'last_name'),
            ),
        }),
        ('Дополнительная информация', {
            'fields': (
                ('balance', 'cashback_balance'),
                ("is_blocked_bot",),
                ('is_admin',),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',),
                ('updated_at',)
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def broadcast(self, request, queryset):
        if 'apply' in request.POST:
            f = forms.BroadcastForm(request.POST, request.FILES)
            if f.is_valid(): 
                broadcast = f.save() 
            else:
                return HttpResponseServerError()
            
            self.message_user(request, f"Рассылка {len(queryset)} сообщений начата")
            user_ids = list(queryset.values_list('user_id', flat=True))
            broadcast_message2.delay(users=user_ids, message_id=broadcast.message.id)
                
            url = reverse(f'admin:{broadcast._meta.app_label}_{broadcast._meta.model_name}_changelist')
            return HttpResponseRedirect(url)
        else:
            user_ids = queryset.values_list('user_id', flat=True)
            form = forms.BroadcastForm(initial={'_selected_action': user_ids, 'users': user_ids})
            context = {'form': form, 'title': u'Создание рассылки'}
            return render(request, "admin/broadcast_message.html", context)

    def all_broadcast(self, request, queryset):
        if 'apply' in request.POST:
            f = forms.BroadcastForm(request.POST, request.FILES)
            if f.is_valid(): 
                broadcast = f.save() 
            else:
                return HttpResponseServerError()
            
            users_queryset = User.objects.filter(is_blocked_bot=False)
            self.message_user(request, f"Рассылка {len(users_queryset)} сообщений начата")
            user_ids = list(users_queryset.values_list('user_id', flat=True))
            broadcast_message2.delay(users=user_ids, message_id=broadcast.message.id)
                
            url = reverse(f'admin:{broadcast._meta.app_label}_{broadcast._meta.model_name}_changelist')
            return HttpResponseRedirect(url)
        else:
            user_ids = queryset.values_list('user_id', flat=True)
            form = forms.BroadcastForm(initial={'_selected_action': user_ids, 'users': user_ids})
            context = {'form': form, 'title': u'Создание рассылки'}
            return render(request, "admin/broadcast_message.html", context)
    
   
    actions = [broadcast, all_broadcast]
    broadcast.short_description = 'Создать рассылку'
    all_broadcast.short_description = 'Создать рассылку для всех'


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pk', 'message_type', 'clicks', 'updated_at', 'created_at'
    ]
    list_filter = ["message_type", ]
    search_fields = ('name', )
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name", 'pk'),
                ('text',),
                ('message_type',),
                ('clicks',)
            ),
        }),
        ('Медия', {
            'fields': (
                ("files",),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',),
                ('updated_at',)
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'pk')
    filter_horizontal = ('files',)

    def set_zeros(self, request, queryset):
        queryset.update(clicks=0)
        self.message_user(request, f"Счетчики кликов обнулены")

    actions = [set_zeros, ]
    set_zeros.short_description = 'Обнулить счетчики'


@admin.register(models.Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'created_at'
    ]
    search_fields = ('name', 'tg_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name",),
                ("message",),
            ),
        }),
        ('Пользователи и группы', {
            'fields': (
                ("users",),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',)
            ),
        }),
    )
    filter_horizontal = ('users',)
    readonly_fields = ('created_at',)

    def send_mailing(self, request, queryset):
        self.message_user(request, f"Рассылка {len(queryset)} сообщений начата!")
        users = []
        for broadast in queryset:
            users += list(broadast.users.all().values_list('user_id', flat=True))

        broadcast_message2.delay(users=users, message_id=broadast.message.id)

    actions = [send_mailing]
    send_mailing.short_description = 'Начать рассылку'


@admin.register(models.File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tg_id', 'file', 'created_at'
    ]
    search_fields = ('name', 'tg_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name",),
                ("tg_id",),
            ),
        }),
        ('Информация о файле', {
            'fields': (
                ("file"),
                ('created_at',),
            ),
        })
    )
    readonly_fields = ('created_at',)


@admin.register(models.Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = [
        'message', 'created_at'
    ]
    search_fields = ('message',)
    fieldsets = (
        ('Основное', {
            'fields': (
                ("message",),
                ("answers",),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ("created_at"),
                ('updated_at',),
            ),
        })
    )
    readonly_fields = ('created_at','updated_at', 'answers', 'message')
