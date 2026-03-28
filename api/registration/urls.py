from django.urls import path

from .views import RegisterUserAPIView

urlpatterns = [
    path('auth/register/', RegisterUserAPIView.as_view(), name='auth-register'),
]
