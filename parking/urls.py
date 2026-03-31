from django.urls import path
from . import views

app_name = "parking"

urlpatterns = [

    # ═══════════════════════════════════
    # OWNER
    # ═══════════════════════════════════
    path('owner/',                              views.ownerDashboardView,     name='owner_dashboard'),

    path('add-parking/',                        views.add_parking,            name='add_parking'),
    path('manage-parking/',                     views.manage_parking,         name='manage_parking'),
    path('edit-parking/<int:parking_id>/',      views.edit_parking,           name='edit_parking'),
    path('delete-parking/<int:parking_id>/',    views.delete_parking,         name='delete_parking'),

    path('manage-slots/',                       views.manage_slots,           name='manage_slots'),
    path('add-slot/',                           views.add_slot,               name='add_slot'),
    path('edit-slot/<int:slot_id>/',            views.edit_slot,              name='edit_slot'),
    path('delete-slot/<int:slot_id>/',          views.delete_slot,            name='delete_slot'),

    path('bookings/',                           views.bookings,               name='bookings'),
    path('booking-detail/<int:booking_id>/',    views.booking_detail,         name='booking_detail'),
    path('delete-booking/<int:booking_id>/',    views.delete_booking,         name='delete_booking'),

    path('earnings/',                           views.earnings,               name='earnings'),
    path('reports/',                            views.reports,                name='reports'),
    path('settings/',                           views.settings_view,          name='settings'),
    path('logout/',                             views.logout_view,            name='logout'),

    path('support-tickets/',                        views.owner_support_tickets,  name='owner_support_tickets'),
    path('support-tickets/<str:ticket_id>/',        views.owner_ticket_detail,    name='owner_ticket_detail'),
    path('support-tickets/<str:ticket_id>/update/', views.owner_ticket_update,    name='owner_ticket_update'),

    # ═══════════════════════════════════
    # USER
    # ═══════════════════════════════════
    path('user/',                               views.userDashboardView,      name='user_dashboard'),

    path('find-parking/',                       views.find_parking,           name='find_parking'),
    path('book/<int:parking_id>/',              views.book_slot,              name='book_slot'),
    path('my-bookings/',                        views.my_bookings,            name='my_bookings'),
    path('active-parking/',                     views.active_parking,         name='active_parking'),
    path('payment-history/',                    views.payment_history,        name='payment_history'),
    path('saved-locations/',                    views.saved_locations_view,   name='saved_locations'),
    path('notifications/',                      views.notifications,          name='notifications'),
    path('profile-settings/',                   views.profile_settings,       name='profile_settings'),
    path('help-support/',                       views.help_support,           name='help_support'),
    path('help-support/submit/',                views.submit_support,         name='submit_support'),

    # AJAX
    path('<int:parking_id>/slots/',             views.available_slots_json,   name='available_slots'),

    # ═══════════════════════════════════
    # RAZORPAY  (all AJAX / JSON)
    # ═══════════════════════════════════
    path('create-order/',                       views.create_order,           name='create_order'),
    path('payment-success/',                    views.payment_success,        name='payment_success'),
    path('payment-failed/',                     views.payment_failed,         name='payment_failed'),
]