from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.models import (db, Doctor, Patient, HealthData, Appointment, 
                               Prescription, Message, Billing, LabReport, PatientCheckIn)
from werkzeug.utils import secure_filename
import os
from app.routes.auth import doctor_required
from datetime import datetime

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    """Doctor dashboard"""
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
    
    # Get critical alerts (high-risk patients)
    critical_patients = []
    recent_health_data = db.session.query(HealthData).join(
        Patient, HealthData.patient_id == Patient.id).filter(
        Patient.id.in_([ap.patient_id for ap in doctor.appointments])
    ).order_by(HealthData.recorded_at.desc()).limit(20)
    
    for health in recent_health_data:
        if health.diabetes_risk > 80 or health.heart_disease_risk > 80 or health.hypertension_risk > 80:
            critical_patients.append(health)
    
    # Get pending patient check-ins (NEW)
    pending_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id, 
        status='pending'
    ).order_by(PatientCheckIn.created_at.desc()).limit(10).all()
    
    pending_checkins_count = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id,
        status='pending'
    ).count()
    
    return render_template('doctor/dashboard.html',
                         doctor=doctor,
                         total_patients=total_patients,
                         today_appointments=today_appointments,
                         pending_appointments=pending_appointments,
                         unread_messages=unread_messages,
                         critical_patients=critical_patients[:5],
                         pending_checkins=pending_checkins,
                         pending_checkins_count=pending_checkins_count)

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
    """View list of patients"""
    doctor = current_user.doctor
    
    # Get unique patients from appointments
    appointment_patient_ids = db.session.query(Appointment.patient_id.distinct()).filter_by(
        doctor_id=doctor.id).all()
    patient_ids = [ap[0] for ap in appointment_patient_ids]
    
    patients = Patient.query.filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
    
    return render_template('doctor/patient_list.html', patients=patients)

@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def view_patient(patient_id):
    """View patient record"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check if doctor has appointments with this patient
    has_access = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    
    if not has_access:
        flash('You do not have access to this patient record', 'danger')
        return redirect(url_for('doctor.patient_list'))
    
    # Get patient health data
    health_data = HealthData.query.filter_by(patient_id=patient_id).order_by(
        HealthData.recorded_at.desc()).all()
    
    # Get appointments
    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()).all()
    
    # Get prescriptions
    prescriptions = Prescription.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).order_by(
        Prescription.prescribed_at.desc()).all()
    
    return render_template('doctor/view_patient.html',
                         patient=patient,
                         health_data=health_data,
                         appointments=appointments,
                         prescriptions=prescriptions)

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
    has_access = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    
    if not has_access:
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
    has_access = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
    
    if not has_access:
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
    data = request.get_json()
    
    message = Message(
        patient_id=patient_id,
        doctor_id=doctor.id,
        sender_type='doctor',
        message_text=data.get('message')
    )
    
    db.session.add(message)
    db.session.commit()
    
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
    has_access = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
        
    if not has_access:
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


@doctor_bp.route('/lab-report/upload/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def upload_lab_report(patient_id):
    """Upload a lab report for a patient"""
    doctor = current_user.doctor
    patient = Patient.query.get_or_404(patient_id)
    
    # Check access
    has_access = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id).first() is not None
        
    if not has_access:
        flash('You do not have access to this patient.', 'danger')
        return redirect(url_for('doctor.patient_list'))

    if request.method == 'POST':
        test_name = request.form.get('test_name')
        result_value = request.form.get('result_value')
        unit = request.form.get('unit')
        reference_range = request.form.get('reference_range')
        notes = request.form.get('notes')
        status = request.form.get('status')
        
        # File Upload Handling
        file_path = None
        if 'report_file' in request.files:
            file = request.files['report_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Ensure directory exists
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'reports')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                save_path = os.path.join(upload_dir, f"{timestamp}_{filename}")
                file.save(save_path)
                
                # Store relative path for serving
                file_path = f"uploads/reports/{timestamp}_{filename}"

        report = LabReport(
            patient_id=patient.id,
            doctor_id=doctor.id,
            test_name=test_name,
            result_value=result_value,
            unit=unit,
            reference_range=reference_range,
            notes=notes,
            status=status,
            report_file=file_path,
            conducted_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Notify Patient
        try:
            NotificationService.send_email(
                patient.user.email,
                f"Lab Report Available - {test_name}",
                f"Dear {patient.first_name},\n\nYour lab report for {test_name} is now available in your portal.\n\nResult: {result_value} {unit}\n\nRegards,\nHMS"
            )
        except Exception:
            pass
        
        flash('Lab report uploaded successfully!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=patient.id))
        
    return render_template('doctor/upload_lab_report.html', patient=patient)

