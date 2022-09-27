from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

urlpatterns = [  
    path('yoo/', csrf_exempt(views.YooPaymentEventView.as_view())),
]