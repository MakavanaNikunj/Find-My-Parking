from django .urls import path
from . import views
app_name = "parking"

urlpatterns = [

    path('owner/',views.ownerDashboardView,name='owner_dashboard'),
    path('user/',views.userDashboardView,name='user_dashboard'),

]
