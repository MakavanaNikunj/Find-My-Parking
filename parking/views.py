from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from django.contrib.auth import logout
from .models import Parking, Booking,Profile,ParkingSlot
from .forms import BookingForm,ProfileForm
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages

# Owner Dashboard Create your views here.
# @login_required(login_url="/core/login/") #to check visit the dashboard page the user or owner are login
from django.contrib.auth import get_user_model
from datetime import timedelta

@role_required(allowed_roles=["parkingowner"])
def ownerDashboardView(request):
    now = timezone.now()
    UserModel = get_user_model()

    # ── STAT CARDS ──
    total_slots = ParkingSlot.objects.count()
    occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
    available_slots = ParkingSlot.objects.filter(status='available').count()

    earnings_today = Booking.objects.filter(
        start_time__date=now.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ── SLOT OVERVIEW ──
    slots = ParkingSlot.objects.select_related('parking').all()[:48]

    # ── RECENT BOOKINGS ──
    recent_bookings = Booking.objects.select_related(
        'user', 'parking'
    ).order_by('-start_time')[:6]

    # ── WEEKLY EARNINGS (last 7 days) ──
    weekly_data = []
    week_total = 0
    peak_day = 'N/A'
    peak_amt = 0

    for i in range(6, -1, -1):
        day = now.date() - timedelta(days=i)
        day_total = Booking.objects.filter(
            start_time__date=day
        ).aggregate(total=Sum('amount'))['total'] or 0

        week_total += day_total
        day_name = day.strftime('%a')
        weekly_data.append({'day': day_name, 'amount': day_total})

        if day_total > peak_amt:
            peak_amt = day_total
            peak_day = day.strftime('%A')

    # ── QUICK STATS ──
    total_users = UserModel.objects.filter(role='user').count()
    new_users_today = UserModel.objects.filter(
        created_at__date=now.date(), role='user'
    ).count()
    pending_approvals = Booking.objects.filter(status='active').count()

    occupancy_rate = round((occupied_slots / total_slots * 100), 1) if total_slots > 0 else 0

    # Avg park duration from completed bookings
    completed = Booking.objects.filter(
        status='completed', end_time__isnull=False
    )
    avg_duration = 0
    if completed.exists():
        total_mins = sum([
            (b.end_time - b.start_time).total_seconds() / 60
            for b in completed if b.end_time
        ])
        avg_duration = round(total_mins / completed.count() / 60, 1)

    # Revenue goal % (target: ₹50,000/week)
    revenue_goal_pct = min(round(week_total / 50000 * 100), 100)

    # ── SEARCH ──
    query = request.GET.get('q', '')
    search_results = None
    if query:
        search_results = Parking.objects.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query)
        )

    # ── OWNER PROFILE ──
    owner_profile, _ = OwnerProfile.objects.get_or_create(user=request.user)

    context = {
        'total_slots': total_slots,
        'occupied_slots': occupied_slots,
        'available_slots': available_slots,
        'earnings_today': earnings_today,
        'slots': slots,
        'recent_bookings': recent_bookings,
        'weekly_data': weekly_data,
        'weekly_total': week_total,
        'peak_day': peak_day,
        'total_users': total_users,
        'new_users_today': new_users_today,
        'pending_approvals': pending_approvals,
        'occupancy_rate': occupancy_rate,
        'avg_duration': avg_duration,
        'revenue_goal_pct': revenue_goal_pct,
        'owner_profile': owner_profile,
        'query': query,
        'search_results': search_results,
    }

    return render(request, 'parking/owner/owner_dashboard.html', context)

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

def manage_parking(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    parkings = Parking.objects.all()

    # Search
    if query:
        parkings = parkings.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query)
        )

    # Status filter
    if status_filter == 'active':
        parkings = parkings.filter(status='active')
    elif status_filter == 'closed':
        parkings = parkings.filter(status='closed')

    return render(request, "parking/owner/manage_parking.html", {
        "parkings": parkings,
        "query": query,
        "status_filter": status_filter,
    })


def add_parking(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        price_per_hour = request.POST.get('price_per_hour')
        total_slots = request.POST.get('total_slots')
        status = request.POST.get('status', 'active')

        Parking.objects.create(
            name=name,
            location=location,
            price_per_hour=price_per_hour,
            total_slots=total_slots,
            available_slots=total_slots,
            status=status,
        )
        messages.success(request, 'Parking added successfully!')
        return redirect('parking:manage_parking')  # ← back to manage page

    return render(request, 'parking/owner/add_parking.html')


def edit_parking(request, parking_id):
    parking = get_object_or_404(Parking, id=parking_id)

    if request.method == 'POST':
        parking.name = request.POST.get('name')
        parking.location = request.POST.get('location')
        parking.price_per_hour = request.POST.get('price_per_hour')
        parking.total_slots = request.POST.get('total_slots')
        parking.status = request.POST.get('status', 'active')
        parking.save()
        messages.success(request, 'Parking updated successfully!')
        return redirect('parking:manage_parking')

    return render(request, 'parking/owner/edit_parking.html', {'parking': parking})


def delete_parking(request, parking_id):
    parking = get_object_or_404(Parking, id=parking_id)
    parking.delete()
    messages.success(request, 'Parking deleted successfully!')
    return redirect('parking:manage_parking')



def manage_slots(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    slots = ParkingSlot.objects.select_related('parking').all()

    if query:
        slots = slots.filter(
            Q(slot_number__icontains=query) |
            Q(parking__name__icontains=query)
        )
    if status_filter == 'available':
        slots = slots.filter(status='available')
    elif status_filter == 'occupied':
        slots = slots.filter(status='occupied')

    parkings = Parking.objects.filter(status='active')  # ✅ needed for dropdown

    return render(request, "parking/owner/manage_slots.html", {
        "slots": slots,
        "parkings": parkings,  # ✅ pass to template
        "query": query,
        "status_filter": status_filter,
    })


def add_slot(request):
    if request.method == 'POST':
        parking_id = request.POST.get('parking')
        slot_number = request.POST.get('slot_number')
        status = request.POST.get('status', 'available')

        parking = get_object_or_404(Parking, id=parking_id)
        ParkingSlot.objects.create(
            parking=parking,
            slot_number=slot_number,
            status=status,
        )
        messages.success(request, 'Slot added successfully!')
        return redirect('parking:manage_slots')  # ← back to manage page

    parkings = Parking.objects.filter(status='active')
    return render(request, 'parking/owner/add_slot.html', {'parkings': parkings})

from django.http import JsonResponse

def available_slots_json(request, parking_id):
    slots = ParkingSlot.objects.filter(
        parking_id=parking_id,
        status='available'
    ).values('slot_number')
    
    data = [{"id": s['slot_number']} for s in slots]
    return JsonResponse({"slots": data})


def edit_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)

    if request.method == 'POST':
        parking_id = request.POST.get('parking')
        slot.parking = get_object_or_404(Parking, id=parking_id)
        slot.slot_number = request.POST.get('slot_number')
        slot.status = request.POST.get('status', 'available')
        slot.save()
        messages.success(request, 'Slot updated successfully!')
        return redirect('parking:manage_slots')

    parkings = Parking.objects.filter(status='active')
    return render(request, 'parking/owner/edit_slot.html', {
        'slot': slot,
        'parkings': parkings,
    })


def delete_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    slot.delete()
    messages.success(request, 'Slot deleted successfully!')
    return redirect('parking:manage_slots')


def bookings(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    all_bookings = Booking.objects.select_related('user', 'parking').all().order_by('-start_time')

    # Search by slot number, parking name, or user email
    if query:
        all_bookings = all_bookings.filter(
            Q(slot_number__icontains=query) |
            Q(parking__name__icontains=query) |
            Q(user__email__icontains=query)
        )

    # Status filter
    if status_filter == 'active':
        all_bookings = all_bookings.filter(status='active')
    elif status_filter == 'completed':
        all_bookings = all_bookings.filter(status='completed')
    elif status_filter == 'cancelled':
        all_bookings = all_bookings.filter(status='cancelled')

    return render(request, "parking/owner/bookings.html", {
        "bookings": all_bookings,
        "query": query,
        "status_filter": status_filter,
    })


def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Get vehicle number from Profile
    try:
        vehicle_number = booking.user.profile.vehicle_number or '—'
    except:
        vehicle_number = '—'

    return render(request, "parking/owner/booking_detail.html", {
        "booking": booking,
        "vehicle_number": vehicle_number,
    })


def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.success(request, 'Booking deleted successfully!')
    return redirect('parking:bookings')


from django.db.models import Sum, Q
from django.db.models.functions import TruncDate
from datetime import timedelta

def earnings(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    now = timezone.now()

    # Base queryset — only completed bookings have real earnings
    base = Booking.objects.filter(amount__gt=0)

    # Search by parking name
    if query:
        base = base.filter(parking__name__icontains=query)

    # Date range filter
    if date_from:
        base = base.filter(start_time__date__gte=date_from)
    if date_to:
        base = base.filter(start_time__date__lte=date_to)

    # ── STAT CARDS (always from full DB, no search/date filter) ──
    total_earnings = Booking.objects.filter(amount__gt=0).aggregate(
        total=Sum('amount'))['total'] or 0

    today_earnings = Booking.objects.filter(
        amount__gt=0,
        start_time__date=now.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    week_start = now.date() - timedelta(days=7)
    weekly_earnings = Booking.objects.filter(
        amount__gt=0,
        start_time__date__gte=week_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ── TABLE — group by date + parking ──
    earnings_data = base.values(
        'start_time__date',
        'parking__name'
    ).annotate(
        total_amount=Sum('amount')
    ).order_by('-start_time__date')

    return render(request, "parking/owner/earnings.html", {
        "earnings": earnings_data,
        "total": total_earnings,
        "today": today_earnings,
        "week": weekly_earnings,
        "query": query,
        "date_from": date_from,
        "date_to": date_to,
    })



from django.db.models import Sum, Count
from datetime import timedelta

def reports(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    now = timezone.now()

    # ── STAT CARDS (always full DB) ──
    total_bookings = Booking.objects.count()
    total_revenue = Booking.objects.aggregate(
        total=Sum('amount'))['total'] or 0
    active_slots = ParkingSlot.objects.filter(status='available').count()

    # ── TABLE queryset ──
    base = Booking.objects.all()

    # Search by date string
    if query:
        base = base.filter(start_time__date__icontains=query)

    # Date range filter
    if date_from:
        base = base.filter(start_time__date__gte=date_from)
    if date_to:
        base = base.filter(start_time__date__lte=date_to)

    # Group by date — count bookings + sum revenue per day
    reports_data = base.values(
        'start_time__date'
    ).annotate(
        total_bookings=Count('id'),
        total_revenue=Sum('amount')
    ).order_by('-start_time__date')

    return render(request, "parking/owner/reports.html", {
        "reports": reports_data,
        "bookings": total_bookings,
        "revenue": total_revenue,
        "slots": active_slots,
        "query": query,
        "date_from": date_from,
        "date_to": date_to,
    })

from .models import Parking, Booking, Profile, ParkingSlot, OwnerProfile
from django.contrib.auth import update_session_auth_hash

def settings(request):
    user = request.user
    owner_profile, created = OwnerProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # ── Name ──
        full_name = request.POST.get('name', '').strip()
        parts = full_name.split()
        user.firstname = parts[0] if parts else ''
        user.lastname = ' '.join(parts[1:]) if len(parts) > 1 else ''

        # ── Email ──
        new_email = request.POST.get('email', '').strip()
        if new_email and new_email != user.email:
            user.email = new_email

        # ── Phone + Business ──
        owner_profile.phone = request.POST.get('phone', '').strip()
        owner_profile.business_name = request.POST.get('business', '').strip()
        owner_profile.save()

        # ── Password ──
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()

        if password:
            if password == confirm:
                user.set_password(password)
                update_session_auth_hash(request, user)  # keeps user logged in
                messages.success(request, 'Password updated successfully!')
            else:
                messages.error(request, 'Passwords do not match!')
                return render(request, 'parking/owner/settings.html', {
                    'user': user,
                    'owner_profile': owner_profile,
                })

        user.save()
        messages.success(request, 'Settings saved successfully!')
        return redirect('parking:owner_dashboard')

    return render(request, "parking/owner/settings.html", {
        "user": user,
        "owner_profile": owner_profile,
    })

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

    # Search by parking name, location, or slot number
    q = request.GET.get('q', '').strip()
    if q:
        bookings = bookings.filter(
            Q(parking__name__icontains=q) |
            Q(parking__location__icontains=q) |
            Q(slot_number__icontains=q)
        )

    # Status filter
    status = request.GET.get('status', 'all')
    if status == 'active':
        bookings = bookings.filter(status='active')
    elif status == 'completed':
        bookings = bookings.filter(status='completed')

    return render(request, "parking/user/my_bookings.html", {"bookings": bookings})


@login_required
def active_parking(request):
    q = request.GET.get('q', '').strip()

    active = Booking.objects.filter(
        user=request.user,
        status='active'
    ).select_related('parking')

    if q:
        active = active.filter(
            Q(parking__name__icontains=q) |
            Q(parking__location__icontains=q) |
            Q(slot_number__icontains=q)
        )

    # Attach vehicle number from user profile to each booking
    try:
        vehicle_number = request.user.profile.vehicle_number or '—'
    except Exception:
        vehicle_number = '—'

    for b in active:
        b.vehicle_number = vehicle_number

    return render(request, "parking/user/active_parking.html", {
        "active": active
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
            booking.status = 'active'

            # ── Calculate amount correctly from naive local times ──
            start = form.cleaned_data['start_time']
            end   = form.cleaned_data['end_time']

            # Strip timezone info to avoid UTC conversion shifting the times
            if hasattr(start, 'tzinfo') and start.tzinfo is not None:
                from django.utils.timezone import localtime
                start = localtime(start)
                end   = localtime(end)

            diff_hours = (end - start).total_seconds() / 3600
            booking.amount = int(diff_hours * parking.price_per_hour)

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



def profile_settings(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=user)
        if form.is_valid():
            # Save phone and vehicle_number to Profile
            profile.phone = form.cleaned_data.get('phone')
            profile.vehicle_number = form.cleaned_data.get('vehicle_number')
            profile.save()

            # Save firstname/lastname to User
            full_name = form.cleaned_data.get('full_name', '').strip()
            parts = full_name.split()
            user.firstname = parts[0] if parts else ''
            user.lastname = ' '.join(parts[1:]) if len(parts) > 1 else ''
            user.save()

            from django.contrib import messages
            messages.success(request, 'Profile updated successfully!')
            return redirect('parking:user_dashboard')
    else:
        form = ProfileForm(instance=profile, user=user)

    context = {
        'user': user,
        'profile': profile,
        'form': form,
    }
    return render(request, 'parking/user/profile_settings.html', context)



  
