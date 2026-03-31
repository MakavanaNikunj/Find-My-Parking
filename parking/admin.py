from django.contrib import admin
from .models import Parking, Booking,ParkingSlot,Profile,OwnerProfile,Payment,SupportTicket

# Register your models here.
admin.site.register(Parking)
admin.site.register(Booking)
admin.site.register(ParkingSlot)
admin.site.register(Profile)
admin.site.register(OwnerProfile)
admin.site.register(Payment)
admin.site.register(SupportTicket)
