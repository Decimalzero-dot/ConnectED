from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('', views.home_view, name='home'),
]