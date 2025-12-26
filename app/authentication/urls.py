from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from app.users.views import change_password

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('me/', views.me, name='me'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('change-password/', change_password, name='change-password'),
]