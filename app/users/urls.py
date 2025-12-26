from django.urls import path
from . import views


urlpatterns = [
    path('', views.list_users, name='list-users'),
    path('create/', views.create_user, name='create-user'),
    path('<int:pk>/update/', views.update_user, name='update-user'),
    path('<int:pk>/toggle-status/', views.toggle_user_status, name='toggle-user-status'),
]