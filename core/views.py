from django.shortcuts import render , redirect
from .forms import UserSignupForm,userLoginView
from .models import User

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

def tempFile(request):
    return render(request , "core/temp.html")

def adminPanel(request):
    return render(request , 'core/admin.html')


