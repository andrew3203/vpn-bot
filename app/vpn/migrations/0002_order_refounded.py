# Generated by Django 3.2.6 on 2022-09-30 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vpn', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='refounded',
            field=models.BooleanField(default=True, verbose_name='Денбги возвращены'),
        ),
    ]
