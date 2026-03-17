from.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms


class UserSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['firstname','lastname','gender' , 'email' , 'role' ,'password1', 'password2','phone']
        widgets = {
            'password1':forms.PasswordInput(),
            'password2':forms.PasswordInput(),
            'gender' : forms.RadioSelect()
        }

class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())     