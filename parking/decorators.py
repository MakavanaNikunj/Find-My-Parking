from django.shortcuts import redirect,HttpResponse,reverse
from django.contrib import messages


def role_required(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request,*args,**kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role in allowed_roles:
                return view_func(request,*args,**kwargs)
            else:
                return HttpResponse("you are NOt Authorised User")
        return wrapper_func
    return decorator    