import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abridge_bot.settings')
django.setup()

from bot.dispatcher import run_pooling

if __name__ == "__main__":
    run_pooling()