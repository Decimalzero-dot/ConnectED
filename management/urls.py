from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    # Super admin
    path('', views.super_dashboard, name='super_dashboard'),
    path('universities/', views.university_list, name='university_list'),
    path('universities/add/', views.university_create, name='university_create'),
    path('universities/<int:pk>/edit/', views.university_edit, name='university_edit'),
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/create/', views.create_campus_admin, name='create_campus_admin'),
    path('students/', views.all_students, name='all_students'),
    path('users/<int:pk>/role/', views.change_user_role, name='change_user_role'),

    # Campus admin (super_admin can also access these)
    path('campus/', views.campus_dashboard, name='campus_dashboard'),
    path('campus/students/', views.campus_students, name='campus_students'),
    path('campus/challenges/create/', views.challenge_create, name='challenge_create'),
    path('campus/challenges/<int:pk>/edit/', views.challenge_edit, name='challenge_edit'),
]