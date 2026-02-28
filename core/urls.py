from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.Home, name="home"),
    path('signup/', views.userSignupView, name='signup'),
    path('login/', views.userLoginView, name='login'),
    path('logout/', views.userLogoutView, name='logout'),
]