from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.userSignupView, name='signup'),
    path('home/', views.Home, name="home"),
    path('login/',views.userLoginView,name = 'login'),
]