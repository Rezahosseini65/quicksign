from django.urls import path

from . import views

urlpatterns = [
    path('phone-number/check/', views.PhoneNumberCheckView.as_view(), name='check-phone'),
    path('login/', views.UserLoginView.as_view(), name='login-user'),
    path('register/', views.UserRegisterView.as_view(), name='register-user')
]