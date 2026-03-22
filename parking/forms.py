from django import forms
from .models import Booking

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