import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash, get_user_model
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.mail import send_mail

import razorpay

from .decorators import role_required
from .models import Parking, Booking, Profile, ParkingSlot, OwnerProfile, SupportTicket
from .forms import BookingForm, ProfileForm


# ══════════════════════════════════════════════════════════════════
# RAZORPAY
# ══════════════════════════════════════════════════════════════════

def create_order(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount")) * 100  # ₹ to paise
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })
        return JsonResponse({
            "order_id": payment["id"],
            "amount": payment["amount"],
            "key": settings.RAZORPAY_KEY_ID
        })


def confirm_booking(request):
    if request.method == "POST":
        from .models import Slot
        slot = Slot.objects.get(id=request.POST.get("slot_id"))
        Booking.objects.create(
            user=request.user,
            slot=slot,
            start_time=request.POST.get("start_time"),
            end_time=request.POST.get("end_time"),
            payment_id=request.POST.get("payment_id"),
            amount=slot.price,
            status="confirmed"
        )
        slot.is_occupied = True
        slot.save()
        return JsonResponse({"status": "success"})


def payment_success(request):
    data = json.loads(request.body)
    from .models import Payment
    payment = Payment.objects.get(razorpay_order_id=data['razorpay_order_id'])
    payment.razorpay_payment_id = data['razorpay_payment_id']
    payment.razorpay_signature = data['razorpay_signature']
    payment.status = "success"
    payment.save()
    booking = payment.booking
    booking.status = "success"
    booking.save()
    return JsonResponse({"status": "ok"})


def payment_failed(request):
    from .models import Payment
    payment = Payment.objects.filter(user=request.user).last()
    if payment:
        payment.status = "failed"
        payment.save()
        booking = payment.booking
        booking.status = "failed"
        booking.save()
    return JsonResponse({"status": "failed"})


# ══════════════════════════════════════════════════════════════════
# OWNER VIEWS
# ══════════════════════════════════════════════════════════════════

@role_required(allowed_roles=["parkingowner"])
def ownerDashboardView(request):
    now = timezone.now()
    UserModel = get_user_model()

    total_slots    = ParkingSlot.objects.count()
    occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
    available_slots = ParkingSlot.objects.filter(status='available').count()

    earnings_today = Booking.objects.filter(
        start_time__date=now.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    slots = ParkingSlot.objects.select_related('parking').all()[:48]
    recent_bookings = Booking.objects.select_related('user', 'parking').order_by('-start_time')[:6]

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

    total_users     = UserModel.objects.filter(role='user').count()
    new_users_today = UserModel.objects.filter(created_at__date=now.date(), role='user').count()
    pending_approvals = Booking.objects.filter(status='active').count()
    occupancy_rate  = round((occupied_slots / total_slots * 100), 1) if total_slots > 0 else 0

    completed  = Booking.objects.filter(status='completed', end_time__isnull=False)
    avg_duration = 0
    if completed.exists():
        total_mins = sum([
            (b.end_time - b.start_time).total_seconds() / 60
            for b in completed if b.end_time
        ])
        avg_duration = round(total_mins / completed.count() / 60, 1)

    revenue_goal_pct = min(round(week_total / 50000 * 100), 100)

    query = request.GET.get('q', '')
    search_results = None
    if query:
        search_results = Parking.objects.filter(
            Q(name__icontains=query) | Q(location__icontains=query)
        )

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


def manage_parking(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    parkings = Parking.objects.all()
    if query:
        parkings = parkings.filter(Q(name__icontains=query) | Q(location__icontains=query))
    if status_filter == 'active':
        parkings = parkings.filter(status='active')
    elif status_filter == 'closed':
        parkings = parkings.filter(status='closed')
    return render(request, "parking/owner/manage_parking.html", {
        "parkings": parkings, "query": query, "status_filter": status_filter,
    })


def add_parking(request):
    if request.method == 'POST':
        Parking.objects.create(
            name=request.POST.get('name'),
            location=request.POST.get('location'),
            price_per_hour=request.POST.get('price_per_hour'),
            total_slots=request.POST.get('total_slots'),
            available_slots=request.POST.get('total_slots'),
            status=request.POST.get('status', 'active'),
        )
        messages.success(request, 'Parking added successfully!')
        return redirect('parking:manage_parking')
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
        slots = slots.filter(Q(slot_number__icontains=query) | Q(parking__name__icontains=query))
    if status_filter == 'available':
        slots = slots.filter(status='available')
    elif status_filter == 'occupied':
        slots = slots.filter(status='occupied')
    parkings = Parking.objects.filter(status='active')
    return render(request, "parking/owner/manage_slots.html", {
        "slots": slots, "parkings": parkings, "query": query, "status_filter": status_filter,
    })


def add_slot(request):
    if request.method == 'POST':
        parking = get_object_or_404(Parking, id=request.POST.get('parking'))
        ParkingSlot.objects.create(
            parking=parking,
            slot_number=request.POST.get('slot_number'),
            status=request.POST.get('status', 'available'),
        )
        messages.success(request, 'Slot added successfully!')
        return redirect('parking:manage_slots')
    parkings = Parking.objects.filter(status='active')
    return render(request, 'parking/owner/add_slot.html', {'parkings': parkings})


def available_slots_json(request, parking_id):
    slots = ParkingSlot.objects.filter(parking_id=parking_id, status='available').values('slot_number')
    return JsonResponse({"slots": [{"id": s['slot_number']} for s in slots]})


def edit_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    if request.method == 'POST':
        slot.parking = get_object_or_404(Parking, id=request.POST.get('parking'))
        slot.slot_number = request.POST.get('slot_number')
        slot.status = request.POST.get('status', 'available')
        slot.save()
        messages.success(request, 'Slot updated successfully!')
        return redirect('parking:manage_slots')
    parkings = Parking.objects.filter(status='active')
    return render(request, 'parking/owner/edit_slot.html', {'slot': slot, 'parkings': parkings})


def delete_slot(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    slot.delete()
    messages.success(request, 'Slot deleted successfully!')
    return redirect('parking:manage_slots')


def bookings(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    all_bookings = Booking.objects.select_related('user', 'parking').all().order_by('-start_time')
    if query:
        all_bookings = all_bookings.filter(
            Q(slot_number__icontains=query) |
            Q(parking__name__icontains=query) |
            Q(user__email__icontains=query)
        )
    if status_filter == 'active':
        all_bookings = all_bookings.filter(status='active')
    elif status_filter == 'completed':
        all_bookings = all_bookings.filter(status='completed')
    elif status_filter == 'cancelled':
        all_bookings = all_bookings.filter(status='cancelled')
    return render(request, "parking/owner/bookings.html", {
        "bookings": all_bookings, "query": query, "status_filter": status_filter,
    })


def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    try:
        vehicle_number = booking.user.profile.vehicle_number or '—'
    except Exception:
        vehicle_number = '—'
    return render(request, "parking/owner/booking_detail.html", {
        "booking": booking, "vehicle_number": vehicle_number,
    })


def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.success(request, 'Booking deleted successfully!')
    return redirect('parking:bookings')


def earnings(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    now = timezone.now()

    base = Booking.objects.filter(amount__gt=0)
    if query:
        base = base.filter(parking__name__icontains=query)
    if date_from:
        base = base.filter(start_time__date__gte=date_from)
    if date_to:
        base = base.filter(start_time__date__lte=date_to)

    total_earnings  = Booking.objects.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or 0
    today_earnings  = Booking.objects.filter(amount__gt=0, start_time__date=now.date()).aggregate(total=Sum('amount'))['total'] or 0
    week_start      = now.date() - timedelta(days=7)
    weekly_earnings = Booking.objects.filter(amount__gt=0, start_time__date__gte=week_start).aggregate(total=Sum('amount'))['total'] or 0

    earnings_data = base.values('start_time__date', 'parking__name').annotate(
        total_amount=Sum('amount')
    ).order_by('-start_time__date')

    return render(request, "parking/owner/earnings.html", {
        "earnings": earnings_data,
        "total": total_earnings, "today": today_earnings, "week": weekly_earnings,
        "query": query, "date_from": date_from, "date_to": date_to,
    })


def reports(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    now = timezone.now()

    total_bookings = Booking.objects.count()
    total_revenue  = Booking.objects.aggregate(total=Sum('amount'))['total'] or 0
    active_slots   = ParkingSlot.objects.filter(status='available').count()

    base = Booking.objects.all()
    if query:
        base = base.filter(start_time__date__icontains=query)
    if date_from:
        base = base.filter(start_time__date__gte=date_from)
    if date_to:
        base = base.filter(start_time__date__lte=date_to)

    reports_data = base.values('start_time__date').annotate(
        total_bookings=Count('id'), total_revenue=Sum('amount')
    ).order_by('-start_time__date')

    return render(request, "parking/owner/reports.html", {
        "reports": reports_data,
        "bookings": total_bookings, "revenue": total_revenue, "slots": active_slots,
        "query": query, "date_from": date_from, "date_to": date_to,
    })


def settings_view(request):
    user = request.user
    owner_profile, _ = OwnerProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        full_name = request.POST.get('name', '').strip()
        parts = full_name.split()
        user.firstname = parts[0] if parts else ''
        user.lastname  = ' '.join(parts[1:]) if len(parts) > 1 else ''

        new_email = request.POST.get('email', '').strip()
        if new_email and new_email != user.email:
            user.email = new_email

        owner_profile.phone         = request.POST.get('phone', '').strip()
        owner_profile.business_name = request.POST.get('business', '').strip()
        owner_profile.save()

        password = request.POST.get('password', '').strip()
        confirm  = request.POST.get('confirm_password', '').strip()

        if password:
            if password == confirm:
                user.set_password(password)
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated successfully!')
            else:
                messages.error(request, 'Passwords do not match!')
                return render(request, 'parking/owner/settings.html', {
                    'user': user, 'owner_profile': owner_profile,
                })

        user.save()
        messages.success(request, 'Settings saved successfully!')
        return redirect('parking:owner_dashboard')

    return render(request, "parking/owner/settings.html", {
        "user": user, "owner_profile": owner_profile,
    })


def logout_view(request):
    logout(request)
    return redirect("login")


# ══════════════════════════════════════════════════════════════════
# USER VIEWS
# ══════════════════════════════════════════════════════════════════

@role_required(allowed_roles=["user"])
def userDashboardView(request):
    user = request.user
    bookings_qs = Booking.objects.filter(user=user)
    query = request.GET.get('q')
    search_results = None
    if query:
        search_results = Parking.objects.filter(
            Q(name__icontains=query) | Q(location__icontains=query)
        )

    total_bookings  = bookings_qs.count()
    active_booking  = bookings_qs.filter(status='active').first()
    active_sessions = bookings_qs.filter(status='active').count()
    upcoming_booking = bookings_qs.filter(status='upcoming').first()
    total_spent     = bookings_qs.aggregate(total=Sum('amount'))['total'] or 0

    now = timezone.now()
    monthly_spent = bookings_qs.filter(
        start_time__month=now.month, start_time__year=now.year
    ).aggregate(total=Sum('amount'))['total'] or 0

    recent_bookings = bookings_qs.order_by('-id')[:5]

    return render(request, 'parking/user/user_dashboard.html', {
        "total_bookings": total_bookings,
        "active_booking": active_booking,
        "active_sessions": active_sessions,
        "upcoming_booking": upcoming_booking,
        "total_spent": total_spent,
        "monthly_spent": monthly_spent,
        "avg_park_time": "2.5",
        "recent_bookings": recent_bookings,
        "search_results": search_results,
        "query": query,
    })


def find_parking(request):
    query = request.GET.get('q')
    parkings = Parking.objects.all()
    if query:
        parkings = parkings.filter(Q(name__icontains=query) | Q(location__icontains=query))
    return render(request, 'parking/user/find_parking.html', {'parkings': parkings})


@login_required
def my_bookings(request):
    bookings_qs = Booking.objects.filter(user=request.user).order_by('-start_time')
    q = request.GET.get('q', '').strip()
    if q:
        bookings_qs = bookings_qs.filter(
            Q(parking__name__icontains=q) |
            Q(parking__location__icontains=q) |
            Q(slot_number__icontains=q)
        )
    status = request.GET.get('status', 'all')
    if status == 'active':
        bookings_qs = bookings_qs.filter(status='active')
    elif status == 'completed':
        bookings_qs = bookings_qs.filter(status='completed')
    return render(request, "parking/user/my_bookings.html", {"bookings": bookings_qs})


@login_required
def active_parking(request):
    q = request.GET.get('q', '').strip()
    active = Booking.objects.filter(user=request.user, status='active').select_related('parking')
    if q:
        active = active.filter(
            Q(parking__name__icontains=q) |
            Q(parking__location__icontains=q) |
            Q(slot_number__icontains=q)
        )
    try:
        vehicle_number = request.user.profile.vehicle_number or '—'
    except Exception:
        vehicle_number = '—'
    for b in active:
        b.vehicle_number = vehicle_number
    return render(request, "parking/user/active_parking.html", {"active": active})


def payment_history(request):
    payments = [
        {"date": "15 Mar 2026", "parking": "Central Plaza Parking", "method": "UPI",         "amount": 80,  "status": "Paid"},
        {"date": "14 Mar 2026", "parking": "City Mall Parking",     "method": "Credit Card",  "amount": 60,  "status": "Paid"},
        {"date": "12 Mar 2026", "parking": "Airport Parking Zone",  "method": "Wallet",       "amount": 120, "status": "Paid"},
    ]
    return render(request, "parking/user/payment_history.html", {"payments": payments})


def saved_locations_view(request):
    locations = Parking.objects.all()
    return render(request, 'parking/user/saved_locations.html', {'locations': locations})


def notifications(request):
    notifications_list = [
        {"title": "Booking Confirmed",   "message": "Your parking slot A12 at Central Plaza has been successfully booked.", "time": "10 minutes ago"},
        {"title": "Parking Ending Soon", "message": "Your parking session at Airport Parking Zone will end in 30 minutes.", "time": "1 hour ago"},
        {"title": "New Parking Available","message": "A new parking space has been added near MG Road.",                   "time": "Today"},
    ]
    return render(request, "parking/user/notifications.html", {"notifications": notifications_list})


@login_required
def help_support(request):
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'parking/user/help_support.html', {'support_tickets': tickets})


@login_required
def submit_support(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    required = ['name', 'email', 'category', 'subject', 'message']
    for field in required:
        if not data.get(field, '').strip():
            return JsonResponse({'success': False, 'error': f'Missing field: {field}'}, status=400)

    if len(data['message'].strip()) < 20:
        return JsonResponse({'success': False, 'error': 'Message too short'}, status=400)

    ticket = SupportTicket.objects.create(
        user     = request.user,
        name     = data['name'].strip(),
        email    = data['email'].strip(),
        category = data['category'].strip(),
        priority = data.get('priority', 'Medium').strip(),
        subject  = data['subject'].strip(),
        message  = data['message'].strip(),
        status   = 'Open',
    )

    try:
        send_mail(
            subject=f'[{ticket.ticket_id}] Support Request Received — {ticket.subject}',
            message=(
                f"Hi {ticket.name},\n\n"
                f"We've received your support request.\n\n"
                f"Ticket ID : {ticket.ticket_id}\n"
                f"Category  : {ticket.category}\n"
                f"Priority  : {ticket.priority}\n"
                f"Subject   : {ticket.subject}\n\n"
                f"Message:\n{ticket.message}\n\n"
                f"Our team will respond within 2–4 hours on business days.\n\n"
                f"— FindMyParking Support\n"
                f"support@findmyparking.com | +91 98765 43210"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ticket.email],
            fail_silently=True,
        )
        send_mail(
            subject=f'[NEW TICKET {ticket.ticket_id}] {ticket.subject} [{ticket.priority}]',
            message=(
                f"New ticket from {ticket.name} ({ticket.email})\n\n"
                f"Ticket ID : {ticket.ticket_id}\n"
                f"Category  : {ticket.category}\n"
                f"Priority  : {ticket.priority}\n"
                f"Subject   : {ticket.subject}\n\n"
                f"Message:\n{ticket.message}\n\n"
                f"Created: {ticket.created_at}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
    except Exception:
        pass

    return JsonResponse({'success': True, 'ticket_id': ticket.ticket_id})


@login_required
def book_slot(request, parking_id):
    parking = get_object_or_404(Parking, id=parking_id)
    if parking.available_slots <= 0:
        return redirect('parking:find_parking')

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user    = request.user
            booking.parking = parking
            booking.status  = 'active'

            start = form.cleaned_data['start_time']
            end   = form.cleaned_data['end_time']
            if hasattr(start, 'tzinfo') and start.tzinfo is not None:
                from django.utils.timezone import localtime
                start = localtime(start)
                end   = localtime(end)

            diff_hours    = (end - start).total_seconds() / 3600
            booking.amount = int(diff_hours * parking.price_per_hour)
            booking.save()

            parking.available_slots -= 1
            parking.save()
            return redirect('parking:my_bookings')
    else:
        form = BookingForm()

    return render(request, "parking/user/book_slot.html", {"form": form, "parking": parking})


@login_required
def profile_settings(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=user)
        if form.is_valid():
            profile.phone          = form.cleaned_data.get('phone')
            profile.vehicle_number = form.cleaned_data.get('vehicle_number')
            profile.save()

            full_name = form.cleaned_data.get('full_name', '').strip()
            parts = full_name.split()
            user.firstname = parts[0] if parts else ''
            user.lastname  = ' '.join(parts[1:]) if len(parts) > 1 else ''
            user.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('parking:user_dashboard')
    else:
        form = ProfileForm(instance=profile, user=user)

    return render(request, 'parking/user/profile_settings.html', {
        'user': user, 'profile': profile, 'form': form,
    })


@role_required(allowed_roles=["parkingowner"])
def owner_support_tickets(request):
    status_filter = request.GET.get('status', 'all')
    tickets = SupportTicket.objects.all().order_by('-created_at')

    if status_filter == 'open':
        tickets = tickets.filter(status='Open')
    elif status_filter == 'resolved':
        tickets = tickets.filter(status='Resolved')
    elif status_filter == 'closed':
        tickets = tickets.filter(status='Closed')

    counts = {
    'all':         SupportTicket.objects.count(),
    'open':        SupportTicket.objects.filter(status='Open').count(),
    'in_progress': SupportTicket.objects.filter(status='In Progress').count(),
    'resolved':    SupportTicket.objects.filter(status='Resolved').count(),
    'closed':      SupportTicket.objects.filter(status='Closed').count(),
}

    return render(request, 'parking/owner/support_tickets.html', {
        'tickets': tickets,
        'status_filter': status_filter,
        'counts': counts,
    })


@role_required(allowed_roles=["parkingowner"])
def owner_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    return render(request, 'parking/owner/ticket_detail.html', {'ticket': ticket})


@role_required(allowed_roles=["parkingowner"])
def owner_ticket_update(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    if request.method == 'POST':
        ticket.status = request.POST.get('status', ticket.status)
        ticket.save()

        # Notify user by email
        try:
            send_mail(
                subject=f'[{ticket.ticket_id}] Your ticket status has been updated',
                message=(
                    f"Hi {ticket.name},\n\n"
                    f"Your support ticket status has been updated.\n\n"
                    f"Ticket ID : {ticket.ticket_id}\n"
                    f"Subject   : {ticket.subject}\n"
                    f"New Status: {ticket.status}\n\n"
                    f"— FindMyParking Support"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ticket.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, f'Ticket {ticket.ticket_id} updated to {ticket.status}')
        return redirect('parking:owner_support_tickets')

    return redirect('parking:owner_ticket_detail', ticket_id=ticket_id)