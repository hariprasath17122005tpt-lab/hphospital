"""
Health Packages / Health Checkup Packages
Apollo-style health checkup packages that patients can browse and book.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models.models import db, Patient, Appointment, Doctor, UserRole

health_packages_bp = Blueprint('health_packages', __name__, url_prefix='/health-packages')

# ── Health Packages Data ─────────────────────────────────────────────────────
HEALTH_PACKAGES = [
    {
        'id': 1,
        'name': 'Basic Health Checkup',
        'price': 999,
        'tests': ['CBC', 'Blood Sugar', 'Thyroid', 'Urine Analysis', 'Lipid Profile'],
        'description': 'Essential screening for general wellness',
        'duration': '2-3 hours',
        'fasting': True,
        'category': 'General',
        'icon': 'fa-heartbeat',
        'color': '#2563eb',
        'popular': False,
        'preparation': [
            'Fasting for 10-12 hours before the test',
            'Drink plenty of water the night before',
            'Avoid alcohol for 24 hours before the test',
            'Bring previous medical reports if available',
        ],
        'ideal_for': 'Adults aged 20-40 seeking annual wellness checks',
    },
    {
        'id': 2,
        'name': 'Comprehensive Health Checkup',
        'price': 2499,
        'tests': ['CBC', 'Blood Sugar', 'HbA1c', 'Thyroid Panel', 'Lipid Profile',
                  'Liver Function', 'Kidney Function', 'Urine Analysis', 'ECG', 'Chest X-Ray'],
        'description': 'Complete body screening with cardiac assessment',
        'duration': '4-5 hours',
        'fasting': True,
        'category': 'General',
        'icon': 'fa-stethoscope',
        'color': '#059669',
        'popular': True,
        'preparation': [
            'Fasting for 10-12 hours before the test',
            'Avoid heavy meals the previous night',
            'Wear comfortable, loose-fitting clothing',
            'Bring any current medications list',
            'Arrive 15 minutes before appointment',
        ],
        'ideal_for': 'Adults aged 30-50 looking for a thorough health evaluation',
    },
    {
        'id': 3,
        'name': 'Cardiac Risk Assessment',
        'price': 3499,
        'tests': ['ECG', 'ECHO', 'Lipid Profile', 'CRP', 'Homocysteine',
                  'Blood Sugar', 'HbA1c', 'Stress Test'],
        'description': 'Heart health evaluation with advanced markers',
        'duration': '5-6 hours',
        'fasting': True,
        'category': 'Cardiac',
        'icon': 'fa-heart',
        'color': '#dc2626',
        'popular': True,
        'preparation': [
            'Fasting for 10-12 hours before the test',
            'Avoid caffeine for 24 hours before stress test',
            'Wear comfortable shoes for treadmill test',
            'Inform doctor about current heart medications',
            'Do not skip regular medications unless advised',
        ],
        'ideal_for': 'Anyone with family history of heart disease or aged 40+',
    },
    {
        'id': 4,
        'name': 'Diabetes Screening',
        'price': 1499,
        'tests': ['Fasting Blood Sugar', 'Post-Prandial Sugar', 'HbA1c',
                  'Kidney Function', 'Lipid Profile', 'Urine Microalbumin'],
        'description': 'Complete diabetes risk & management panel',
        'duration': '3-4 hours',
        'fasting': True,
        'category': 'Diabetes',
        'icon': 'fa-tint',
        'color': '#7c3aed',
        'popular': False,
        'preparation': [
            'Fasting for 10-12 hours before the test',
            'Post-prandial sample taken 2 hours after meal',
            'Carry glucose drink or meal for PP test',
            'Bring glucometer readings if available',
        ],
        'ideal_for': 'Individuals with family history of diabetes or at-risk groups',
    },
    {
        'id': 5,
        'name': 'Women Health Package',
        'price': 2999,
        'tests': ['CBC', 'Thyroid Panel', 'Iron Studies', 'Vitamin D', 'Vitamin B12',
                  'Calcium', 'Pap Smear', 'Mammography', 'Bone Density'],
        'description': "Comprehensive women's health screening",
        'duration': '5-6 hours',
        'fasting': True,
        'category': 'Women',
        'icon': 'fa-female',
        'color': '#ec4899',
        'popular': True,
        'preparation': [
            'Fasting for 10-12 hours before blood tests',
            'Schedule outside menstrual period for Pap Smear',
            'Avoid using vaginal creams 48 hours before Pap Smear',
            'Wear comfortable two-piece clothing',
            'Inform if pregnant or breastfeeding',
        ],
        'ideal_for': 'Women aged 30+ for comprehensive reproductive and general health',
    },
    {
        'id': 6,
        'name': 'Senior Citizen Package',
        'price': 3999,
        'tests': ['CBC', 'Blood Sugar', 'HbA1c', 'Liver Function', 'Kidney Function',
                  'Thyroid', 'Lipid Profile', 'ECG', 'ECHO', 'Chest X-Ray',
                  'Bone Density', 'PSA/CA-125', 'Eye Check'],
        'description': 'Complete screening for 60+ years',
        'duration': '6-7 hours',
        'fasting': True,
        'category': 'Senior',
        'icon': 'fa-user-md',
        'color': '#0891b2',
        'popular': False,
        'preparation': [
            'Fasting for 10-12 hours before the test',
            'Bring all current medications and prescriptions',
            'Carry previous health reports for comparison',
            'Have a companion for assistance if needed',
            'Wear comfortable, easy-to-remove clothing',
            'Inform about any implants (pacemaker, etc.)',
        ],
        'ideal_for': 'Adults aged 60+ for comprehensive age-appropriate screening',
    },
    {
        'id': 7,
        'name': 'Pre-Employment Health Check',
        'price': 799,
        'tests': ['CBC', 'Blood Sugar', 'Urine Analysis', 'Chest X-Ray', 'Vision Test'],
        'description': 'Standard pre-employment medical fitness',
        'duration': '1-2 hours',
        'fasting': False,
        'category': 'Corporate',
        'icon': 'fa-briefcase',
        'color': '#ea580c',
        'popular': False,
        'preparation': [
            'No fasting required',
            'Bring valid photo ID proof',
            'Carry spectacles or contact lenses if used',
            'Wear a shirt with sleeves that can be rolled up',
        ],
        'ideal_for': 'Job applicants and corporate employees requiring fitness certificates',
    },
    {
        'id': 8,
        'name': 'Child Health Package',
        'price': 1299,
        'tests': ['CBC', 'Blood Sugar', 'Iron Studies', 'Vitamin D', 'Thyroid',
                  'Growth Assessment', 'Vision & Hearing'],
        'description': 'Pediatric growth and development assessment',
        'duration': '2-3 hours',
        'fasting': True,
        'category': 'Pediatric',
        'icon': 'fa-child',
        'color': '#16a34a',
        'popular': False,
        'preparation': [
            'Fasting for 8-10 hours (can have water)',
            'Bring vaccination records',
            'Bring previous growth charts if available',
            'Carry a snack for after blood draw',
            'Parent/guardian must accompany the child',
        ],
        'ideal_for': 'Children aged 3-15 for annual health and growth monitoring',
    },
]

# Categories for filter tabs
CATEGORIES = [
    {'key': 'all', 'label': 'All Packages', 'icon': 'fa-th-large'},
    {'key': 'General', 'label': 'General', 'icon': 'fa-heartbeat'},
    {'key': 'Cardiac', 'label': 'Cardiac', 'icon': 'fa-heart'},
    {'key': 'Diabetes', 'label': 'Diabetes', 'icon': 'fa-tint'},
    {'key': 'Women', 'label': 'Women', 'icon': 'fa-female'},
    {'key': 'Senior', 'label': 'Senior', 'icon': 'fa-user-md'},
    {'key': 'Corporate', 'label': 'Corporate', 'icon': 'fa-briefcase'},
    {'key': 'Pediatric', 'label': 'Pediatric', 'icon': 'fa-child'},
]


def _get_package_by_id(pkg_id):
    """Look up a package by its ID."""
    for pkg in HEALTH_PACKAGES:
        if pkg['id'] == pkg_id:
            return pkg
    return None


# ── Public: List all packages ────────────────────────────────────────────────
@health_packages_bp.route('/')
def listing():
    """Public page showing all available health checkup packages."""
    category = request.args.get('category', 'all')
    if category and category != 'all':
        packages = [p for p in HEALTH_PACKAGES if p['category'] == category]
    else:
        packages = HEALTH_PACKAGES
        category = 'all'

    return render_template(
        'health_packages/listing.html',
        packages=packages,
        categories=CATEGORIES,
        active_category=category,
        all_packages=HEALTH_PACKAGES,
    )


# ── Public: Package detail ───────────────────────────────────────────────────
@health_packages_bp.route('/<int:id>')
def detail(id):
    """Show detailed information about a single health package."""
    package = _get_package_by_id(id)
    if not package:
        flash('Health package not found.', 'warning')
        return redirect(url_for('health_packages.listing'))

    # Suggest related packages from the same category (exclude current)
    related = [p for p in HEALTH_PACKAGES if p['category'] == package['category'] and p['id'] != id]
    if len(related) < 2:
        # Fill with popular packages from other categories
        popular = [p for p in HEALTH_PACKAGES if p.get('popular') and p['id'] != id]
        related = (related + popular)[:3]

    # Get available doctors for booking
    doctors = []
    try:
        doctors = Doctor.query.filter_by(verified=True, is_suspended=False).all()
    except Exception:
        pass

    return render_template(
        'health_packages/detail.html',
        package=package,
        related=related,
        doctors=doctors,
    )


# ── Authenticated: Book a package ────────────────────────────────────────────
@health_packages_bp.route('/book', methods=['POST'])
@login_required
def book():
    """Book a health checkup package (patient role required)."""
    # Role check
    role_value = getattr(current_user.role, 'value', str(current_user.role))
    if role_value != 'PATIENT':
        flash('Only patients can book health packages.', 'danger')
        return redirect(url_for('health_packages.listing'))

    package_id = request.form.get('package_id', type=int)
    preferred_date = request.form.get('preferred_date', '')
    doctor_id = request.form.get('doctor_id', type=int)

    package = _get_package_by_id(package_id)
    if not package:
        flash('Invalid health package selected.', 'danger')
        return redirect(url_for('health_packages.listing'))

    # Get the patient record
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found. Please complete your profile first.', 'warning')
        return redirect(url_for('health_packages.listing'))

    # Parse preferred date
    try:
        if preferred_date:
            appt_date = datetime.strptime(preferred_date, '%Y-%m-%d')
            # Set time to 8:00 AM for health checkups
            appt_date = appt_date.replace(hour=8, minute=0)
        else:
            # Default to tomorrow 8 AM
            appt_date = (datetime.utcnow() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    except ValueError:
        appt_date = (datetime.utcnow() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)

    # Validate the date is in the future
    if appt_date.date() <= datetime.utcnow().date():
        flash('Please select a future date for your health checkup.', 'warning')
        return redirect(url_for('health_packages.detail', id=package_id))

    # Find a doctor — use selected doctor or first available
    doctor = None
    if doctor_id:
        doctor = Doctor.query.get(doctor_id)
    if not doctor:
        doctor = Doctor.query.filter_by(verified=True, is_suspended=False).first()
    if not doctor:
        # Fallback: get any doctor
        doctor = Doctor.query.first()

    if not doctor:
        flash('No doctors available at the moment. Please try again later.', 'warning')
        return redirect(url_for('health_packages.detail', id=package_id))

    # Create appointment
    reason = f"Health Package: {package['name']}"
    notes = (
        f"Package: {package['name']} (ID: {package['id']})\n"
        f"Price: Rs. {package['price']}\n"
        f"Tests: {', '.join(package['tests'])}\n"
        f"Duration: {package['duration']}\n"
        f"Fasting Required: {'Yes' if package['fasting'] else 'No'}"
    )

    try:
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=appt_date,
            reason=reason,
            status='confirmed',
            notes=notes,
        )
        db.session.add(appointment)
        db.session.commit()
        flash(f'Successfully booked "{package["name"]}"! Your appointment is on {appt_date.strftime("%d %b %Y")} at 8:00 AM.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to book the package. Please try again.', 'danger')

    return redirect(url_for('health_packages.my_bookings'))


# ── Authenticated: My bookings ───────────────────────────────────────────────
@health_packages_bp.route('/my-bookings')
@login_required
def my_bookings():
    """Show patient's booked health packages."""
    role_value = getattr(current_user.role, 'value', str(current_user.role))
    if role_value != 'PATIENT':
        flash('Only patients can view their bookings.', 'danger')
        return redirect(url_for('health_packages.listing'))

    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'warning')
        return redirect(url_for('health_packages.listing'))

    # Find appointments that are health package bookings
    bookings = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.reason.like('Health Package:%'),
    ).order_by(Appointment.appointment_date.desc()).all()

    # Enrich bookings with package data
    enriched_bookings = []
    for booking in bookings:
        # Extract package name from reason
        pkg_name = booking.reason.replace('Health Package: ', '')
        pkg_data = None
        for p in HEALTH_PACKAGES:
            if p['name'] == pkg_name:
                pkg_data = p
                break

        enriched_bookings.append({
            'appointment': booking,
            'package': pkg_data,
            'package_name': pkg_name,
        })

    return render_template(
        'health_packages/my_bookings.html',
        bookings=enriched_bookings,
        all_packages=HEALTH_PACKAGES,
    )
