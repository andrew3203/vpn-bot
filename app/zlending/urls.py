from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from . import views

urlpatterns = [  
    # TODO: make webhook more secure
    path('', views.LendingView.as_view()),
    path('privacy/', views.privacy, name="privacy"),
]