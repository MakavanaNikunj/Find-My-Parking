from django.urls import path
from . import views

app_name = "parking"

urlpatterns = [
    # owner dashboard urls
    path('owner/',views.ownerDashboardView,name='owner_dashboard'),
    path('add-parking/', views.add_parking, name='add_parking'),
    path('manage-parking/', views.manage_parking, name='manage_parking'),
    path('manage-slots/', views.manage_slots, name='manage_slots'),
    path('bookings/', views.bookings, name='bookings'),
    path('earnings/', views.earnings, name='earnings'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings, name='settings'),
    path("logout/", views.logout_view, name="logout"),



    # user dashboard urls 
    path('user/', views.userDashboardView, name='user_dashboard'),
    path('find-parking/', views.find_parking, name='find_parking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('active-parking/', views.active_parking, name='active_parking'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('saved-locations/', views.saved_locations_view, name='saved_locations'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile-settings/', views.profile_settings, name='profile_settings'),
    path('help-support/', views.help_support, name='help_support'),
    path('book/<int:parking_id>/', views.book_slot, name='book_slot'),
]



