"""Advanced Hospital Analytics Dashboard"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.models import (db, Patient, Doctor, Appointment, Prescription,
                                Visit, LabOrder, IPAdmission, Billing, BillItem,
                                EmergencyCase, OTBooking, PatientFeedback,
                                Medicine, Bed, UserRole)
from datetime import datetime, timedelta
from sqlalchemy import func, extract

analytics_bp = Blueprint('analytics_dashboard', __name__, url_prefix='/analytics')


def _admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.host_login'))
        role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()
        if role_val not in ('HOST', 'ADMIN', 'DOCTOR'):
            from flask import flash, redirect
            flash('Access denied.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@analytics_bp.route('/')
@analytics_bp.route('/dashboard')
@login_required
@_admin_required
def dashboard():
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    # Patient Stats
    total_patients = Patient.query.count()
    new_patients_month = Patient.query.filter(
        Patient.created_at >= month_start
    ).count()
    new_patients_today = Patient.query.filter(
        func.date(Patient.created_at) == today
    ).count()

    # Appointment Stats
    total_appointments_month = Appointment.query.filter(
        Appointment.appointment_date >= month_start
    ).count()
    appointments_today = Appointment.query.filter(
        func.date(Appointment.appointment_date) == today
    ).count()
    completed_today = Appointment.query.filter(
        func.date(Appointment.appointment_date) == today,
        Appointment.status == 'completed'
    ).count()

    # Revenue (from billings)
    revenue_month = 0
    revenue_today = 0
    try:
        revenue_month = db.session.query(
            func.coalesce(func.sum(Billing.total_amount), 0)
        ).filter(Billing.created_at >= month_start).scalar() or 0
        revenue_today = db.session.query(
            func.coalesce(func.sum(Billing.total_amount), 0)
        ).filter(func.date(Billing.created_at) == today).scalar() or 0
    except Exception:
        pass

    # IP Stats
    active_admissions = 0
    try:
        active_admissions = IPAdmission.query.filter_by(status='Admitted').count()
    except Exception:
        pass

    # Lab Stats
    lab_orders_today = 0
    try:
        lab_orders_today = LabOrder.query.filter(
            func.date(LabOrder.created_at) == today
        ).count()
    except Exception:
        pass

    # Doctor Stats
    total_doctors = Doctor.query.filter_by(is_deleted=False).count()

    # Emergency Stats
    emergency_today = 0
    try:
        emergency_today = EmergencyCase.query.filter(
            func.date(EmergencyCase.arrival_time) == today
        ).count()
    except Exception:
        pass

    # OT Stats
    surgeries_today = 0
    try:
        surgeries_today = OTBooking.query.filter(
            func.date(OTBooking.scheduled_date) == today
        ).count()
    except Exception:
        pass

    # Bed occupancy
    bed_stats = {'total': 0, 'occupied': 0, 'available': 0, 'occupancy_rate': 0}
    try:
        bed_stats['total'] = Bed.query.count()
        bed_stats['occupied'] = Bed.query.filter_by(is_occupied=True).count()
        bed_stats['available'] = bed_stats['total'] - bed_stats['occupied']
        if bed_stats['total'] > 0:
            bed_stats['occupancy_rate'] = round((bed_stats['occupied'] / bed_stats['total']) * 100)
    except Exception:
        pass

    # Feedback
    avg_rating = 0
    try:
        avg_rating = db.session.query(func.avg(PatientFeedback.rating)).scalar() or 0
        avg_rating = round(avg_rating, 1)
    except Exception:
        pass

    stats = {
        'total_patients': total_patients,
        'new_patients_month': new_patients_month,
        'new_patients_today': new_patients_today,
        'total_appointments_month': total_appointments_month,
        'appointments_today': appointments_today,
        'completed_today': completed_today,
        'revenue_month': revenue_month,
        'revenue_today': revenue_today,
        'active_admissions': active_admissions,
        'lab_orders_today': lab_orders_today,
        'total_doctors': total_doctors,
        'emergency_today': emergency_today,
        'surgeries_today': surgeries_today,
        'bed_stats': bed_stats,
        'avg_rating': avg_rating,
    }

    return render_template('analytics/dashboard.html', stats=stats)


@analytics_bp.route('/api/patient-trends')
@login_required
@_admin_required
def patient_trends():
    """Last 30 days patient registration trend."""
    data = []
    for i in range(30, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        count = Patient.query.filter(func.date(Patient.created_at) == day).count()
        data.append({'date': day.isoformat(), 'count': count})
    return jsonify(data)


@analytics_bp.route('/api/revenue-trends')
@login_required
@_admin_required
def revenue_trends():
    """Last 30 days revenue trend."""
    data = []
    for i in range(30, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        try:
            amount = db.session.query(
                func.coalesce(func.sum(Billing.total_amount), 0)
            ).filter(func.date(Billing.created_at) == day).scalar() or 0
        except Exception:
            amount = 0
        data.append({'date': day.isoformat(), 'amount': float(amount)})
    return jsonify(data)


@analytics_bp.route('/api/department-stats')
@login_required
@_admin_required
def department_stats():
    """Appointments by doctor specialization."""
    try:
        results = db.session.query(
            Doctor.specialization,
            func.count(Appointment.id)
        ).join(Appointment, Appointment.doctor_id == Doctor.id).group_by(
            Doctor.specialization
        ).all()
        return jsonify([{'department': r[0] or 'General', 'count': r[1]} for r in results])
    except Exception:
        return jsonify([])


@analytics_bp.route('/api/visit-distribution')
@login_required
@_admin_required
def visit_distribution():
    """Visit type distribution."""
    try:
        results = db.session.query(
            Visit.visit_type,
            func.count(Visit.id)
        ).group_by(Visit.visit_type).all()
        return jsonify([{'type': r[0], 'count': r[1]} for r in results])
    except Exception:
        return jsonify([])
