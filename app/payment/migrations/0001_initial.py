# Generated by Django 3.2.6 on 2022-10-04 09:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('price', models.FloatField(verbose_name='Сумма')),
                ('paid', models.BooleanField(default=False, verbose_name='Оплачен')),
                ('refounded', models.BooleanField(default=False, verbose_name='Возврашен')),
                ('canceled', models.BooleanField(default=False, verbose_name='Отменен')),
                ('notes', models.TextField(blank=True, default='', max_length=300, verbose_name='Доп. инфа')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='bot.user')),
            ],
            options={
                'verbose_name': 'Платеж',
                'verbose_name_plural': 'Платежи',
                'ordering': ['-created_at'],
            },
        ),
    ]
