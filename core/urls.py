from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.userSignupView, name='signup'),
    path('temp/', views.tempFile),
    path('adminPanel/', views.adminPanel),
]