from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_notifications, name='my-notifications'),
    path('<int:pk>/read/', views.mark_as_read, name='mark-as-read'),
    path('read-all/', views.mark_all_as_read, name='mark-all-as-read'),
    path('<int:pk>/delete/', views.delete_notification, name='delete-notification'),
]