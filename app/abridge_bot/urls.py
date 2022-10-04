from django.contrib import admin
from django.urls import include, path
from abridge_bot import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include('zlending.urls')),
    path("bot/", include('bot.urls')),
    path("payment/", include('payment.urls')),
    path('admin/', admin.site.urls),
]

handler404 = 'zlending.views.handler404'

if bool(settings.DEBUG):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
