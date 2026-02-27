from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import role_required

# Create your views here.
# @login_required(login_url="/core/login/") #to check visit the dashboard page the user or owner are login
@role_required(allowed_roles=["parkingowner"])
def ownerDashboardView(request):
    return render(request,'parking/owner/owner_dashboard.html')

# @login_required(login_url="/core/login/")
@role_required(allowed_roles=["user"])
def userDashboardView(request):
    return render(request,'parking/user/user_dashboard.html')

  
