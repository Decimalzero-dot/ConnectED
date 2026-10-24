from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('explore/', views.explore_view, name='explore'),
    path('explore/<int:pk>/', views.explore_detail, name='explore_detail'),
]
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
handler403 = 'core.views.error_403'
handler429 = 'accounts.views.handler429'