# Generated by Django 3.2.6 on 2022-10-04 18:26

import bot.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('name', models.CharField(max_length=120, verbose_name='Название')),
                ('tg_id', models.CharField(blank=True, default=None, max_length=100, null=True, verbose_name='Телеграм id')),
                ('file', models.FileField(null=True, upload_to=bot.models.user_directory_path, verbose_name='Файл, видео')),
            ],
            options={
                'verbose_name': 'Медиа файл',
                'verbose_name_plural': 'Медиа файлы',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Изменен')),
                ('name', models.CharField(max_length=120, unique=True, verbose_name='Название')),
                ('text', models.TextField(help_text='Размер текста не более 4096 символов. Если вы используете кнопки, то их кол-во должно быть равно кол-ву сообщений выбранных ниже. Название кнопки должно совпадать с названием сообщения, к которому оно ведет.', max_length=4096, verbose_name='Текст')),
                ('message_type', models.CharField(choices=[('SIMPLE_TEXT', 'Простой текст'), ('POLL', 'Опрос'), ('KEYBOORD_BTN', 'Кнопка'), ('FLY_BTN', 'Чат. Кнопка')], default='SIMPLE_TEXT', max_length=25, verbose_name='Тип Сообщения')),
                ('clicks', models.IntegerField(blank=True, default=0, verbose_name='Кол-во кликов')),
                ('unique_clicks', models.IntegerField(blank=True, default=0, verbose_name='Кол-во уникальных кликов')),
                ('remember_answer', models.BooleanField(blank=True, default=False, help_text='Запомомнить на какую кнопку нажал пользователь. Результат будет доступен в след сообщениях через keywords по названию сообщения.', verbose_name='Запомнить ответ')),
                ('files', models.ManyToManyField(blank=True, to='bot.File', verbose_name='Картинки, Видео, Файлы')),
            ],
            options={
                'verbose_name': 'Сообщение',
                'verbose_name_plural': 'Сообщения',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Изменен')),
                ('user_id', models.PositiveBigIntegerField(primary_key=True, serialize=False, verbose_name='Телеграм id')),
                ('username', models.CharField(blank=True, max_length=32, null=True, verbose_name='Username')),
                ('first_name', models.CharField(blank=True, max_length=256, null=True, verbose_name='Имя')),
                ('last_name', models.CharField(blank=True, max_length=256, null=True, verbose_name='Фаммилия')),
                ('language_code', models.CharField(blank=True, help_text='Язык приложения телеграм', max_length=8, null=True, verbose_name='Язык')),
                ('deep_link', models.CharField(blank=True, max_length=64, null=True, verbose_name='Person code')),
                ('is_blocked_bot', models.BooleanField(default=False, verbose_name='Бот в блоке')),
                ('is_admin', models.BooleanField(default=False, verbose_name='Админ')),
                ('balance', models.FloatField(default=0, verbose_name='Баланс')),
                ('cashback_balance', models.FloatField(default=0, verbose_name='Кешбек')),
            ],
            options={
                'verbose_name': 'Клиент',
                'verbose_name_plural': 'Клиенты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Изменен')),
                ('answers', models.TextField(blank=True, max_length=500, null=True, verbose_name='Ответы')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.message', verbose_name='Сообщение')),
            ],
            options={
                'verbose_name': 'Результат опроса',
                'verbose_name_plural': 'Результаты опросов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Broadcast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('name', models.CharField(max_length=20, verbose_name='Название')),
                ('message', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='bot.message')),
                ('users', models.ManyToManyField(blank=True, to='bot.User')),
            ],
            options={
                'verbose_name': 'Рассылка',
                'verbose_name_plural': 'Рассылки',
                'ordering': ['-created_at'],
            },
        ),
    ]
