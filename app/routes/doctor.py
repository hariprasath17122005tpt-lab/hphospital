from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.models import (db, Doctor, Patient, HealthData, PatientVitals, Appointment, 
                               Prescription, PrescriptionMedicine, Medicine, Message,
                               Billing, LabReport, LabOrder, PatientCheckIn, ReceptionQueue,
                               PharmacyOrder, MedicalImage, DoctorEvent)
from werkzeug.utils import secure_filename
import os
import json
import hashlib
from app.routes.auth import doctor_required
from datetime import datetime, date as date_cls
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case, inspect

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')


CLINICAL_TEMPLATES = {
    'fever_consultation': {
        'label': 'Fever Consultation',
        'symptoms': 'Fever, body ache, mild headache',
        'diagnosis': 'Acute febrile illness (provisional)',
        'notes': 'Assess hydration, monitor temperature trend, evaluate red-flag symptoms.',
        'lab_tests': ['CBC', 'CRP'],
        'followup_notes': 'Review in 2-3 days or earlier if worsening.'
    },
    'diabetes_followup': {
        'label': 'Diabetes Follow-up',
        'symptoms': 'Routine diabetes follow-up',
        'diagnosis': 'Type 2 diabetes mellitus follow-up',
        'notes': 'Review glucose log, reinforce diet/exercise adherence, assess hypoglycemia episodes.',
        'lab_tests': ['HbA1c', 'Fasting Blood Sugar', 'Serum Creatinine'],
        'followup_notes': 'Repeat HbA1c in 3 months and continue home glucose monitoring.'
    },
    'hypertension_review': {
        'label': 'Hypertension Review',
        'symptoms': 'Blood pressure review',
        'diagnosis': 'Hypertension follow-up',
        'notes': 'Review BP chart, sodium intake, medication adherence, and target organ symptoms.',
        'lab_tests': ['Renal Function Test', 'Lipid Profile'],
        'followup_notes': 'Home BP monitoring advised; follow-up in 4 weeks.'
    },
    'pediatric_visit': {
        'label': 'Pediatric Visit',
        'symptoms': 'General pediatric consultation',
        'diagnosis': 'Pediatric evaluation (provisional)',
        'notes': 'Assess growth, hydration, vaccination status, and parental concerns.',
        'lab_tests': ['CBC'],
        'followup_notes': 'Return if fever persists, poor intake, or breathing difficulty.'
    }
}

DRUG_INTERACTION_RULES = {
    frozenset(['warfarin', 'aspirin']): 'Increased bleeding risk when combined with Aspirin.',
    frozenset(['warfarin', 'ibuprofen']): 'Increased bleeding risk with NSAIDs.',
    frozenset(['lisinopril', 'spironolactone']): 'Risk of hyperkalemia; monitor potassium.',
    frozenset(['metformin', 'contrast']): 'Temporarily hold Metformin around contrast imaging if renal risk.',
    frozenset(['azithromycin', 'ondansetron']): 'QT prolongation risk; monitor clinically.',
    frozenset(['amlodipine', 'simvastatin']): 'Simvastatin exposure may increase; consider dose caution.'
}


def _build_quick_clinical_brief(patient, latest_health):
    """Generate a compact doctor-facing triage summary for the patient view."""
    if not latest_health:
        return {
            'severity': 'No Recent Data',
            'severity_class': 'secondary',
            'highest_risk': 0,
            'risk_band': 'Unknown',
            'red_flags': ['No recent vitals available'],
            'next_actions': ['Request fresh vitals before prescribing major changes.'],
        }

    red_flags = []
    next_actions = []

    systolic = latest_health.systolic_bp or 0
    diastolic = latest_health.diastolic_bp or 0
    fasting = latest_health.fasting_sugar or 0
    heart_rate = latest_health.heart_rate or 0

    highest_risk = max(
        latest_health.diabetes_risk or 0,
        latest_health.heart_disease_risk or 0,
        latest_health.hypertension_risk or 0
    )

    if systolic >= 180 or diastolic >= 120:
        red_flags.append('Potential hypertensive crisis range BP')
    elif systolic >= 140 or diastolic >= 90:
        red_flags.append('Stage-2 hypertension pattern')

    if fasting >= 180:
        red_flags.append('Marked fasting hyperglycemia')
    elif fasting >= 126:
        red_flags.append('Diabetic-range fasting sugar')

    if heart_rate and (heart_rate > 120 or heart_rate < 50):
        red_flags.append('Abnormal resting heart-rate range')

    if highest_risk >= 85:
        severity = 'Critical'
        severity_class = 'danger'
        risk_band = 'Very High'
        next_actions.extend([
            'Prioritize same-day review and medication adherence check.',
            'Assess red-flag symptoms and emergency escalation criteria.'
        ])
    elif highest_risk >= 65:
        severity = 'High'
        severity_class = 'warning'
        risk_band = 'High'
        next_actions.extend([
            'Plan close follow-up within 3-7 days.',
            'Reinforce BP/sugar logs and lifestyle compliance.'
        ])
    elif highest_risk >= 35:
        severity = 'Moderate'
        severity_class = 'info'
        risk_band = 'Moderate'
        next_actions.append('Continue current plan with routine follow-up.')
    else:
        severity = 'Stable'
        severity_class = 'success'
        risk_band = 'Low'
        next_actions.append('Maintain current treatment and preventive counseling.')

    if not red_flags:
        red_flags.append('No acute clinical flags detected from latest recorded data.')

    return {
        'severity': severity,
        'severity_class': severity_class,
        'highest_risk': int(round(highest_risk)),
        'risk_band': risk_band,
        'red_flags': red_flags[:4],
        'next_actions': next_actions[:3],
    }


def _doctor_has_access(doctor, patient_id):
    """Check if doctor has access to a patient via appointment, reception queue, prescription, or express check-in"""
    if doctor is None:
        return False
    # Query only IDs to reduce schema-coupling with partially migrated DBs.
    has_appointment = db.session.query(Appointment.id).filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    if has_appointment:
        return True
    # Access via reception queue (patient was assigned to this doctor)
    has_queue = db.session.query(ReceptionQueue.id).filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    if has_queue:
        return True
    # Access via prescription (doctor already wrote a prescription for this patient)
    has_prescription = db.session.query(Prescription.id).filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    if has_prescription:
        return True
    # Access via express check-in (patient selected this doctor for express check-in)
    has_checkin = db.session.query(PatientCheckIn.id).filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    return has_checkin


def _format_checkin_symptoms(raw_symptoms):
    """Normalize symptoms field (JSON/list/text) into a UI-friendly string."""
    if not raw_symptoms:
        return ''
    if isinstance(raw_symptoms, list):
        return ', '.join([str(x).strip() for x in raw_symptoms if str(x).strip()])
    text = str(raw_symptoms).strip()
    if not text:
        return ''
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return ', '.join([str(x).strip() for x in parsed if str(x).strip()])
        if isinstance(parsed, dict):
            values = [str(v).strip() for v in parsed.values() if str(v).strip()]
            return ', '.join(values)
    except Exception:
        pass
    return text


@doctor_bp.route('/portal')
@login_required
@doctor_required
def portal():
    """Unified doctor portal page (supports ?mode=dashboard|op|tools)."""
    doctor = current_user.doctor
    if not doctor:
        flash('Doctor profile not found for this account.', 'danger')
        return redirect(url_for('auth.logout'))
    return render_template('doctor/portal.html', doctor=doctor)


@doctor_bp.route('/api/portal/summary')
@login_required
@doctor_required
def api_portal_summary():
    """Portal summary payload for dashboard and OP mode widgets."""
    doctor = current_user.doctor
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile missing'}), 400

    now = datetime.utcnow()
    today_start = datetime.combine(date_cls.today(), datetime.min.time())
    today_end = datetime.combine(date_cls.today(), datetime.max.time())

    today_appointments = Appointment.query.filter_by(doctor_id=doctor.id).filter(
        Appointment.appointment_date.between(today_start, today_end)
    ).count()

    pending_appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='pending').filter(
        Appointment.appointment_date.between(today_start, today_end)
    ).count()

    waiting_queue_rows = ReceptionQueue.query.filter(
        ReceptionQueue.doctor_id == doctor.id,
        ReceptionQueue.reception_status == 'Accepted',
        ReceptionQueue.doctor_status.in_(['Pending', 'Accepted']),
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.asc()).limit(20).all()

    waiting_queue = []
    waiting_patient_ids = set()
    for row in waiting_queue_rows:
        patient = row.patient
        row_status = 'accepted' if (row.doctor_status or '').lower() == 'accepted' else 'pending'
        waiting_queue.append({
            'entry_id': row.id,
            'token': row.token_number,
            'patient_id': row.patient_id,
            'patient_name': f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{row.patient_id}",
            'visit_reason': row.visit_reason or 'General visit',
            'status': row_status,
            'severity': 'normal',
            'priority': 'normal',
            'visit_type': row.patient_type or 'OPD',
            'reason': row.visit_reason or 'Reception queue',
            'symptoms': '',
            'created_at': row.created_at.strftime('%H:%M') if row.created_at else ''
        })
        if row.patient_id:
            waiting_patient_ids.add(row.patient_id)

    pending_lab_reports = LabOrder.query.filter(
        LabOrder.doctor_id == doctor.id,
        LabOrder.status.in_(['PENDING', 'SAMPLE_COLLECTED', 'PROCESSING'])
    ).count()

    abnormal_lab_alerts = LabReport.query.filter(
        LabReport.doctor_id == doctor.id,
        LabReport.critical_alert.is_(True)
    ).count()

    recent_rx_rows = Prescription.query.filter_by(doctor_id=doctor.id).order_by(
        Prescription.prescribed_at.desc()
    ).limit(6).all()

    recent_prescriptions = []
    for rx in recent_rx_rows:
        patient = rx.patient
        recent_prescriptions.append({
            'patient_id': rx.patient_id,
            'patient_name': f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{rx.patient_id}",
            'diagnosis': (rx.diagnosis or rx.notes or 'General prescription')[:120],
            'date': rx.prescribed_at.strftime('%Y-%m-%d %H:%M') if rx.prescribed_at else ''
        })

    checkins = PatientCheckIn.query.filter(
        PatientCheckIn.doctor_id == doctor.id,
        PatientCheckIn.status.in_(['pending', 'accepted', 'rejected']),
        PatientCheckIn.created_at >= today_start
    ).order_by(
        case(
            (PatientCheckIn.priority == 'urgent', 0),
            (PatientCheckIn.severity == 'severe', 1),
            (PatientCheckIn.severity == 'moderate', 2),
            else_=3
        ),
        PatientCheckIn.created_at.desc()
    ).limit(60).all()

    express_checkins = []
    for ci in checkins:
        patient = ci.patient
        express_checkins.append({
            'checkin_id': ci.id,
            'patient_id': ci.patient_id,
            'patient_name': f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{ci.patient_id}",
            'status': (ci.status or 'pending').lower(),
            'severity': (ci.severity or 'normal').lower(),
            'priority': (ci.priority or 'normal').lower(),
            'visit_type': ci.visit_type or 'follow-up',
            'reason': ci.check_in_reason or 'General consultation',
            'symptoms': _format_checkin_symptoms(ci.symptoms),
            'created_at': ci.created_at.strftime('%H:%M') if ci.created_at else ''
        })

    patient_ids_for_risk = set(waiting_patient_ids)
    patient_ids_for_risk.update([c['patient_id'] for c in express_checkins if c.get('patient_id')])

    critical_alerts = []
    if patient_ids_for_risk:
        latest_health_rows = HealthData.query.filter(
            HealthData.patient_id.in_(patient_ids_for_risk)
        ).order_by(HealthData.recorded_at.desc()).limit(50).all()

        seen = set()
        for hd in latest_health_rows:
            if hd.patient_id in seen:
                continue
            risk = max(hd.diabetes_risk or 0, hd.heart_disease_risk or 0, hd.hypertension_risk or 0)
            if risk < 80:
                continue
            patient = Patient.query.get(hd.patient_id)
            critical_alerts.append({
                'patient_id': hd.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}" if patient else f"Patient #{hd.patient_id}",
                'risk': int(round(risk)),
                'recorded_at': hd.recorded_at.strftime('%Y-%m-%d %H:%M') if hd.recorded_at else ''
            })
            seen.add(hd.patient_id)
            if len(critical_alerts) >= 8:
                break

    notifications = []
    pending_checkins_count = sum(1 for c in express_checkins if c.get('status') == 'pending')
    if pending_checkins_count:
        notifications.append({
            'message': f'{pending_checkins_count} express check-in(s) waiting for action',
            'severity': 'warning',
            'time': now.strftime('%H:%M')
        })
    if pending_appointments:
        notifications.append({
            'message': f'{pending_appointments} appointment(s) are pending confirmation',
            'severity': 'warning',
            'time': now.strftime('%H:%M')
        })
    if abnormal_lab_alerts:
        notifications.append({
            'message': f'{abnormal_lab_alerts} critical lab alert(s) require review',
            'severity': 'warning',
            'time': now.strftime('%H:%M')
        })
    if not notifications:
        notifications.append({'message': 'All clear. No urgent alerts right now.', 'severity': 'info', 'time': now.strftime('%H:%M')})

    return jsonify({
        'success': True,
        'server_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': {
            'today_appointments': today_appointments,
            'waiting_patients': len(waiting_queue),
            'pending_lab_reports': pending_lab_reports,
            'abnormal_lab_alerts': abnormal_lab_alerts,
            'recent_prescriptions': len(recent_prescriptions),
            'express_checkins': len(express_checkins),
            'op_patients': len(waiting_queue) + len(express_checkins)
        },
        'waiting_queue': waiting_queue,
        'notifications': notifications,
        'critical_alerts': critical_alerts,
        'recent_prescriptions': recent_prescriptions,
        'express_checkins': express_checkins
    })

@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    """Legacy dashboard route redirected to the unified doctor portal."""
    return redirect(url_for('doctor.portal'))
    doctor = current_user.doctor
    
    # Get statistics
    total_patients = len(doctor.appointments)
    today_appointments = Appointment.query.filter_by(doctor_id=doctor.id).filter(
        Appointment.appointment_date.between(
            datetime.utcnow().replace(hour=0, minute=0, second=0),
            datetime.utcnow().replace(hour=23, minute=59, second=59)
        )
    ).count()
    
    # Get pending appointments
    pending_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, status='pending').order_by(
        Appointment.appointment_date).limit(5).all()
    
    # Get unread messages
    unread_messages = Message.query.filter_by(doctor_id=doctor.id, is_read=False).count()
    
    # Get pending patient check-ins (NEW)
    from datetime import date as date_cls
    today_start = datetime.combine(date_cls.today(), datetime.min.time())
    
    pending_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id, 
        status='pending'
    ).order_by(PatientCheckIn.created_at.desc()).limit(10).all()
    
    pending_checkins_count = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id,
        status='pending'
    ).count()
    
    # Get patients sent by reception (accepted by reception, waiting for doctor)
    reception_patients = ReceptionQueue.query.filter(
        ReceptionQueue.doctor_id == doctor.id,
        ReceptionQueue.reception_status == 'Accepted',
        ReceptionQueue.doctor_status.in_(['Pending', 'Accepted']),
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.asc()).all()
    
    # Determine which patients the doctor is seeing today to filter critical care list
    today_patient_ids = set()
    today_patient_ids.update([rq.patient_id for rq in reception_patients if rq.patient_id])
    today_patient_ids.update([pc.patient_id for pc in pending_checkins if pc.patient_id])
    
    # Add pending appointments for today
    today_end = datetime.combine(date_cls.today(), datetime.max.time())
    today_pending_apps = Appointment.query.filter_by(
        doctor_id=doctor.id, status='pending').filter(
        Appointment.appointment_date.between(today_start, today_end)).all()
    today_patient_ids.update([ap.patient_id for ap in today_pending_apps])
    
    # Get critical alerts (high-risk patients) only for today's active queues
    critical_patients = []
    if today_patient_ids:
        recent_health_data = db.session.query(HealthData).filter(
            HealthData.patient_id.in_(today_patient_ids)
        ).order_by(HealthData.recorded_at.desc()).limit(20).all()
        
        seen_patients = set() # Avoid duplicates in UI
        for health in recent_health_data:
            if health.patient_id in seen_patients:
                continue
            diabetes_risk = health.diabetes_risk or 0
            heart_disease_risk = health.heart_disease_risk or 0
            hypertension_risk = health.hypertension_risk or 0
            if diabetes_risk > 80 or heart_disease_risk > 80 or hypertension_risk > 80:
                critical_patients.append(health)
                seen_patients.add(health.patient_id)
    
    return render_template('doctor/dashboard.html',
                         doctor=doctor,
                         total_patients=total_patients,
                         today_appointments=today_appointments,
                         pending_appointments=pending_appointments,
                         unread_messages=unread_messages,
                         critical_patients=critical_patients[:5],
                         pending_checkins=pending_checkins,
                         pending_checkins_count=pending_checkins_count,
                         reception_patients=reception_patients)

@doctor_bp.route('/profile')
@login_required
@doctor_required
def profile():
    """Doctor profile"""
    doctor = current_user.doctor
    return render_template('doctor/profile.html', doctor=doctor)

@doctor_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def edit_profile():
    """Edit doctor profile"""
    doctor = current_user.doctor
    
    if request.method == 'POST':
        doctor.first_name = request.form.get('first_name', doctor.first_name)
        doctor.last_name = request.form.get('last_name', doctor.last_name)
        doctor.qualification = request.form.get('qualification', doctor.qualification)
        doctor.specialization = request.form.get('specialization', doctor.specialization)
        doctor.experience_years = int(request.form.get('experience_years', doctor.experience_years or 0))
        doctor.hospital = request.form.get('hospital', doctor.hospital)
        doctor.clinic_address = request.form.get('clinic_address', doctor.clinic_address)
        doctor.phone = request.form.get('phone', doctor.phone)
        doctor.consultation_fee = float(request.form.get('consultation_fee', doctor.consultation_fee or 0))
        doctor.availability_hours = request.form.get('availability_hours', doctor.availability_hours)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('doctor.profile'))
    
    return render_template('doctor/edit_profile.html', doctor=doctor)

@doctor_bp.route('/patients')
@login_required
@doctor_required
def patient_list():
    """View list of patients — from appointments, queue, and prescriptions"""
    doctor = current_user.doctor
    
    # Gather patient IDs from all sources (appointments, queue, express check-ins, prescriptions)
    appt_ids = db.session.query(Appointment.patient_id.distinct()).filter_by(doctor_id=doctor.id).all()
    queue_ids = db.session.query(ReceptionQueue.patient_id.distinct()).filter(
        db.or_(
            ReceptionQueue.doctor_id == doctor.id,
            ReceptionQueue.doctor_id.is_(None)
        )
    ).all()
    checkin_ids = db.session.query(PatientCheckIn.patient_id.distinct()).filter_by(doctor_id=doctor.id).all()
    rx_ids = db.session.query(Prescription.patient_id.distinct()).filter_by(doctor_id=doctor.id).all()
    
    patient_ids = set()
    for row in appt_ids + queue_ids + checkin_ids + rx_ids:
        patient_ids.add(row[0])

    # fallback: include all patients if no filtered list found, to ensure reception-created patients are visible
    if not patient_ids:
        patients = Patient.query.order_by(Patient.first_name.asc()).all()
    else:
        patients = Patient.query.filter(Patient.id.in_(patient_ids)).order_by(Patient.first_name.asc()).all()
    
    return render_template('doctor/patient_list.html', patients=patients)

@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def view_patient(patient_id):
    """View patient record"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check if doctor has access to this patient (appointment, queue, or prescription)
    if not _doctor_has_access(doctor, patient_id):
        flash('You do not have access to this patient record', 'danger')
        return redirect(url_for('doctor.patient_list'))
    
    # Get patient health data (Doctor AI-entry)
    health_data = HealthData.query.filter_by(patient_id=patient_id).order_by(
        HealthData.recorded_at.desc()).all()

    recent_health_data = []
    for h in health_data:
        recent_health_data.append({
            'source': 'health_data',
            'recorded_at': h.recorded_at,
            'systolic_bp': h.systolic_bp,
            'diastolic_bp': h.diastolic_bp,
            'heart_rate': h.heart_rate,
            'temperature': h.temperature,
            'oxygen_level': None,
            'respiratory_rate': None,
            'weight': h.bmi if h.bmi is not None else None,
            'nurse': None,
            'notes': h.symptoms or ''
        })

    recent_health_data.sort(key=lambda x: x['recorded_at'] or datetime.min, reverse=True)

    latest_health = health_data[0] if health_data else None
    quick_brief = _build_quick_clinical_brief(patient, latest_health)
    
    # Get appointments
    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()).all()
    
    # Get prescriptions
    prescriptions = Prescription.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Prescription.prescribed_at.desc()).all()

    # Get related lab orders/reports
    lab_orders = LabOrder.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(LabOrder.created_at.desc()).all()
    lab_reports = LabReport.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(LabReport.conducted_at.desc()).all()
    
    return render_template('doctor/view_patient.html',
                         patient=patient,
                         health_data=health_data,
                         recent_health_data=recent_health_data,
                         appointments=appointments,
                         prescriptions=prescriptions,
                         quick_brief=quick_brief,
                         lab_orders=lab_orders,
                         lab_reports=lab_reports)

@doctor_bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    """View appointments"""
    doctor = current_user.doctor
    filter_status = request.args.get('status', 'all')
    
    query = Appointment.query.filter_by(doctor_id=doctor.id)
    
    if filter_status != 'all':
        query = query.filter_by(status=filter_status)
    
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/appointments.html',
                         appointments=appointments,
                         current_status=filter_status)

from app.services.notification_service import NotificationService

@doctor_bp.route('/appointments/<int:appointment_id>/approve', methods=['POST'])
@login_required
@doctor_required
def approve_appointment(appointment_id):
    """Approve appointment"""
    doctor = current_user.doctor
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    appointment.status = 'confirmed'
    db.session.commit()
    
    # Send Notification
    try:
        NotificationService.send_appointment_status_update(
            appointment.patient, doctor, appointment, 'confirmed'
        )
    except Exception as e:
        print(f"Notification error: {e}")

    return jsonify({'success': True})

@doctor_bp.route('/appointments/<int:appointment_id>/reject', methods=['POST'])
@login_required
@doctor_required
def reject_appointment(appointment_id):
    """Reject appointment"""
    doctor = current_user.doctor
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    appointment.status = 'cancelled'
    db.session.commit()
    
    # Send Notification
    try:
        NotificationService.send_appointment_status_update(
            appointment.patient, doctor, appointment, 'cancelled'
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    return jsonify({'success': True})

@doctor_bp.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
@login_required
@doctor_required
def complete_appointment(appointment_id):
    """Mark appointment as completed"""
    doctor = current_user.doctor
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    appointment.status = 'completed'
    appointment.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

@doctor_bp.route('/prescription/write/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def write_prescription(patient_id):
    """Write prescription for patient"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check access
    if not _doctor_has_access(doctor, patient_id):
        flash('You do not have access to this patient', 'danger')
        return redirect(url_for('doctor.patient_list'))
    
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        medicines = request.form.get('medicines') or request.form.get('medication')
        dosage = request.form.get('dosage')
        frequency = request.form.get('frequency')
        duration = request.form.get('duration')
        instructions = request.form.get('instructions') or request.form.get('notes')
        diet_recommendations = request.form.get('diet_recommendations')
        exercise_recommendations = request.form.get('exercise_recommendations')
        
        prescription = Prescription(
            patient_id=patient_id,
            doctor_id=doctor.id,
            appointment_id=appointment_id if appointment_id else None,
            medicines=medicines,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            instructions=instructions,
            diet_recommendations=diet_recommendations,
            exercise_recommendations=exercise_recommendations
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        flash('Prescription saved successfully!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=patient_id))
    
    # Get completed appointments for this patient
    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id,
        patient_id=patient_id,
        status='completed').all()
    
    return render_template('doctor/write_prescription.html',
                         patient=patient,
                         appointments=appointments)

@doctor_bp.route('/messages')
@login_required
@doctor_required
def messages():
    """List of patients to chat with"""
    doctor = current_user.doctor
    
    # Get patients from appointments and existing messages
    appointment_patient_ids = [a.patient_id for a in Appointment.query.filter_by(doctor_id=doctor.id).all()]
    message_patient_ids = [m.patient_id for m in Message.query.filter_by(doctor_id=doctor.id).all()]
    
    # Unique patient IDs
    patient_ids = set(appointment_patient_ids + message_patient_ids)
    
    patients_list = []
    for p_id in patient_ids:
        patient = Patient.query.get(p_id)
        if patient:
            # Get unread count
            unread = Message.query.filter_by(
                doctor_id=doctor.id, 
                patient_id=p_id, 
                sender_type='patient', 
                is_read=False
            ).count()
            
            # Get last message
            last_msg = Message.query.filter(
                ((Message.doctor_id == doctor.id) & (Message.patient_id == p_id))
            ).order_by(Message.created_at.desc()).first()
            
            patients_list.append({
                'info': patient,
                'unread': unread,
                'last_message': last_msg
            })
    
    # If no patients found (new doctor), show some patients from directory
    if not patients_list:
        all_patients = Patient.query.limit(10).all()
        for patient in all_patients:
             patients_list.append({
                'info': patient,
                'unread': 0,
                'last_message': None
            })

    return render_template('doctor/messages.html', patients_list=patients_list)

@doctor_bp.route('/chat/<int:patient_id>')
@login_required
@doctor_required
def chat(patient_id):
    """Chat with patient"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check access
    if not _doctor_has_access(doctor, patient_id):
        flash('You do not have access to this patient', 'danger')
        return redirect(url_for('doctor.patient_list'))
    
    # Get messages
    messages = Message.query.filter(
        (Message.doctor_id == doctor.id) & (Message.patient_id == patient_id)
    ).order_by(Message.created_at).all()
    
    # Mark patient messages as read
    for msg in messages:
        if msg.sender_type == 'patient':
            msg.is_read = True
    db.session.commit()
    
    return render_template('doctor/chat.html', patient=patient, messages=messages)

@doctor_bp.route('/api/send-message/<int:patient_id>', methods=['POST'])
@login_required
@doctor_required
def send_message(patient_id):
    """Send message to patient (API)"""
    doctor = current_user.doctor
    data = request.get_json(silent=True) or {}
    
    message = Message(
        patient_id=patient_id,
        doctor_id=doctor.id,
        sender_type='doctor',
        message_text=data.get('message')
    )
    
    db.session.add(message)
    db.session.commit()
    
    try:
        from app.events import emit_to_user
        patient = Patient.query.get(patient_id)
        if patient and patient.user_id:
            emit_to_user(patient.user_id, 'new_message', {
                'message_id': message.id,
                'message_text': message.message_text,
                'patient_id': patient_id,
                'doctor_id': doctor.id,
                'sender_type': 'doctor',
                'created_at': message.created_at.isoformat() if message.created_at else datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"Socket emit failed: {e}")
        
    return jsonify({'success': True, 'message_id': message.id})

@doctor_bp.route('/analytics')
@login_required
@doctor_required
def analytics():
    """Analytics dashboard for doctor"""
    doctor = current_user.doctor
    
    # Get unique patients from appointments
    appointment_patient_ids = db.session.query(Appointment.patient_id.distinct()).filter_by(
        doctor_id=doctor.id).all()
    patient_ids = [ap[0] for ap in appointment_patient_ids] if appointment_patient_ids else []
    
    total_patients = len(patient_ids) if patient_ids else 0
    
    # Get appointment statistics
    total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
    completed_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, status='completed').count()
    pending_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, status='pending').count()
    
    # Get patient risk distribution
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    conditions = []
    age_stats = 0
    
    if patient_ids:
        # Get latest health data for each patient
        health_records = db.session.query(HealthData).filter(
            HealthData.patient_id.in_(patient_ids)
        ).order_by(HealthData.patient_id, HealthData.recorded_at.desc()).distinct(
            HealthData.patient_id).all()
        
        for health in health_records:
            avg_risk = (health.diabetes_risk + health.heart_disease_risk + health.hypertension_risk) / 3
            if avg_risk > 60:
                high_risk_count += 1
            elif avg_risk > 30:
                medium_risk_count += 1
            else:
                low_risk_count += 1
        
        # Calculate average age
        patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
        if patients:
            ages = [p.age for p in patients if p.age]
            if ages:
                age_stats = sum(ages) / len(ages)
        
        # Compile common conditions
        conditions = [
            ('Diabetes Risk', high_risk_count),
            ('Medium Risk', medium_risk_count),
            ('Low Risk', low_risk_count)
        ]
    
    return render_template('doctor/analytics.html',
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         completed_appointments=completed_appointments,
                         pending_appointments=pending_appointments,
                         high_risk_count=high_risk_count,
                         medium_risk_count=medium_risk_count,
                         low_risk_count=low_risk_count,
                         conditions=conditions,
                         age_stats=int(age_stats) if age_stats else 0)


@doctor_bp.route('/billing/create/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_bill(patient_id):
    """Create a bill for a patient"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check if doctor has access
    if not _doctor_has_access(doctor, patient_id):
        flash('You do not have access to this patient.', 'danger')
        return redirect(url_for('doctor.patient_list'))

    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        appointment_id = request.form.get('appointment_id')
        
        bill = Billing(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_id=int(appointment_id) if appointment_id else None,
            amount=amount,
            description=description,
            status='Unpaid'
        )
        
        db.session.add(bill)
        db.session.commit()
        
        flash('Bill created successfully!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=patient.id))
        
    # Get recent appointments for context
    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()).limit(5).all()
        
    return render_template('doctor/create_bill.html', 
                         patient=patient, 
                         appointments=appointments)



# ─── New Prescription Module ─────────────────────────


@doctor_bp.route('/prescription/create/<int:patient_id>')
@login_required
@doctor_required
def create_prescription(patient_id):
    """Render the hospital-style prescription editor page"""
    patient = Patient.query.get_or_404(patient_id)
    doctor = current_user.doctor
    try:
        medicines = Medicine.query.order_by(Medicine.name).all()
    except SQLAlchemyError:
        current_app.logger.exception("Failed to load medicines for prescription editor")
        medicines = []

    try:
        health_data = HealthData.query.filter_by(patient_id=patient.id).order_by(HealthData.recorded_at.desc()).all()
    except SQLAlchemyError:
        current_app.logger.exception("Failed to load health data for prescription editor")
        health_data = []

    return render_template('doctor/create_prescription.html', patient=patient, doctor=doctor, medicines=medicines, health_data=health_data)


@doctor_bp.route('/api/search-medicine')
@login_required
@doctor_required
def api_search_medicine():
    """Autocomplete medicine names for doctor prescription form."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])

    try:
        limit = int(request.args.get('limit', 12))
    except (TypeError, ValueError):
        limit = 12
    limit = max(1, min(limit, 25))

    prefix = f"{q}%"
    contains = f"%{q}%"

    medicines = (
        Medicine.query
        .filter(Medicine.name.ilike(contains))
        .order_by(
            case((Medicine.name.ilike(prefix), 0), else_=1),
            func.length(Medicine.name),
            Medicine.name.asc()
        )
        .limit(limit)
        .all()
    )

    names = []
    seen = set()
    for med in medicines:
        if not med.name:
            continue
        key = med.name.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        names.append(med.name)

    return jsonify(names)


@doctor_bp.route('/api/check-medicine', methods=['POST'])
@login_required
@doctor_required
def api_check_medicine():
    """Check one medicine against pharmacy inventory."""
    data = request.get_json(silent=True) or {}
    medicine = (data.get('medicine') or '').strip()
    if not medicine:
        return jsonify({'success': False, 'error': 'medicine is required'}), 400

    med = Medicine.query.filter(func.lower(Medicine.name) == medicine.lower()).first()
    if med is None:
        med = Medicine.query.filter(Medicine.name.ilike(medicine)).first()

    if med is None:
        return jsonify({
            'name': medicine,
            'status': 'not_found',
            'stock_quantity': 0
        })

    status = 'available' if (med.stock or 0) > 0 else 'out_of_stock'
    return jsonify({
        'name': med.name,
        'status': status,
        'stock_quantity': int(med.stock or 0)
    })



@doctor_bp.route('/api/prescription/create', methods=['POST'])
@login_required
@doctor_required
def api_create_prescription():
    """API to save a new prescription and its medicines.
    WORKFLOW: Also auto-creates PharmacyOrder for each medicine so pharmacy receives it immediately."""
    try:
        data = request.get_json(silent=True) or {}
        patient_id = data.get('patient_id')
        diagnosis = data.get('diagnosis', '')
        notes = data.get('notes', '')
        medicines = data.get('medicines', [])
        
        if not patient_id or not medicines:
            return jsonify({'success': False, 'error': 'Patient ID and Medicines are required'}), 400
        
        doctor = current_user.doctor

        def _has_column(model, name):
            return name in model.__table__.columns

        can_use_medicine_items = False
        try:
            can_use_medicine_items = inspect(db.engine).has_table(PrescriptionMedicine.__tablename__)
        except Exception:
            current_app.logger.exception('Could not inspect PrescriptionMedicine table; continuing without line items')

        try:
            prescription_fields = {
                'patient_id': patient_id,
                'doctor_id': doctor.id,
                'diagnosis': diagnosis,
                'notes': notes,
            }
            if _has_column(Prescription, 'medicines'):
                prescription_fields['medicines'] = '[]'

            new_prescription = Prescription(**prescription_fields)
            db.session.add(new_prescription)
            db.session.flush()

            for med in medicines:
                if can_use_medicine_items:
                    new_med = PrescriptionMedicine(
                        prescription_id=new_prescription.id,
                        medicine_name=med.get('medicine_name'),
                        dosage=med.get('dosage'),
                        frequency=med.get('frequency'),
                        duration=med.get('duration'),
                        instruction=med.get('instruction'),
                        food_relation=med.get('food_relation')
                    )
                    db.session.add(new_med)
                else:
                    current_app.logger.warning('PrescriptionMedicine table not present; skipping prescription line items')

                pharmacy_order = PharmacyOrder(
                    patient_id=patient_id,
                    doctor_id=doctor.id,
                    prescription_id=new_prescription.id,
                    medicine_name=med.get('medicine_name', ''),
                    quantity=1,
                    dosage=f"{med.get('dosage', '')} | {med.get('frequency', '')} | {med.get('duration', '')}",
                    status='Pending',
                    notes=f"{med.get('instruction', '')} ({med.get('food_relation', '')})"
                )
                db.session.add(pharmacy_order)

            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Prescription saved & sent to pharmacy automatically',
                'prescription_id': new_prescription.id
            })
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception('New prescription module save failed; trying legacy fallback')

        try:
            legacy_fields = {
                'patient_id': patient_id,
                'doctor_id': doctor.id,
                'diagnosis': diagnosis,
                'notes': notes,
            }
            if _has_column(Prescription, 'medicines'):
                legacy_fields['medicines'] = json.dumps(medicines)

            legacy_prescription = Prescription(**legacy_fields)
            db.session.add(legacy_prescription)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Prescription saved (legacy mode).',
                'prescription_id': legacy_prescription.id
            })
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception('Legacy prescription fallback save failed')
            return jsonify({'success': False, 'error': 'Could not save prescription due to database schema mismatch. Please run DB migration.'}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Unexpected prescription save failure')
        return jsonify({'success': False, 'error': f'Unexpected server error: {str(e)}'}), 500

@doctor_bp.route('/api/prescription/<int:id>', methods=['GET'])
@login_required
def api_get_prescription(id):
    """API to fetch full prescription details for printing/previewing"""
    prescription = Prescription.query.get_or_404(id)
    
    # Security: Only involved doctor or patient, or admin/host
    if current_user.role.value == 'PATIENT' and prescription.patient.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    elif current_user.role.value == 'DOCTOR' and prescription.doctor.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    meds = []
    for m in prescription.medicine_items:
        meds.append({
            'medicine_name': m.medicine_name,
            'dosage': m.dosage,
            'frequency': m.frequency,
            'duration': m.duration,
            'instruction': m.instruction,
            'food_relation': m.food_relation
        })
        
    return jsonify({
        'success': True,
        'prescription': {
            'id': prescription.id,
            'date': prescription.prescribed_at.strftime('%Y-%m-%d %I:%M %p'),
            'diagnosis': prescription.diagnosis,
            'notes': prescription.notes,
            'doctor_name': f"Dr. {prescription.doctor.first_name} {prescription.doctor.last_name}",
            'patient_name': f"{prescription.patient.first_name} {prescription.patient.last_name}",
            'patient_age': prescription.patient.age_str() if hasattr(prescription.patient, 'age_str') else prescription.patient.age,
            'patient_gender': prescription.patient.gender,
            'medicines': meds
        }
    })


@doctor_bp.route('/prescription/print/<int:id>')
@login_required
def print_prescription(id):
    """Printable e-prescription with branding and QR verification payload."""
    prescription = Prescription.query.get_or_404(id)

    if current_user.role.value == 'PATIENT' and prescription.patient.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    elif current_user.role.value == 'DOCTOR' and prescription.doctor.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    meds = []
    for m in prescription.medicine_items:
        meds.append({
            'name': m.medicine_name,
            'dosage': m.dosage or '',
            'frequency': m.frequency or '',
            'duration': m.duration or '',
            'instruction': m.instruction or ''
        })

    payload = {
        'prescription_id': prescription.id,
        'patient_id': prescription.patient_id,
        'doctor_id': prescription.doctor_id,
        'issued_at': prescription.prescribed_at.strftime('%Y-%m-%d %H:%M')
    }
    token_base = f"{payload['prescription_id']}|{payload['patient_id']}|{payload['doctor_id']}|{payload['issued_at']}"
    verify_token = hashlib.sha256(token_base.encode('utf-8')).hexdigest()[:24]

    return render_template(
        'doctor/prescription_print.html',
        prescription=prescription,
        medicines=meds,
        verify_token=verify_token,
        qr_payload=json.dumps({**payload, 'token': verify_token})
    )

@doctor_bp.route('/api/patient/<int:patient_id>/prescriptions', methods=['GET'])
@login_required
def api_patient_prescriptions(patient_id):
    """GET list of a patient's prescriptions"""
    if current_user.role.value == 'PATIENT' and current_user.patient and current_user.patient.id != patient_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.prescribed_at.desc()).all()
    results = []
    for p in prescriptions:
        results.append({
            'id': p.id,
            'date': p.prescribed_at.strftime('%Y-%m-%d %I:%M %p'),
            'doctor_name': f"Dr. {p.doctor.first_name} {p.doctor.last_name}",
            'diagnosis': p.diagnosis
        })
    return jsonify({'success': True, 'prescriptions': results})


# ─── Doctor Lab Requests ────────────────────────────────────────────────

def _get_current_doctor():
    doctor = getattr(current_user, 'doctor', None)
    if not doctor:
        flash('Doctor profile not found. Please contact admin.', 'danger')
    return doctor


@doctor_bp.route('/lab-requests')
@login_required
@doctor_required
def lab_requests():
    """Doctor-referred lab orders only (walk-in has doctor_id NULL)."""
    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for('doctor.portal'))

    reports = LabOrder.query.filter_by(doctor_id=doctor.id).order_by(
        LabOrder.created_at.desc()).all()
    return render_template('doctor/lab_requests.html', reports=reports, doctor=doctor)


@doctor_bp.route('/lab-reports')
@login_required
@doctor_required
def lab_reports_view():
    """Completed lab orders for this doctor's referrals (not walk-in)."""
    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for('doctor.portal'))

    reports = LabOrder.query.filter_by(doctor_id=doctor.id, status='COMPLETED').order_by(
        LabOrder.updated_at.desc()).all()
    return render_template('doctor/lab_reports.html', reports=reports, doctor=doctor)


@doctor_bp.route('/pharmacy-orders')
@login_required
@doctor_required
def pharmacy_orders():
    """View pharmacy orders created from this doctor's prescriptions"""
    doctor = current_user.doctor
    orders = PharmacyOrder.query.filter_by(doctor_id=doctor.id).order_by(
        PharmacyOrder.created_at.desc()).all()
    return render_template('doctor/pharmacy_orders.html', orders=orders, doctor=doctor)


@doctor_bp.route('/api/lab/request', methods=['POST'])
@login_required
@doctor_required
def api_request_lab_test():
    """Doctor requests a lab test directly from the doctor dashboard"""
    from app.routes.lab import _create_lab_order_row, SOURCE_DOCTOR

    data = request.get_json()
    patient_id = data.get('patient_id')
    test_name = data.get('test_name')
    notes = data.get('notes', '')

    if not patient_id or not test_name:
        return jsonify({'success': False, 'error': 'Patient and test name are required'}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    doctor = current_user.doctor
    try:
        order = _create_lab_order_row(
            patient.id, test_name.strip(), SOURCE_DOCTOR, doctor.id,
            notes=notes.strip() or None,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('api_request_lab_test')
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({
        'success': True,
        'order_id': order.id,
        'report_id': order.id,
        'message': f'Lab test "{test_name}" requested successfully',
    })


@doctor_bp.route('/api/lab/create-report', methods=['POST'])
@login_required
@doctor_required
def api_create_lab_report():
    """Create a full lab report with test panels and results directly from OP panel."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    tests = data.get('tests', [])  # list of {test_name, result_value, unit, reference_range, is_abnormal}
    panel_name = data.get('panel_name', 'General Laboratory Panel')
    notes = data.get('notes', '')

    if not patient_id or not tests:
        return jsonify({'success': False, 'error': 'Patient ID and at least one test are required'}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    doctor = current_user.doctor
    report_ids = []
    try:
        for t in tests:
            test_name = (t.get('test_name') or '').strip()
            if not test_name:
                continue
            result_value = (t.get('result_value') or '').strip()
            is_abnormal = bool(t.get('is_abnormal', False))
            report_data = {}
            if result_value:
                report_data['Result'] = result_value
            if (t.get('unit') or '').strip():
                report_data['Unit'] = (t.get('unit') or '').strip()
            if (t.get('reference_range') or '').strip():
                report_data['Reference Range'] = (t.get('reference_range') or '').strip()

            report = LabReport(
                patient_id=patient_id,
                doctor_id=doctor.id,
                test_name=t.get('panel_name', panel_name) + ' — ' + test_name if t.get('panel_name') else test_name,
                result_value=result_value,
                unit=(t.get('unit') or '').strip(),
                reference_range=(t.get('reference_range') or '').strip(),
                report_data=report_data or None,
                status='Completed',
                notes=notes,
                remarks=f"Panel: {panel_name}",
                critical_alert=is_abnormal,
                conducted_at=datetime.utcnow()
            )
            db.session.add(report)
            db.session.flush()
            report_ids.append(report.id)
        db.session.commit()
        first_id = report_ids[0] if report_ids else None
        return jsonify({
            'success': True,
            'report_ids': report_ids,
            'print_url': url_for('doctor.print_lab_report', report_id=first_id, _external=False) if first_id else None,
            'message': f'Lab report with {len(report_ids)} test(s) saved successfully'
        })
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception('Failed to save lab report')
        return jsonify({'success': False, 'error': 'Database error saving lab report'}), 500
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unexpected error while saving lab report')
        return jsonify({'success': False, 'error': 'Unexpected server error while saving lab report'}), 500


@doctor_bp.route('/lab-report/print/<int:report_id>')
@login_required
def print_lab_report(report_id):
    """Render a printable lab report for an OP patient."""
    report = LabReport.query.get_or_404(report_id)
    # Security: only the doctor who created it or the patient it belongs to
    if current_user.role.value == 'DOCTOR' and report.doctor and report.doctor.user_id != current_user.id:
        flash('Unauthorized access to lab report.', 'danger')
        return redirect(url_for('doctor.portal'))
    if current_user.role.value == 'PATIENT' and report.patient.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('patient.dashboard'))

    # Get all reports in the same panel/session (same patient + doctor + date)
    from datetime import timedelta
    panel_reports = LabReport.query.filter(
        LabReport.patient_id == report.patient_id,
        LabReport.doctor_id == report.doctor_id,
        LabReport.conducted_at.between(
            report.conducted_at - timedelta(minutes=5),
            report.conducted_at + timedelta(minutes=5)
        )
    ).all()

    return render_template('doctor/lab_report_print.html',
                           report=report,
                           panel_reports=panel_reports,
                           patient=report.patient,
                           doctor=report.doctor)


def _doctor_patient_ids(doctor_id):
    """Return all patient IDs a doctor can legitimately access."""
    appt_ids = db.session.query(Appointment.patient_id).filter_by(doctor_id=doctor_id).distinct().all()
    queue_ids = db.session.query(ReceptionQueue.patient_id).filter_by(doctor_id=doctor_id).distinct().all()
    rx_ids = db.session.query(Prescription.patient_id).filter_by(doctor_id=doctor_id).distinct().all()
    checkin_ids = db.session.query(PatientCheckIn.patient_id).filter_by(doctor_id=doctor_id).distinct().all()
    return {row[0] for row in (appt_ids + queue_ids + rx_ids + checkin_ids) if row and row[0]}


def _parse_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _is_abnormal(result_value, reference_range):
    """Best-effort abnormal flag based on numeric result and range like '70-110'."""
    rv = _parse_float(result_value)
    if rv is None or not reference_range:
        return False
    cleaned = str(reference_range).replace(" ", "")
    if "-" not in cleaned:
        return False
    parts = cleaned.split("-", 1)
    low = _parse_float(parts[0])
    high = _parse_float(parts[1])
    if low is None or high is None:
        return False
    return rv < low or rv > high


def _medicines_from_payload(payload_medicines):
    meds = []
    for med in payload_medicines or []:
        name = (med.get('medicine_name') or '').strip()
        if not name:
            continue
        meds.append({
            'medicine_name': name,
            'dosage': (med.get('dosage') or '').strip(),
            'frequency': (med.get('frequency') or '').strip(),
            'duration': (med.get('duration') or '').strip(),
            'instruction': (med.get('instruction') or '').strip(),
            'food_relation': (med.get('food_relation') or '').strip(),
        })
    return meds


def _normalize_med_name(name):
    return ' '.join((name or '').strip().lower().split())


def _drug_interaction_alerts(med_names):
    alerts = []
    meds = {_normalize_med_name(x) for x in med_names if _normalize_med_name(x)}
    for pair, warning in DRUG_INTERACTION_RULES.items():
        if pair.issubset(meds):
            label = " + ".join([x.title() for x in sorted(pair)])
            alerts.append({
                'type': 'drug_interaction',
                'severity': 'high',
                'message': f'Interaction warning ({label}): {warning}'
            })
    return alerts


def _build_clinical_alerts(patient, medicines):
    alerts = []
    med_names = [m['medicine_name'] for m in medicines if m.get('medicine_name')]
    med_names_lower = [_normalize_med_name(m) for m in med_names]

    # 1) Drug allergy warning
    allergy_text = _normalize_med_name(patient.allergies or '')
    known_allergies = [a.strip() for a in allergy_text.replace(';', ',').split(',') if a.strip()]
    for med in med_names:
        med_l = _normalize_med_name(med)
        allergy_hit = med_l and (med_l in allergy_text or any(a in med_l or med_l in a for a in known_allergies))
        if allergy_hit:
            alerts.append({
                'type': 'drug_allergy',
                'severity': 'high',
                'message': f'Allergy warning: {patient.first_name} may be allergic to {med}.'
            })

    # 2) Duplicate medicines in same prescription draft
    seen = set()
    duplicates = set()
    for med_l in med_names_lower:
        if med_l in seen:
            duplicates.add(med_l)
        seen.add(med_l)
    for dup in duplicates:
        alerts.append({
            'type': 'drug_duplication',
            'severity': 'medium',
            'message': f'Duplicate medicine in current prescription: {dup.title()}.'
        })

    # 2.5) Drug-drug interaction checks
    alerts.extend(_drug_interaction_alerts(med_names_lower))

    # 3) Duplicate with very recent prescriptions
    recent_rx = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.prescribed_at.desc()).limit(5).all()
    recent_meds = set()
    for rx in recent_rx:
        try:
            for pm in rx.medicine_items:
                if pm.medicine_name:
                    recent_meds.add(_normalize_med_name(pm.medicine_name))
        except Exception:
            pass
        raw = (rx.medicines or '').strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            n = _normalize_med_name(item.get('medicine_name') or '')
                            if n:
                                recent_meds.add(n)
                        elif isinstance(item, str):
                            recent_meds.add(_normalize_med_name(item))
            except Exception:
                for part in raw.split(','):
                    name = _normalize_med_name(part)
                    if name:
                        recent_meds.add(name)

    for med_l in med_names_lower:
        if med_l in recent_meds:
            alerts.append({
                'type': 'drug_duplication',
                'severity': 'low',
                'message': f'{med_l.title()} was prescribed recently. Confirm continuation/duplication.'
            })

    # 4) Abnormal lab value alerts
    recent_labs = LabReport.query.filter_by(patient_id=patient.id, status='Completed').order_by(
        LabReport.conducted_at.desc()).limit(10).all()
    for lab in recent_labs:
        if _is_abnormal(lab.result_value, lab.reference_range):
            alerts.append({
                'type': 'abnormal_lab',
                'severity': 'high',
                'message': f'Abnormal lab: {lab.test_name} = {lab.result_value} (Ref: {lab.reference_range}).'
            })

    # 5) Critical patient alerts from latest vitals / risk scores
    latest_health = HealthData.query.filter_by(patient_id=patient.id).order_by(
        HealthData.recorded_at.desc()).first()
    if latest_health:
        if (latest_health.diabetes_risk or 0) >= 80 or (latest_health.heart_disease_risk or 0) >= 80 or (latest_health.hypertension_risk or 0) >= 80:
            alerts.append({
                'type': 'critical_risk',
                'severity': 'high',
                'message': 'Critical risk score is high (>= 80). Prioritize close monitoring.'
            })
        if (latest_health.systolic_bp or 0) >= 180 or (latest_health.diastolic_bp or 0) >= 120:
            alerts.append({
                'type': 'critical_vitals',
                'severity': 'high',
                'message': 'Critical BP recorded in latest vitals.'
            })
        if (latest_health.heart_rate or 0) >= 120:
            alerts.append({
                'type': 'critical_vitals',
                'severity': 'high',
                'message': 'Tachycardia alert: Heart rate is above safe threshold.'
            })
        if (latest_health.temperature or 0) >= 101.0:
            alerts.append({
                'type': 'critical_vitals',
                'severity': 'high',
                'message': 'Fever alert: Temperature is above safe threshold.'
            })

    return alerts
@doctor_bp.route('/api/patients/search', methods=['GET'])
@login_required
@doctor_required
def api_search_patients():
    """Search patient by UHID / ID / phone / name, only from doctor's accessible pool."""
    doctor = current_user.doctor
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'success': True, 'patients': []})

    q_upper = q.upper()
    allowed_ids = _doctor_patient_ids(doctor.id)
    if not allowed_ids:
        return jsonify({'success': True, 'patients': []})

    query = Patient.query.filter(Patient.id.in_(allowed_ids))
    if q.isdigit():
        query = query.filter(
            db.or_(
                Patient.id == int(q),
                Patient.phone.ilike(f'%{q}%'),
                Patient.uhid.ilike(f'%{q_upper}%')
            )
        )
    else:
        query = query.filter(
            db.or_(
                Patient.uhid.ilike(f'%{q_upper}%'),
                Patient.name.ilike(f'%{q}%'),
                Patient.first_name.ilike(f'%{q}%'),
                Patient.last_name.ilike(f'%{q}%'),
                Patient.phone.ilike(f'%{q}%')
            )
        )

    patients = query.order_by(Patient.first_name.asc()).limit(30).all()
    return jsonify({
        'success': True,
        'patients': [{
            'id': p.id,
            'name': f"{p.first_name} {p.last_name}",
            'uhid': p.uhid,
            'phone': p.phone or '',
            'age': p.age,
            'gender': p.gender,
            'allergies': p.allergies or '',
            'chronic_history': p.medical_history or ''
        } for p in patients]
    })


@doctor_bp.route('/api/patient/<int:patient_id>/emr', methods=['GET'])
@login_required
@doctor_required
def api_patient_emr(patient_id):
    """Full EMR view payload with timeline."""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    if not _doctor_has_access(doctor, patient_id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()).all()
    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id).order_by(Prescription.prescribed_at.desc()).all()
    labs = LabReport.query.filter_by(patient_id=patient_id).order_by(
        LabReport.conducted_at.desc()).all()
    health = HealthData.query.filter_by(patient_id=patient_id).order_by(
        HealthData.recorded_at.desc()).all()
    vitals = PatientVitals.query.filter_by(patient_id=patient_id).order_by(
        PatientVitals.recorded_at.desc()).all()
    bills = Billing.query.filter_by(patient_id=patient_id).order_by(
        Billing.created_at.desc()).all()
    docs = MedicalImage.query.filter_by(patient_id=patient_id).order_by(
        MedicalImage.uploaded_at.desc()).all()

    timeline = []
    for a in appointments:
        timeline.append({
            'type': 'appointment',
            'time': a.appointment_date,
            'title': f'Appointment ({a.status})',
            'details': a.reason or ''
        })
    for rx in prescriptions:
        timeline.append({
            'type': 'prescription',
            'time': rx.prescribed_at,
            'title': 'Prescription created',
            'details': rx.diagnosis or ''
        })
    for lab in labs:
        timeline.append({
            'type': 'lab',
            'time': lab.conducted_at or lab.created_at,
            'title': f'Lab: {lab.test_name} ({lab.status})',
            'details': f"Result: {lab.result_value or 'Pending'}"
        })
    for h in health:
        timeline.append({
            'type': 'vitals',
            'time': h.recorded_at,
            'title': 'Vitals updated',
            'details': f"BP {h.systolic_bp or '-'} / {h.diastolic_bp or '-'}, HR {h.heart_rate or '-'}"
        })
    for d in docs:
        timeline.append({
            'type': 'document',
            'time': d.uploaded_at,
            'title': f"Document: {d.image_type or 'medical image'}",
            'details': d.original_filename or d.filename
        })
    for b in bills:
        timeline.append({
            'type': 'procedure',
            'time': b.created_at,
            'title': 'Procedure / Billing Entry',
            'details': b.description or ''
        })

    timeline.sort(key=lambda x: x['time'] or datetime.min, reverse=True)

    def _rx_medicines(rx):
        meds = []
        try:
            for m in rx.medicine_items:
                meds.append({
                    'name': m.medicine_name,
                    'dosage': m.dosage,
                    'frequency': m.frequency,
                    'duration': m.duration,
                    'instruction': m.instruction
                })
        except Exception:
            pass
        if meds:
            return meds
        raw = rx.medicines or ''
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                out = []
                for item in parsed:
                    if isinstance(item, dict):
                        out.append({
                            'name': item.get('medicine_name') or '',
                            'dosage': item.get('dosage') or '',
                            'frequency': item.get('frequency') or '',
                            'duration': item.get('duration') or '',
                            'instruction': item.get('instruction') or ''
                        })
                    elif isinstance(item, str):
                        out.append({'name': item, 'dosage': '', 'frequency': '', 'duration': '', 'instruction': ''})
                return out
        except Exception:
            pass
        return [{'name': x.strip(), 'dosage': '', 'frequency': '', 'duration': '', 'instruction': ''} for x in raw.split(',') if x.strip()]

    return jsonify({
        'success': True,
        'patient': {
            'id': patient.id,
            'uhid': patient.uhid,
            'name': f"{patient.first_name} {patient.last_name}",
            'age': patient.age,
            'gender': patient.gender,
            'phone': patient.phone or '',
            'blood_type': patient.blood_type or '',
            'allergies': patient.allergies or '',
            'chronic_diseases': patient.medical_history or '',
            'address': patient.address or ''
        },
        'appointments': [{
            'id': a.id,
            'date': a.appointment_date.strftime('%Y-%m-%d %H:%M'),
            'status': a.status,
            'reason': a.reason,
            'notes': a.notes or ''
        } for a in appointments[:50]],
        'prescriptions': [{
            'id': rx.id,
            'date': rx.prescribed_at.strftime('%Y-%m-%d %H:%M'),
            'diagnosis': rx.diagnosis or '',
            'notes': rx.notes or '',
            'medicines': _rx_medicines(rx)
        } for rx in prescriptions[:50]],
        'lab_reports': [{
            'id': l.id,
            'test_name': l.test_name,
            'status': l.status,
            'result_value': l.result_value or '',
            'unit': l.unit or '',
            'reference_range': l.reference_range or '',
            'abnormal': _is_abnormal(l.result_value, l.reference_range),
            'date': (l.conducted_at or l.created_at).strftime('%Y-%m-%d %H:%M')
        } for l in labs[:100]],
        'vitals': [{
            'id': h.id,
            'date': h.recorded_at.strftime('%Y-%m-%d %H:%M'),
            'symptoms': h.symptoms or '',
            'bp': f"{h.systolic_bp or '-'} / {h.diastolic_bp or '-'}",
            'heart_rate': h.heart_rate or '',
            'temperature': h.temperature or '',
            'diabetes_risk': h.diabetes_risk or 0,
            'heart_disease_risk': h.heart_disease_risk or 0,
            'hypertension_risk': h.hypertension_risk or 0
        } for h in health[:100]],
        'documents': [{
            'id': d.id,
            'name': d.original_filename or d.filename,
            'type': d.image_type or '',
            'uploaded_at': d.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            'file_path': d.file_path,
            'clinical_context': d.clinical_context or ''
        } for d in docs[:100]],
        'billing': [{
            'id': b.id,
            'amount': b.amount,
            'status': b.status,
            'description': b.description,
            'date': b.created_at.strftime('%Y-%m-%d %H:%M')
        } for b in bills[:50]],
        'timeline': [{
            'type': t['type'],
            'title': t['title'],
            'details': t['details'],
            'time': (t['time'] or datetime.min).strftime('%Y-%m-%d %H:%M')
        } for t in timeline[:200]]
    })


@doctor_bp.route('/api/clinical-alerts', methods=['POST'])
@login_required
@doctor_required
def api_clinical_alerts():
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)
    doctor = current_user.doctor
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    if not _doctor_has_access(doctor, patient.id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    medicines = _medicines_from_payload(data.get('medicines', []))
    alerts = _build_clinical_alerts(patient, medicines)
    pharmacy_status = _pharmacy_status_for_medicines(medicines)
    return jsonify({'success': True, 'alerts': alerts, 'pharmacy_status': pharmacy_status})


@doctor_bp.route('/api/clinical-templates', methods=['GET'])
@login_required
@doctor_required
def api_clinical_templates():
    templates = [{'key': k, **v} for k, v in CLINICAL_TEMPLATES.items()]
    return jsonify({'success': True, 'templates': templates})


@doctor_bp.route('/api/decision-support', methods=['POST'])
@login_required
@doctor_required
def api_decision_support():
    data = request.get_json(silent=True) or {}
    symptoms = (data.get('symptoms') or '').lower()
    if not symptoms:
        return jsonify({'success': True, 'suggestions': [], 'recommended_labs': [], 'triage_level': 'routine'})

    suggestions = []
    labs = set()
    triage = 'routine'

    if 'chest pain' in symptoms or 'breathless' in symptoms or 'shortness of breath' in symptoms:
        triage = 'urgent'
        suggestions.append('Rule out acute coronary syndrome and respiratory compromise.')
        labs.update(['ECG', 'Troponin', 'Chest X-Ray'])
    if 'fever' in symptoms:
        suggestions.append('Consider infectious workup and hydration status assessment.')
        labs.update(['CBC', 'CRP'])
    if 'polyuria' in symptoms or 'polydipsia' in symptoms or 'high sugar' in symptoms:
        suggestions.append('Screen for glycemic decompensation and diabetes control.')
        labs.update(['HbA1c', 'Fasting Blood Sugar'])
    if 'headache' in symptoms and ('bp' in symptoms or 'blood pressure' in symptoms):
        suggestions.append('Evaluate hypertension urgency and secondary causes if persistent.')
        labs.update(['Renal Function Test'])
    if 'cough' in symptoms:
        suggestions.append('Assess severity, oxygenation, and differential including infection.')
        labs.update(['CBC'])

    if not suggestions:
        suggestions.append('Use symptom progression, vitals trend, and prior EMR timeline for diagnosis refinement.')

    return jsonify({
        'success': True,
        'suggestions': suggestions[:6],
        'recommended_labs': sorted(list(labs))[:8],
        'triage_level': triage
    })


@doctor_bp.route('/api/internal-messages', methods=['GET', 'POST'])
@login_required
@doctor_required
def api_internal_messages():
    doctor = current_user.doctor
    allowed_types = [
        'doctor_to_lab', 'doctor_to_pharmacy', 'doctor_to_reception',
        'lab_to_doctor', 'pharmacy_to_doctor', 'reception_to_doctor'
    ]
    if request.method == 'GET':
        patient_id = request.args.get('patient_id', type=int)
        query = Message.query.filter(
            Message.doctor_id == doctor.id,
            Message.sender_type.in_(allowed_types)
        )
        if patient_id:
            if not _doctor_has_access(doctor, patient_id):
                return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403
            query = query.filter(Message.patient_id == patient_id)

        msgs = query.order_by(Message.created_at.desc()).limit(150).all()
        return jsonify({'success': True, 'messages': [{
            'id': m.id,
            'patient_id': m.patient_id,
            'patient_name': (f"{m.patient.first_name} {m.patient.last_name}" if m.patient else 'Unknown'),
            'sender_type': m.sender_type,
            'message_text': m.message_text,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M')
        } for m in msgs]})

    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    channel = (data.get('channel') or '').strip().lower()
    text = (data.get('message') or '').strip()
    if not patient_id or not text:
        return jsonify({'success': False, 'error': 'patient_id and message are required'}), 400
    if not _doctor_has_access(doctor, patient_id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    sender_map = {
        'lab': 'doctor_to_lab',
        'pharmacy': 'doctor_to_pharmacy',
        'reception': 'doctor_to_reception'
    }
    sender_type = sender_map.get(channel)
    if not sender_type:
        return jsonify({'success': False, 'error': 'Unsupported channel'}), 400
    msg = Message(
        patient_id=patient_id,
        doctor_id=doctor.id,
        sender_type=sender_type,
        message_text=text
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True, 'message_id': msg.id})


@doctor_bp.route('/api/visit-summary', methods=['POST'])
@login_required
@doctor_required
def api_visit_summary():
    doctor = current_user.doctor
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    if not _doctor_has_access(doctor, patient.id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    diagnosis = (data.get('diagnosis') or '').strip()
    symptoms = (data.get('symptoms') or '').strip()
    notes = (data.get('consultation_notes') or '').strip()
    followup_date = (data.get('followup_date') or '').strip()
    medicines = data.get('medicines') or []
    med_text = ', '.join([m.get('medicine_name', '').strip() for m in medicines if m.get('medicine_name')])

    summary = (
        f"Visit Summary\n"
        f"Patient: {patient.first_name} {patient.last_name}\n"
        f"Doctor: Dr. {doctor.first_name} {doctor.last_name}\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Symptoms: {symptoms or 'N/A'}\n"
        f"Diagnosis: {diagnosis or 'N/A'}\n"
        f"Notes: {notes or 'N/A'}\n"
        f"Medicines: {med_text or 'N/A'}\n"
        f"Follow-up: {followup_date or 'Not scheduled'}\n"
    )

    sent_email = False
    sent_sms = False
    try:
        if patient.user and patient.user.email:
            NotificationService.send_email(patient.user.email, "Your Visit Summary", summary)
            sent_email = True
    except Exception:
        current_app.logger.exception("Failed to send visit summary email")
    try:
        if patient.phone:
            sms_line = f"Visit summary: Dx {diagnosis or 'N/A'}. Follow-up: {followup_date or 'NA'}."
            NotificationService.send_sms(patient.phone, sms_line[:150])
            sent_sms = True
    except Exception:
        current_app.logger.exception("Failed to send visit summary sms")

    return jsonify({'success': True, 'summary': summary, 'sent_email': sent_email, 'sent_sms': sent_sms})


@doctor_bp.route('/api/consultation/save', methods=['POST'])
@login_required
@doctor_required
def api_consultation_save():
    """End-to-end consultation save: EMR update + Rx + Lab + Pharmacy + follow-up."""
    data = request.get_json(silent=True) or {}
    doctor = current_user.doctor
    patient_id = data.get('patient_id')
    appointment_id = data.get('appointment_id')
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    if not _doctor_has_access(doctor, patient.id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    symptoms = (data.get('symptoms') or '').strip()
    diagnosis = (data.get('diagnosis') or '').strip()
    consultation_notes = (data.get('consultation_notes') or '').strip()
    followup_notes = (data.get('followup_notes') or '').strip()
    followup_date_raw = (data.get('followup_date') or '').strip()
    medicines = _medicines_from_payload(data.get('medicines', []))
    lab_tests = [str(x).strip() for x in (data.get('lab_tests') or []) if str(x).strip()]
    vitals = data.get('vitals') or {}

    alerts = _build_clinical_alerts(patient, medicines)
    pharmacy_status = _pharmacy_status_for_medicines(medicines)

    created = {
        'health_data_id': None,
        'prescription_id': None,
        'lab_report_ids': [],
        'lab_order_ids': [],
        'pharmacy_order_ids': [],
        'followup_appointment_id': None
    }

    try:
        # EMR update: add new health record if clinician entered symptoms/vitals.
        has_vitals = any(vitals.get(k) not in (None, '', []) for k in ['systolic_bp', 'diastolic_bp', 'heart_rate', 'temperature'])
        if symptoms or has_vitals:
            hd = HealthData(
                patient_id=patient.id,
                symptoms=symptoms or None,
                systolic_bp=int(vitals.get('systolic_bp')) if str(vitals.get('systolic_bp', '')).isdigit() else None,
                diastolic_bp=int(vitals.get('diastolic_bp')) if str(vitals.get('diastolic_bp', '')).isdigit() else None,
                heart_rate=int(vitals.get('heart_rate')) if str(vitals.get('heart_rate', '')).isdigit() else None,
                temperature=_parse_float(vitals.get('temperature')),
                recorded_at=datetime.utcnow()
            )
            db.session.add(hd)
            db.session.flush()
            created['health_data_id'] = hd.id

        # Link consultation summary to appointment.
        if appointment_id:
            appt = Appointment.query.filter_by(id=appointment_id, doctor_id=doctor.id, patient_id=patient.id).first()
            if appt:
                merged_note_parts = [x for x in [appt.notes or '', consultation_notes, f"Diagnosis: {diagnosis}" if diagnosis else ''] if x]
                appt.notes = "\n\n".join(merged_note_parts)
                if appt.status in ('pending', 'confirmed'):
                    appt.status = 'completed'
                appt.updated_at = datetime.utcnow()

        # Prescription + automatic pharmacy orders.
        if medicines or diagnosis or consultation_notes:
            rx = Prescription(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_id=appointment_id if appointment_id else None,
                diagnosis=diagnosis or None,
                notes=consultation_notes or None,
                medicines='[]'
            )
            db.session.add(rx)
            db.session.flush()
            created['prescription_id'] = rx.id

            for med in medicines:
                rx_med = PrescriptionMedicine(
                    prescription_id=rx.id,
                    medicine_name=med['medicine_name'],
                    dosage=med['dosage'],
                    frequency=med['frequency'],
                    duration=med['duration'],
                    instruction=med['instruction'],
                    food_relation=med['food_relation']
                )
                db.session.add(rx_med)

                order = PharmacyOrder(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    prescription_id=rx.id,
                    medicine_name=med['medicine_name'],
                    quantity=1,
                    dosage=f"{med['dosage']} | {med['frequency']} | {med['duration']}",
                    status='Pending',
                    notes=med['instruction']
                )
                db.session.add(order)
                db.session.flush()
                created['pharmacy_order_ids'].append(order.id)

        # Lab orders (unified workflow — doctor-referred)
        from app.routes.lab import _create_lab_order_row, SOURCE_DOCTOR
        lab_notes = consultation_notes or diagnosis or 'Ordered during consultation'
        for test_name in lab_tests:
            lo = _create_lab_order_row(
                patient.id,
                test_name,
                SOURCE_DOCTOR,
                doctor.id,
                notes=lab_notes,
            )
            db.session.flush()
            created['lab_order_ids'].append(lo.id)
            created['lab_report_ids'].append(lo.id)

        # Follow-up schedule
        if followup_date_raw:
            followup_date = None
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'):
                try:
                    followup_date = datetime.strptime(followup_date_raw, fmt)
                    break
                except ValueError:
                    continue
            if followup_date is None:
                return jsonify({'success': False, 'error': 'Invalid follow-up date format'}), 400
            if followup_date.hour == 0 and followup_date.minute == 0:
                followup_date = followup_date.replace(hour=10, minute=0)

            fup = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=followup_date,
                reason=f"Follow-up: {diagnosis or 'Consultation review'}",
                status='pending',
                notes=followup_notes or 'Follow-up scheduled by doctor'
            )
            db.session.add(fup)
            db.session.flush()
            created['followup_appointment_id'] = fup.id

            try:
                NotificationService.send_email(
                    patient.user.email,
                    "Follow-up Appointment Scheduled",
                    (
                        f"Dear {patient.first_name},\n\n"
                        f"Your follow-up visit with Dr. {doctor.first_name} {doctor.last_name} is scheduled on "
                        f"{followup_date.strftime('%Y-%m-%d %I:%M %p')}.\n\n"
                        f"Notes: {followup_notes or 'Please attend on time.'}\n\n"
                        "Regards,\nHospital Team"
                    )
                )
                if patient.phone:
                    NotificationService.send_sms(
                        patient.phone,
                        f"Follow-up scheduled on {followup_date.strftime('%Y-%m-%d %I:%M %p')} with Dr. {doctor.last_name}."
                    )
            except Exception:
                current_app.logger.exception("Failed to send follow-up notification")

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Consultation saved successfully',
            'created': created,
            'alerts': alerts,
            'pharmacy_status': pharmacy_status
        })
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Consultation save failed")
        return jsonify({'success': False, 'error': str(exc)}), 500


@doctor_bp.route('/api/consultation/upload-document', methods=['POST'])
@login_required
@doctor_required
def api_upload_consultation_document():
    """Upload medical document/image and link it to patient EMR."""
    doctor = current_user.doctor
    patient_id = request.form.get('patient_id')
    document_type = (request.form.get('document_type') or 'clinical-document').strip()
    clinical_context = (request.form.get('clinical_context') or '').strip()

    if not patient_id:
        return jsonify({'success': False, 'error': 'patient_id is required'}), 400
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    if not _doctor_has_access(doctor, patient.id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'Invalid file'}), 400

    allowed = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'success': False, 'error': f'Unsupported file type: .{ext}'}), 400

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'medical_images')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file.filename)
    save_name = f"doctor_{doctor.id}_patient_{patient.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    abs_path = os.path.join(upload_dir, save_name)
    file.save(abs_path)

    rel_path = f"uploads/medical_images/{save_name}"
    doc = MedicalImage(
        patient_id=patient.id,
        filename=save_name,
        original_filename=filename,
        image_type=document_type,
        clinical_context=clinical_context,
        file_path=rel_path,
        uploaded_at=datetime.utcnow()
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Document uploaded',
        'document': {
            'id': doc.id,
            'name': doc.original_filename,
            'type': doc.image_type,
            'file_path': doc.file_path,
            'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d %H:%M')
        }
    })


@doctor_bp.route('/api/queue/call-next', methods=['POST'])
@login_required
@doctor_required
def api_call_next_patient():
    """Doctor calls next waiting patient from reception queue."""
    doctor = current_user.doctor
    today_start = datetime.combine(date_cls.today(), datetime.min.time())
    entry = ReceptionQueue.query.filter(
        ReceptionQueue.doctor_id == doctor.id,
        ReceptionQueue.reception_status == 'Accepted',
        ReceptionQueue.doctor_status == 'Pending',
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.asc()).first()

    if not entry:
        return jsonify({'success': False, 'error': 'No waiting patients in queue'}), 404

    entry.doctor_status = 'Accepted'
    entry.status = 'In Consultation'
    entry.consultation_time = datetime.utcnow()
    entry.doctor_responded_at = datetime.utcnow()
    db.session.commit()

    patient = entry.patient
    return jsonify({
        'success': True,
        'queue_entry_id': entry.id,
        'patient': {
            'id': patient.id if patient else None,
            'name': f"{patient.first_name} {patient.last_name}" if patient else 'Unknown',
            'token': entry.token_number
        }
    })


@doctor_bp.route('/api/followup/schedule', methods=['POST'])
@login_required
@doctor_required
def api_schedule_followup():
    """Schedule follow-up and send notification."""
    data = request.get_json(silent=True) or {}
    doctor = current_user.doctor
    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    if not _doctor_has_access(doctor, patient.id):
        return jsonify({'success': False, 'error': 'Unauthorized patient access'}), 403

    date_str = (data.get('date') or '').strip()
    time_str = (data.get('time') or '10:00').strip()
    notes = (data.get('notes') or 'Follow-up visit').strip()
    reason = (data.get('reason') or 'Follow-up consultation').strip()

    if not date_str:
        return jsonify({'success': False, 'error': 'date is required'}), 400

    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date/time format'}), 400

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=dt,
        reason=reason,
        status='pending',
        notes=notes
    )
    db.session.add(appt)
    db.session.commit()

    try:
        NotificationService.send_email(
            patient.user.email,
            "Follow-up Reminder",
            (
                f"Dear {patient.first_name},\n\n"
                f"Your follow-up appointment with Dr. {doctor.first_name} {doctor.last_name} is scheduled for "
                f"{dt.strftime('%Y-%m-%d %I:%M %p')}.\n\n"
                f"Notes: {notes}\n\nRegards,\nHospital Team"
            )
        )
        if patient.phone:
            NotificationService.send_sms(
                patient.phone,
                f"Reminder: Follow-up on {dt.strftime('%Y-%m-%d %I:%M %p')} with Dr. {doctor.last_name}."
            )
    except Exception:
        current_app.logger.exception("Follow-up reminder notification failed")

    return jsonify({
        'success': True,
        'message': 'Follow-up scheduled',
        'appointment_id': appt.id
    })


@doctor_bp.route('/api/schedule', methods=['GET', 'POST'])
@login_required
@doctor_required
def api_doctor_schedule():
    """Doctor schedule management: working hours, leave blocks, and events."""
    doctor = current_user.doctor

    if request.method == 'GET':
        now = datetime.utcnow()
        upcoming = DoctorEvent.query.filter(
            DoctorEvent.doctor_id == doctor.id,
            DoctorEvent.end_time >= now
        ).order_by(DoctorEvent.start_time.asc()).limit(100).all()
        return jsonify({
            'success': True,
            'availability_hours': doctor.availability_hours or '',
            'events': [{
                'id': e.id,
                'title': e.title,
                'event_type': e.event_type or '',
                'start_time': e.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': e.end_time.strftime('%Y-%m-%d %H:%M')
            } for e in upcoming]
        })

    data = request.get_json(silent=True) or {}
    action = (data.get('action') or '').strip()
    if action == 'update_hours':
        doctor.availability_hours = (data.get('availability_hours') or '').strip()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Working hours updated'})

    if action == 'add_event':
        title = (data.get('title') or '').strip()
        start_time = (data.get('start_time') or '').strip()
        end_time = (data.get('end_time') or '').strip()
        event_type = (data.get('event_type') or 'custom').strip()
        if not title or not start_time or not end_time:
            return jsonify({'success': False, 'error': 'title, start_time, end_time are required'}), 400
        try:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid datetime format. Use YYYY-MM-DD HH:MM'}), 400
        if end_dt <= start_dt:
            return jsonify({'success': False, 'error': 'end_time must be after start_time'}), 400
        event = DoctorEvent(
            doctor_id=doctor.id,
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            event_type=event_type
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Schedule event added', 'event_id': event.id})

    return jsonify({'success': False, 'error': 'Unsupported action'}), 400
