# Generated by Django 3.2.6 on 2022-10-03 14:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vpn', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан'),
        ),
        migrations.AlterField(
            model_name='peer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан'),
        ),
    ]