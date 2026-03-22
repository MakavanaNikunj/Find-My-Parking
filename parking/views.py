from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from .models import Parking, Booking
from .forms import BookingForm
from .models import Booking
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q

# Owner Dashboard Create your views here.
# @login_required(login_url="/core/login/") #to check visit the dashboard page the user or owner are login
@role_required(allowed_roles=["parkingowner"])
def ownerDashboardView(request):
    return render(request,'parking/owner/owner_dashboard.html')

# @login_required(login_url="/core/login/")

@role_required(allowed_roles=["user"])


def userDashboardView(request):
    user = request.user
    bookings = Booking.objects.filter(user=user)

    query = request.GET.get('q')

    search_results = None

    if query:
        search_results = Parking.objects.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query)
        )

    total_bookings = bookings.count()
    active_booking = bookings.filter(status='active').first()
    active_sessions = bookings.filter(status='active').count()
    upcoming_booking = bookings.filter(status='upcoming').first()

    total_spent = bookings.aggregate(total=Sum('amount'))['total'] or 0

    now = timezone.now()
    monthly_spent = bookings.filter(
        start_time__month=now.month,
        start_time__year=now.year
    ).aggregate(total=Sum('amount'))['total'] or 0

    avg_park_time = "2.5"
    recent_bookings = bookings.order_by('-id')[:5]

    context = {
        "total_bookings": total_bookings,
        "active_booking": active_booking,
        "active_sessions": active_sessions,
        "upcoming_booking": upcoming_booking,
        "total_spent": total_spent,
        "monthly_spent": monthly_spent,
        "avg_park_time": avg_park_time,
        "recent_bookings": recent_bookings,
        "search_results": search_results,
        "query": query,
    }

    return render(request, 'parking/user/user_dashboard.html', context)

def add_parking(request):
    return render(request, 'owner/add_parking.html')

def manage_parking(request):

    parkings = [
        {
            "name": "Central Plaza Parking",
            "location": "Downtown City",
            "slots": 120,
            "price": 40,
            "status": "Active"
        },
        {
            "name": "Airport Parking Zone",
            "location": "Airport Road",
            "slots": 200,
            "price": 60,
            "status": "Active"
        },
        {
            "name": "Mall Parking Area",
            "location": "City Mall",
            "slots": 80,
            "price": 30,
            "status": "Closed"
        }
    ]

    return render(request,"parking/owner/manage_parking.html",{"parkings":parkings})


def manage_slots(request):

    slots = [
        {"number": 1, "parking": "Central Plaza Parking", "status": "Available"},
        {"number": 2, "parking": "Central Plaza Parking", "status": "Occupied"},
        {"number": 3, "parking": "Airport Parking Zone", "status": "Available"},
        {"number": 4, "parking": "Airport Parking Zone", "status": "Occupied"},
        {"number": 5, "parking": "Mall Parking Area", "status": "Available"},
        {"number": 6, "parking": "Mall Parking Area", "status": "Occupied"},
    ]

    return render(request, "parking/owner/manage_slots.html", {"slots": slots})


def bookings(request):

    bookings = [
        {
            "vehicle": "MH 12 AB 3456",
            "user": "Rahul Sharma",
            "slot": "A-07",
            "time": "10:00 AM",
            "status": "Active"
        },
        {
            "vehicle": "GJ 01 CD 7890",
            "user": "Priya Patel",
            "slot": "B-03",
            "time": "09:30 AM",
            "status": "Pending"
        },
        {
            "vehicle": "KA 05 EF 2234",
            "user": "Amit Kumar",
            "slot": "C-11",
            "time": "08:45 AM",
            "status": "Completed"
        }
    ]

    return render(request, "parking/owner/bookings.html", {"bookings": bookings})


def earnings(request):

    earnings_data = [
        {"date": "10 Mar 2026", "parking": "Central Plaza Parking", "amount": 1200},
        {"date": "09 Mar 2026", "parking": "Airport Parking Zone", "amount": 1800},
        {"date": "08 Mar 2026", "parking": "Mall Parking Area", "amount": 900},
    ]

    total_earnings = 3900
    today_earnings = 1200
    week_earnings = 2700

    return render(request,"parking/owner/earnings.html",{
        "earnings":earnings_data,
        "total":total_earnings,
        "today":today_earnings,
        "week":week_earnings
    })



def reports(request):

    reports = [
        {"date":"10 Mar 2026","bookings":45,"revenue":1200},
        {"date":"09 Mar 2026","bookings":52,"revenue":1800},
        {"date":"08 Mar 2026","bookings":38,"revenue":900},
        {"date":"07 Mar 2026","bookings":41,"revenue":1100},
    ]

    total_bookings = 176
    total_revenue = 5000
    active_slots = 48

    return render(request,"parking/owner/reports.html",{
        "reports":reports,
        "bookings":total_bookings,
        "revenue":total_revenue,
        "slots":active_slots
    })

def settings(request):
    return render(request,"parking/owner/settings.html")

def logout_view(request):
    logout(request)
    return redirect("login")



# User Dashboard Create your views here.



from django.db.models import Q

def find_parking(request):
    query = request.GET.get('q')

    parkings = Parking.objects.all()

    if query:
        parkings = parkings.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query)
        )

    return render(request, 'parking/user/find_parking.html', {
        'parkings': parkings
    })

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-start_time')

    return render(request, "parking/user/my_bookings.html", {
        "bookings": bookings
    })


def active_parking(request):

    active_parkings = [
        {
            "parking": "Central Plaza Parking",
            "location": "MG Road",
            "slot": "A12",
            "start": "10:00 AM",
            "end": "12:00 PM",
            "vehicle": "GJ01AB1234",
            "price": 80
        },
        {
            "parking": "Airport Parking Zone",
            "location": "Airport Road",
            "slot": "C22",
            "start": "02:00 PM",
            "end": "05:00 PM",
            "vehicle": "GJ05XY7890",
            "price": 150
        }
    ]

    return render(request,"parking/user/active_parking.html",{
        "active": active_parkings
    })


def payment_history(request):

    payments = [
        {
            "date": "15 Mar 2026",
            "parking": "Central Plaza Parking",
            "method": "UPI",
            "amount": 80,
            "status": "Paid"
        },
        {
            "date": "14 Mar 2026",
            "parking": "City Mall Parking",
            "method": "Credit Card",
            "amount": 60,
            "status": "Paid"
        },
        {
            "date": "12 Mar 2026",
            "parking": "Airport Parking Zone",
            "method": "Wallet",
            "amount": 120,
            "status": "Paid"
        }
    ]

    return render(request,"parking/user/payment_history.html",{
        "payments": payments
    })

def saved_locations_view(request):
    locations = Parking.objects.all()  # or your model

    return render(request, 'parking/user/saved_locations.html', {
        'locations': locations
    })


def notifications(request):

    notifications_list = [
        {
            "title": "Booking Confirmed",
            "message": "Your parking slot A12 at Central Plaza has been successfully booked.",
            "time": "10 minutes ago"
        },
        {
            "title": "Parking Ending Soon",
            "message": "Your parking session at Airport Parking Zone will end in 30 minutes.",
            "time": "1 hour ago"
        },
        {
            "title": "New Parking Available",
            "message": "A new parking space has been added near MG Road.",
            "time": "Today"
        }
    ]

    return render(request,"parking/user/notifications.html",{
        "notifications": notifications_list
    })


def profile_settings(request):

    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+91 9876543210",
        "vehicle": "GJ01AB1234"
    }

    return render(request,"parking/user/profile_settings.html",{
        "user": user_data
    })


def help_support(request):

    faqs = [
        {
            "question": "How do I book a parking slot?",
            "answer": "Go to Find Parking page, choose a parking location and click Book Slot."
        },
        {
            "question": "How do I cancel my booking?",
            "answer": "Go to My Bookings section and click Cancel on the booking."
        },
        {
            "question": "How can I update my vehicle number?",
            "answer": "Open Profile Settings and update your vehicle information."
        },
        {
            "question": "Who do I contact for payment issues?",
            "answer": "Please contact support using the form below or email support@findmyparking.com"
        }
    ]

    return render(request,"parking/user/help_support.html",{
        "faqs": faqs
    })



@login_required
def book_slot(request, parking_id):
    parking = get_object_or_404(Parking, id=parking_id)

    if parking.available_slots <= 0:
        return redirect('parking:find_parking')

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.parking = parking
            booking.amount = parking.price_per_hour
            booking.status = 'active'
            booking.save()

            parking.available_slots -= 1
            parking.save()

            return redirect('parking:my_bookings')
    else:
        form = BookingForm()

    return render(request, "parking/user/book_slot.html", {
        "form": form,
        "parking": parking
    })
  
