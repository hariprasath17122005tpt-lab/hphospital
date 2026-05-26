"""Emergency Department / Triage Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, EmergencyCase, Patient, Doctor, UserRole)
from datetime import datetime, timedelta
from sqlalchemy import func

emergency_bp = Blueprint('emergency', __name__, url_prefix='/emergency')


def _staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.doctor_login'))
        role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()
        if role_val not in ('DOCTOR', 'HOST', 'ADMIN', 'NURSE', 'RECEPTIONIST'):
            flash('Access denied.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@emergency_bp.route('/')
@emergency_bp.route('/dashboard')
@login_required
@_staff_required
def dashboard():
    active_cases = EmergencyCase.query.filter(
        EmergencyCase.status.in_(['Active', 'Stabilized'])
    ).order_by(
        # Critical first
        db.case(
            (EmergencyCase.triage_level == 'Critical', 1),
            (EmergencyCase.triage_level == 'Urgent', 2),
            (EmergencyCase.triage_level == 'Semi-Urgent', 3),
            else_=4
        ),
        EmergencyCase.arrival_time.desc()
    ).all()

    today = datetime.utcnow().date()
    stats = {
        'active': EmergencyCase.query.filter(EmergencyCase.status == 'Active').count(),
        'stabilized': EmergencyCase.query.filter(EmergencyCase.status == 'Stabilized').count(),
        'total_today': EmergencyCase.query.filter(func.date(EmergencyCase.arrival_time) == today).count(),
        'discharged_today': EmergencyCase.query.filter(
            func.date(EmergencyCase.arrival_time) == today,
            EmergencyCase.status == 'Discharged'
        ).count(),
        'admitted_today': EmergencyCase.query.filter(
            func.date(EmergencyCase.arrival_time) == today,
            EmergencyCase.status == 'Admitted'
        ).count(),
        'critical': EmergencyCase.query.filter(
            EmergencyCase.triage_level == 'Critical',
            EmergencyCase.status.in_(['Active', 'Stabilized'])
        ).count(),
    }

    recent_discharged = EmergencyCase.query.filter(
        EmergencyCase.status.in_(['Discharged', 'Admitted', 'Transferred']),
        EmergencyCase.arrival_time >= datetime.utcnow() - timedelta(hours=24)
    ).order_by(EmergencyCase.arrival_time.desc()).limit(20).all()

    doctors = Doctor.query.filter_by(is_deleted=False).all()

    return render_template('emergency/dashboard.html',
                           active_cases=active_cases,
                           recent_discharged=recent_discharged,
                           stats=stats,
                           doctors=doctors)


@emergency_bp.route('/register', methods=['GET', 'POST'])
@login_required
@_staff_required
def register():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', type=int)
            case = EmergencyCase(
                patient_id=patient_id,
                triage_level=request.form.get('triage_level', 'Urgent'),
                triage_color=_triage_color(request.form.get('triage_level', 'Urgent')),
                chief_complaint=request.form.get('chief_complaint'),
                arrival_mode=request.form.get('arrival_mode', 'Walk-in'),
                patient_name=request.form.get('patient_name'),
                patient_age=request.form.get('patient_age', type=int),
                patient_gender=request.form.get('patient_gender'),
                patient_phone=request.form.get('patient_phone'),
                bp_systolic=request.form.get('bp_systolic', type=int),
                bp_diastolic=request.form.get('bp_diastolic', type=int),
                heart_rate=request.form.get('heart_rate', type=int),
                spo2=request.form.get('spo2', type=int),
                temperature=request.form.get('temperature', type=float),
                gcs_score=request.form.get('gcs_score', 15, type=int),
                attending_doctor_id=request.form.get('attending_doctor_id', type=int),
                status='Active'
            )
            db.session.add(case)
            db.session.commit()
            flash('Emergency case registered!', 'success')
            return redirect(url_for('emergency.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    doctors = Doctor.query.filter_by(is_deleted=False).all()
    patients = Patient.query.order_by(Patient.name).limit(100).all()
    return render_template('emergency/register.html', doctors=doctors, patients=patients)


@emergency_bp.route('/api/update', methods=['POST'])
@login_required
@_staff_required
def update_case():
    data = request.get_json(silent=True) or {}
    case = EmergencyCase.query.get(data.get('case_id'))
    if not case:
        return jsonify({'success': False, 'error': 'Case not found'}), 404

    if 'status' in data:
        case.status = data['status']
        if data['status'] == 'Stabilized':
            case.stabilized_at = datetime.utcnow()
        elif data['status'] in ('Discharged', 'Admitted', 'Transferred'):
            case.discharged_at = datetime.utcnow()
            case.disposition = data['status']
    if 'treatment_given' in data:
        case.treatment_given = data['treatment_given']
    if 'attending_doctor_id' in data:
        case.attending_doctor_id = data['attending_doctor_id']

    db.session.commit()
    return jsonify({'success': True})


@emergency_bp.route('/case/<int:case_id>')
@login_required
@_staff_required
def view_case(case_id):
    case = EmergencyCase.query.get_or_404(case_id)
    return render_template('emergency/view_case.html', case=case)


@emergency_bp.route('/triage-board')
@login_required
@_staff_required
def triage_board():
    """Live triage board for emergency display."""
    cases = EmergencyCase.query.filter(
        EmergencyCase.status.in_(['Active', 'Stabilized'])
    ).order_by(EmergencyCase.arrival_time.desc()).all()
    return render_template('emergency/triage_board.html', cases=cases)


def _triage_color(level):
    return {
        'Critical': 'Red',
        'Urgent': 'Orange',
        'Semi-Urgent': 'Yellow',
        'Non-Urgent': 'Green'
    }.get(level, 'Blue')
