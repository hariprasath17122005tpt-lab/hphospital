"""Telemedicine / Video Consultation Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, TelemedicineSession, Patient, Doctor, Appointment, UserRole)
from datetime import datetime, timedelta
from sqlalchemy import func
import uuid

telemedicine_bp = Blueprint('telemedicine', __name__, url_prefix='/telemedicine')


@telemedicine_bp.route('/')
@telemedicine_bp.route('/dashboard')
@login_required
def dashboard():
    role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()

    if role_val == 'PATIENT':
        patient = current_user.patient
        if not patient:
            flash('Patient profile not found.', 'error')
            return redirect(url_for('patient.dashboard'))
        sessions = TelemedicineSession.query.filter_by(patient_id=patient.id).order_by(
            TelemedicineSession.scheduled_time.desc()
        ).all()
        upcoming = [s for s in sessions if s.status in ('Scheduled', 'Waiting')]
    elif role_val == 'DOCTOR':
        doctor = current_user.doctor
        if not doctor:
            flash('Doctor profile not found.', 'error')
            return redirect(url_for('doctor.portal'))
        sessions = TelemedicineSession.query.filter_by(doctor_id=doctor.id).order_by(
            TelemedicineSession.scheduled_time.desc()
        ).all()
        upcoming = [s for s in sessions if s.status in ('Scheduled', 'Waiting')]
    else:
        sessions = TelemedicineSession.query.order_by(
            TelemedicineSession.scheduled_time.desc()
        ).limit(50).all()
        upcoming = [s for s in sessions if s.status in ('Scheduled', 'Waiting')]

    stats = {
        'total_sessions': len(sessions),
        'upcoming': len(upcoming),
        'completed': len([s for s in sessions if s.status == 'Completed']),
        'in_progress': len([s for s in sessions if s.status == 'In Progress']),
    }

    return render_template('telemedicine/dashboard.html',
                           sessions=sessions, upcoming=upcoming,
                           stats=stats, role=role_val)


@telemedicine_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        try:
            room_id = f"tele-{uuid.uuid4().hex[:8]}"
            session_obj = TelemedicineSession(
                patient_id=request.form.get('patient_id', type=int),
                doctor_id=request.form.get('doctor_id', type=int),
                session_type=request.form.get('session_type', 'Video'),
                room_id=room_id,
                meeting_link=f"/telemedicine/room/{room_id}",
                scheduled_time=datetime.strptime(request.form.get('scheduled_time'), '%Y-%m-%dT%H:%M'),
                status='Scheduled'
            )
            db.session.add(session_obj)
            db.session.commit()
            flash('Teleconsultation scheduled!', 'success')
            return redirect(url_for('telemedicine.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    doctors = Doctor.query.filter_by(is_deleted=False).all()
    patients = Patient.query.order_by(Patient.name).limit(200).all()
    return render_template('telemedicine/schedule.html', doctors=doctors, patients=patients)


@telemedicine_bp.route('/room/<room_id>')
@login_required
def consultation_room(room_id):
    session_obj = TelemedicineSession.query.filter_by(room_id=room_id).first_or_404()
    return render_template('telemedicine/room.html', session=session_obj)


@telemedicine_bp.route('/api/update-status', methods=['POST'])
@login_required
def update_status():
    data = request.get_json(silent=True) or {}
    session_obj = TelemedicineSession.query.get(data.get('session_id'))
    if not session_obj:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    new_status = data.get('status')
    session_obj.status = new_status
    if new_status == 'In Progress':
        session_obj.started_at = datetime.utcnow()
    elif new_status == 'Completed':
        session_obj.ended_at = datetime.utcnow()
        if session_obj.started_at:
            session_obj.duration_minutes = int((datetime.utcnow() - session_obj.started_at).total_seconds() / 60)
        session_obj.consultation_notes = data.get('notes', '')

    db.session.commit()
    return jsonify({'success': True})


@telemedicine_bp.route('/api/rate', methods=['POST'])
@login_required
def rate_session():
    data = request.get_json(silent=True) or {}
    session_obj = TelemedicineSession.query.get(data.get('session_id'))
    if not session_obj:
        return jsonify({'success': False}), 404

    session_obj.patient_rating = data.get('rating', 5)
    session_obj.patient_feedback = data.get('feedback', '')
    db.session.commit()
    return jsonify({'success': True})
