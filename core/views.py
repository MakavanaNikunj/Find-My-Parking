from django.shortcuts import render , redirect,HttpResponse
from .forms import UserSignupForm,UserLoginForm
from .models import User
from django.contrib.auth import authenticate,login,logout

# Create your views here.

def userSignupView(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')  # temporary redirect
    else:
        form = UserSignupForm()

    return render(request, 'core/signup.html', {'form': form})

def Home(request):
    return render(request , "core/home.html")

def adminPanel(request):
    return render(request , 'core/admin.html')


from django.contrib import messages

def userLoginView(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = authenticate(request, email=email, password=password)
            

            if user is not None:
                login(request, user)

                role = (user.role or "").strip().lower()

                if role == "parkingowner":
                    return redirect('parking:owner_dashboard')

                elif role == "user":
                    return redirect("parking:user_dashboard")

                else:
                    messages.error(request, "Invalid role assigned.")
                    return redirect("login")

            else:
                messages.error(request, "Invalid email or password")

    else:
        form = UserLoginForm()

    return render(request, "core/login.html", {"form": form})



def userLogoutView(request):
    logout(request)
    return redirect("home")








