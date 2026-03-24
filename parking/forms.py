from django import forms
from django.utils import timezone
from .models import Booking, Profile


# =========================
# BOOKING FORM
# =========================
class BookingForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ['slot_number', 'end_time']

        widgets = {
            'slot_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Slot (A1, B2)'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            })
        }

    def clean_end_time(self):
        end_time = self.cleaned_data.get('end_time')

        if end_time:
            if end_time <= timezone.now():
                raise forms.ValidationError("End time must be in the future.")

        return end_time


# =========================
# PROFILE FORM
# =========================
class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )

    class Meta:
        model = Profile
        fields = ['phone', 'vehicle_number']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'vehicle_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter vehicle number'
            }),
        }

    # ✅ ADD HERE — replaces your old __init__
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            firstname = self.user.firstname or ''
            lastname = self.user.lastname or ''
            self.fields['full_name'].initial = f"{firstname} {lastname}".strip()

    # ✅ ADD HERE — replaces your old save
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            full_name = self.cleaned_data.get('full_name', '')
            parts = full_name.split()
            self.user.firstname = parts[0] if parts else ''
            self.user.lastname = ' '.join(parts[1:]) if len(parts) > 1 else ''
            self.user.save()
        if commit:
            profile.save()
        return profile