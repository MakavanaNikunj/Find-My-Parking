from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Parking(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    price_per_hour = models.IntegerField()
    total_slots = models.IntegerField()
    available_slots = models.IntegerField()

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)

    slot_number = models.CharField(max_length=10)

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    duration = models.CharField(max_length=50, blank=True)  # ✅ ADD THIS
    amount = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.user} - {self.parking} - {self.slot_number}"
    

    