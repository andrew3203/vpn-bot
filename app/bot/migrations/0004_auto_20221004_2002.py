# Generated by Django 3.2.6 on 2022-10-04 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_alter_message_remember_answer'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='id',
        ),
        migrations.AlterField(
            model_name='message',
            name='name',
            field=models.CharField(max_length=120, primary_key=True, serialize=False, verbose_name='Название'),
        ),
    ]