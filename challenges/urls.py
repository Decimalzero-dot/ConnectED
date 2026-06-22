from django.urls import path
from . import views

app_name = 'challenges'

urlpatterns = [
    path('', views.challenge_list, name='list'),
    path('<int:pk>/', views.challenge_detail, name='detail'),
    path('review/', views.review_queue, name='review_queue'),
    path('review/<int:pk>/', views.review_submission, name='review_submission'),
]