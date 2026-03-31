from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


# =========================
# PARKING MODEL
# =========================
class Parking(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('closed', 'Closed'),
    )

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    price_per_hour = models.IntegerField()
    total_slots = models.IntegerField()
    available_slots = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return self.name


# =========================
# PARKING SLOT MODEL
# =========================
class ParkingSlot(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
    )

    parking = models.ForeignKey(Parking, on_delete=models.CASCADE, related_name='slots')
    slot_number = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.slot_number} - {self.parking.name}"


# =========================
# USER PROFILE
# =========================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return str(self.user)


# =========================
# OWNER PROFILE
# =========================
class OwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    business_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return str(self.user)


# =========================
# BOOKING MODEL
# =========================
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending',   'Pending'),    # created, awaiting payment
        ('active',    'Active'),     # payment success, slot booked
        ('completed', 'Completed'),  # session ended
        ('cancelled', 'Cancelled'),  # cancelled by user
        ('failed',    'Failed'),     # payment failed
    )

    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    parking     = models.ForeignKey(Parking, on_delete=models.CASCADE)
    slot_number = models.CharField(max_length=10)

    start_time  = models.DateTimeField(default=timezone.now)
    end_time    = models.DateTimeField(null=True, blank=True)

    duration    = models.CharField(max_length=50, blank=True)
    amount      = models.IntegerField(default=0)

    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time:
            time_diff     = self.end_time - self.start_time
            total_minutes = int(time_diff.total_seconds() // 60)

            hours   = total_minutes // 60
            minutes = total_minutes % 60
            self.duration = f"{hours}h {minutes}m"

            if not self.amount:
                hourly_rate  = self.parking.price_per_hour
                total_hours  = total_minutes / 60
                self.amount  = int(total_hours * hourly_rate)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.parking} - Slot {self.slot_number}"


# =========================
# PAYMENT MODEL
# =========================
class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed',  'Failed'),
    )

    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")

    amount  = models.IntegerField()

    razorpay_order_id   = models.CharField(max_length=200)
    razorpay_payment_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True, null=True)

    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.status}"


# =========================
# SUPPORT TICKET
# =========================
class SupportTicket(models.Model):
    PRIORITY_CHOICES = [('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')]
    STATUS_CHOICES   = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name       = models.CharField(max_length=150)
    email      = models.EmailField()
    category   = models.CharField(max_length=100)
    priority   = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    subject    = models.CharField(max_length=255)
    message    = models.TextField()
    status     = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Open')
    ticket_id  = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.ticket_id}] {self.subject} — {self.status}"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import random, string
            self.ticket_id = 'TKT-' + ''.join(random.choices(string.digits, k=5))
        super().save(*args, **kwargs)


# =========================
# SIGNALS (AUTO PROFILE)
# =========================
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

UserModel = get_user_model()


@receiver(post_save, sender=UserModel)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
        OwnerProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=UserModel)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    if hasattr(instance, 'owner_profile'):
        instance.owner_profile.save()