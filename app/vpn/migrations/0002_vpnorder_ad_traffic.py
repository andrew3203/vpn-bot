# Generated by Django 3.2.6 on 2022-10-11 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vpn', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vpnorder',
            name='ad_traffic',
            field=models.IntegerField(blank=True, default=0, verbose_name='Доп. Трафик'),
        ),
    ]