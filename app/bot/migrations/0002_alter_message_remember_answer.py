# Generated by Django 3.2.6 on 2022-10-04 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='remember_answer',
            field=models.BooleanField(blank=True, default=False, help_text='Запомомнить на какую кнопку нажал пользователь. Результат будет доступен в след сообщениях через keywords, где key - название кнопки', verbose_name='Запомнить ответ'),
        ),
    ]