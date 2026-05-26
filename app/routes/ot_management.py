"""Operation Theatre (OT) Management Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, OTBooking, Patient, Doctor, IPAdmission, UserRole)
from app.routes.auth import doctor_required
from datetime import datetime, timedelta
from sqlalchemy import func

ot_bp = Blueprint('ot', __name__, url_prefix='/ot')


def _staff_required(f):
    """Allow DOCTOR, HOST, NURSE roles."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.doctor_login'))
        role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()
        if role_val not in ('DOCTOR', 'HOST', 'ADMIN', 'NURSE'):
            flash('Access denied.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@ot_bp.route('/')
@ot_bp.route('/dashboard')
@login_required
@_staff_required
def dashboard():
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    todays_surgeries = OTBooking.query.filter(
        func.date(OTBooking.scheduled_date) == today
    ).order_by(OTBooking.scheduled_date).all()

    upcoming = OTBooking.query.filter(
        OTBooking.scheduled_date >= datetime.utcnow(),
        OTBooking.status.in_(['Scheduled', 'In Progress'])
    ).order_by(OTBooking.scheduled_date).limit(20).all()

    completed_today = OTBooking.query.filter(
        func.date(OTBooking.scheduled_date) == today,
        OTBooking.status == 'Completed'
    ).count()

    in_progress = OTBooking.query.filter(OTBooking.status == 'In Progress').all()

    stats = {
        'total_today': len(todays_surgeries),
        'completed_today': completed_today,
        'in_progress': len(in_progress),
        'upcoming_week': OTBooking.query.filter(
            OTBooking.scheduled_date.between(datetime.utcnow(), datetime.utcnow() + timedelta(days=7)),
            OTBooking.status == 'Scheduled'
        ).count()
    }

    # OT Room status
    ot_rooms = ['OT-1', 'OT-2', 'OT-3', 'Minor OT']
    room_status = {}
    for room in ot_rooms:
        active = OTBooking.query.filter(
            OTBooking.ot_room == room,
            OTBooking.status == 'In Progress'
        ).first()
        room_status[room] = {
            'status': 'Occupied' if active else 'Available',
            'booking': active
        }

    return render_template('ot/dashboard.html',
                           todays_surgeries=todays_surgeries,
                           upcoming=upcoming,
                           in_progress=in_progress,
                           stats=stats,
                           room_status=room_status,
                           ot_rooms=ot_rooms)


@ot_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@_staff_required
def schedule():
    if request.method == 'POST':
        try:
            booking = OTBooking(
                patient_id=request.form.get('patient_id', type=int),
                doctor_id=request.form.get('doctor_id', type=int),
                surgery_name=request.form.get('surgery_name'),
                surgery_type=request.form.get('surgery_type', 'Elective'),
                ot_room=request.form.get('ot_room', 'OT-1'),
                scheduled_date=datetime.strptime(request.form.get('scheduled_date'), '%Y-%m-%dT%H:%M'),
                estimated_duration=request.form.get('estimated_duration', 60, type=int),
                anesthesia_type=request.form.get('anesthesia_type'),
                anesthetist_name=request.form.get('anesthetist_name'),
                assistant_surgeon=request.form.get('assistant_surgeon'),
                scrub_nurse=request.form.get('scrub_nurse'),
                pre_op_diagnosis=request.form.get('pre_op_diagnosis'),
                priority=request.form.get('priority', 'Elective'),
                status='Scheduled'
            )
            db.session.add(booking)
            db.session.commit()
            flash('Surgery scheduled successfully!', 'success')
            return redirect(url_for('ot.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling surgery: {str(e)}', 'error')

    patients = Patient.query.order_by(Patient.name).all()
    doctors = Doctor.query.filter_by(is_deleted=False).all()
    return render_template('ot/schedule.html', patients=patients, doctors=doctors)


@ot_bp.route('/api/update-status', methods=['POST'])
@login_required
@_staff_required
def update_status():
    data = request.get_json(silent=True) or {}
    booking_id = data.get('booking_id')
    new_status = data.get('status')

    booking = OTBooking.query.get(booking_id)
    if not booking:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404

    booking.status = new_status
    if new_status == 'In Progress':
        booking.actual_start = datetime.utcnow()
    elif new_status == 'Completed':
        booking.actual_end = datetime.utcnow()
        booking.post_op_diagnosis = data.get('post_op_diagnosis', '')
        booking.procedure_notes = data.get('procedure_notes', '')
        booking.complications = data.get('complications', '')

    db.session.commit()
    return jsonify({'success': True, 'message': f'Status updated to {new_status}'})


@ot_bp.route('/booking/<int:booking_id>')
@login_required
@_staff_required
def view_booking(booking_id):
    booking = OTBooking.query.get_or_404(booking_id)
    return render_template('ot/view_booking.html', booking=booking)


@ot_bp.route('/api/search-patients')
@login_required
@_staff_required
def search_patients():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    patients = Patient.query.filter(
        db.or_(Patient.name.ilike(f'%{q}%'), Patient.uhid.ilike(f'%{q}%'))
    ).limit(10).all()
    return jsonify([{'id': p.id, 'name': p.full_name, 'uhid': p.uhid} for p in patients])
