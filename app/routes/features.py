from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.models import db, Medicine, BloodInventory, Bed, DoctorEvent, NurseTask, Staff, PatientCheckIn, Patient, Doctor
import warnings
warnings.filterwarnings('ignore')

features_bp = Blueprint('features', __name__, url_prefix='/features')

# ============================================================================
# STEP 8: NEW CORRECT CHATBOT - INTEGRATED WITH FLASK
# ============================================================================

from app.ml_models.strict_medical_chatbot import StrictMedicalChatbot
from app.services.ai_service import LocalAIService

chatbot_instance = None

def get_chatbot_instance():
    """Get or initialize the strict medical chatbot"""
    global chatbot_instance
    
    if chatbot_instance is None:
        try:
            chatbot_instance = StrictMedicalChatbot()
            print("✅ Strict Medical Chatbot initialized for Flask")
        except Exception as e:
            print(f"❌ Error initializing chatbot: {e}")
            return None
    
    return chatbot_instance



@features_bp.route('/api/ai-chat', methods=['POST'])
@login_required
def ai_chat():
    """
    API Endpoint for Local AI Chatbot (Ollama + BioMistral)
    """
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        response = LocalAIService.get_ai_response(message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'response': "Error: Local AI service is offline."}), 500

@features_bp.route('/ai-assistant')
@login_required
def ai_assistant():
    """Page for the Local AI Medical Assistant"""
    return render_template('features/ai_assistant.html')

from app.models.models import db, Medicine, BloodInventory, Bed

@features_bp.route('/operations')
@login_required
def operations():
    """Operations Center - Bed & Ambulance Tracking"""
    from app.models.models import Bed, Ambulance, Patient
    
    beds = Bed.query.all()
    # Seed beds if none exist
    if not beds:
        seed_beds()
        beds = Bed.query.all()
        
    ambulances = Ambulance.query.all()
    # Seed ambulances if none exist
    if not ambulances:
        seed_ambulances()
        ambulances = Ambulance.query.all()

    bed_data = []
    for bed in beds:
        patient_name = 'Vacant'
        if bed.is_occupied and bed.patient_id:
            patient = Patient.query.get(bed.patient_id)
            if patient:
                patient_name = f"{patient.first_name} {patient.last_name}"

        bed_data.append({
            'id': bed.id,
            'number': bed.bed_number,
            'ward': bed.ward_type,
            'status': bed.status,
            'patient': patient_name
        })

    return render_template('features/operations.html', 
                         beds=bed_data, 
                         ambulances=ambulances)

def seed_beds():
    """Seed initial hospital beds"""
    from app.models.models import Bed
    wards = [
        ('ICU', 5),
        ('General Ward', 10),
        ('Emergency', 5),
        ('Pediatrics', 5)
    ]
    for ward_name, count in wards:
        for i in range(1, count + 1):
            bed_num = f"{ward_name[0]}{i:02d}"
            # Check if bed already exists by number and type
            if not Bed.query.filter_by(bed_number=bed_num, ward_type=ward_name).first():
                bed = Bed(ward_type=ward_name, bed_number=bed_num, is_occupied=False)
                db.session.add(bed)
    db.session.commit()

def seed_ambulances():
    """Seed initial ambulances"""
    from app.models.models import Ambulance
    initial_ambulances = [
        ('AMB-001', 'Advanced Life Support', 'Available', 'Hospital Base', 'John Doe', '555-0101'),
        ('AMB-002', 'Basic Life Support', 'On Mission', 'Downtown Medical', 'Jane Smith', '555-0102'),
        ('AMB-003', 'Basic Life Support', 'Available', 'Hospital Base', 'Mike Ross', '555-0103'),
        ('AMB-004', 'Advanced Life Support', 'Maintenance', 'Service Center', 'Harvey Specter', '555-0104')
    ]
    for num, vtype, status, loc, driver, phone in initial_ambulances:
        if not Ambulance.query.filter_by(vehicle_number=num).first():
            amb = Ambulance(
                vehicle_number=num,
                vehicle_type=vtype,
                status=status,
                current_location=loc,
                driver_name=driver,
                driver_phone=phone
            )
            db.session.add(amb)
    db.session.commit()

@features_bp.route('/pharmacy')
@login_required
def pharmacy():
    """Pharmacy & Inventory Management"""
    search_query = request.args.get('search', '').strip()
    
    # Base query
    query = Medicine.query
    
    if search_query:
        query = query.filter(Medicine.name.ilike(f'%{search_query}%'))
        
    inventory = query.all()
    
    # Calculate Stats (using full inventory for stats context, or just hardcode if easier, 
    # but let's do real stats on full table to be proper)
    all_inventory = Medicine.query.all()
    
    low_stock = sum(1 for m in all_inventory if m.stock < 50)
    total_value = sum((m.stock * (m.unit_price or 0)) for m in all_inventory)
    
    import datetime
    current_year = str(datetime.datetime.now().year)
    expiring_soon = sum(1 for m in all_inventory if m.expiry_date and m.expiry_date.startswith(current_year))
    
    stats = {
        'low_stock': low_stock,
        'total_value': f"${total_value:,.2f}",
        'expiring_soon': expiring_soon,
        'daily_sales': 156 
    }
    
    return render_template('features/pharmacy.html', inventory=inventory, stats=stats, search_query=search_query)

@features_bp.route('/api/pharmacy/restock', methods=['POST'])
@login_required
def restock_pharmacy():
    """API to Restock Medicine"""
    data = request.get_json()
    med_id = data.get('id')
    amount = data.get('amount')
    
    if not med_id or not amount:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    medicine = Medicine.query.get(med_id)
    if not medicine:
        return jsonify({'success': False, 'error': 'Medicine not found'})
        
    medicine.stock += amount
    db.session.commit()
    
    return jsonify({'success': True})

@features_bp.route('/api/pharmacy/add', methods=['POST'])
@login_required
def add_medicine():
    """API to Add New Medicine"""
    data = request.get_json()
    
    try:
        new_med = Medicine(
            name=data['name'],
            stock=int(data['stock']),
            unit_price=float(data['unit_price']),
            expiry_date=data['expiry_date'],
            batch_number=data.get('batch_number', 'N/A'),
            manufacturer=data.get('manufacturer', 'N/A')
        )
        db.session.add(new_med)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@features_bp.route('/features/pharmacy/export')
@login_required
def export_pharmacy_report():
    """Export Inventory as CSV"""
    import csv
    import io
    from flask import Response
    
    inventory = Medicine.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Name', 'Stock', 'Unit Price', 'Expiry Date', 'Batch', 'Manufacturer', 'Status'])
    
    # Rows
    for m in inventory:
        writer.writerow([m.id, m.name, m.stock, m.unit_price, m.expiry_date, m.batch_number, m.manufacturer, m.status])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=pharmacy_inventory.csv"}
    )

@features_bp.route('/education')
@login_required
def education():
    """Personalized Health Education"""
    videos = [
        # Diabetes Management (Verified)
        {'id': 'wZAjVQWbMlE', 'title': 'What is Diabetes? (CDC Verified)', 'category': 'Diabetes', 'duration': '02:30'},
        {'id': 'X9ivR4y03DE', 'title': 'Understanding Diabetes', 'category': 'Diabetes', 'duration': '05:15'},
        {'id': 'JAjJoFj5-DA', 'title': 'Reverse Type 2 Diabetes', 'category': 'Diabetes', 'duration': '15:30'},
        {'id': 'sV2dtA74Yx0', 'title': 'What is Type 2 Diabetes?', 'category': 'Diabetes', 'duration': '03:45'},

        # Hypertension & Heart (Verified)
        {'id': 'diG519dFVNs', 'title': 'High Blood Pressure Explained', 'category': 'Hypertension', 'duration': '02:50'},
        {'id': 'H04d3rJCLCE', 'title': 'How the Heart Works (Mayo Clinic)', 'category': 'Heart Health', 'duration': '03:10'},
        {'id': '50lFZHOyPzI', 'title': 'How the Heart Pumps Blood', 'category': 'Heart Health', 'duration': '04:45'},
        
        # Mental Health & Wellness (TED-Ed Verified)
        {'id': 'WuyPuH9ojCE', 'title': 'How Stress Affects Your Brain', 'category': 'Mental Health', 'duration': '04:15'},
        {'id': 'gedoSfZvBgE', 'title': 'Benefits of Good Sleep', 'category': 'Wellness', 'duration': '05:10'},
        {'id': 'z-IR48Mb3W0', 'title': 'What is Depression?', 'category': 'Mental Health', 'duration': '04:50'},
        {'id': 'PSRJfaAYkW4', 'title': 'How Your Immune System Works', 'category': 'Immunity', 'duration': '05:20'},
        {'id': 'OyK0oE5rwFY', 'title': 'Benefits of Good Posture', 'category': 'Wellness', 'duration': '04:30'},
        {'id': 'lEXBxijQREo', 'title': 'Sugar and the Brain', 'category': 'Nutrition', 'duration': '04:55'},
        {'id': 'wUEl8KrMz14', 'title': 'Why Sitting is Bad', 'category': 'Wellness', 'duration': '05:05'}
    ]
    return render_template('patient/health_videos.html', videos=videos)

@features_bp.route('/digital-checkin', methods=['GET', 'POST'])
@login_required
def digital_checkin():
    """Digital Check-in & Queue Management - Express Check-in System"""
    # Fetch all available doctors for the selection dropdown
    doctors = Doctor.query.all()

    if request.method == 'POST':
        # Get form data
        check_in_reason = request.form.get('reason', 'General check-up')
        visit_type = request.form.get('visit_type', 'follow-up')
        symptoms = request.form.get('symptoms', '')
        severity = request.form.get('severity', 'normal')
        # Vital signs
        temperature = request.form.get('temperature')
        blood_pressure = request.form.get('blood_pressure')
        heart_rate = request.form.get('heart_rate')

        # Get patient details
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        
        if patient:
            # Determine appropriate doctor
            doctor_id = None
            selected_doctor_id = request.form.get('doctor_id')
            if selected_doctor_id:
                doctor_id = int(selected_doctor_id)
            else:
                # Fallback: Get first available doctor if none selected (though form should require it)
                first_doctor = Doctor.query.first()
                doctor_id = first_doctor.id if first_doctor else None

            if not doctor_id:
                flash('❌ Error: No doctor selected or available.', 'danger')
                return redirect(url_for('features.digital_checkin'))

            # Create check-in record
            checkin = PatientCheckIn(
                patient_id=patient.id,
                doctor_id=doctor_id,
                check_in_reason=check_in_reason,
                visit_type=visit_type,
                symptoms=symptoms,
                severity=severity,
                temperature=float(temperature) if temperature else None,
                blood_pressure=blood_pressure if blood_pressure else None,
                heart_rate=int(heart_rate) if heart_rate else None,
                status='pending',
                priority='normal' if severity == 'normal' else 'urgent'
            )
            
            db.session.add(checkin)
            db.session.commit()
            
            # Fetch content for success message
            assigned_doctor = Doctor.query.get(doctor_id)
            doctor_name = f"Dr. {assigned_doctor.first_name} {assigned_doctor.last_name}" if assigned_doctor else "the doctor"

            flash(f'✅ Express Check-in Successful! Your request has been sent to {doctor_name}.', 'success')
            return redirect(url_for('patient.dashboard'))
        else:
            flash('❌ Error: Patient profile not found.', 'danger')
            return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/check_in.html', doctors=doctors)

@features_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Patient Feedback System"""
    if request.method == 'POST':
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('patient.dashboard'))
    return render_template('features/feedback.html')

@features_bp.route('/emergency-sos')
@login_required
def emergency_sos():
    """Emergency SOS Handler - Now Hospital Finder"""
    import json
    import os
    
    search_query = request.args.get('search', '').strip().lower()
    
    # Construct path to data file
    # features.py is in app/routes/, so we go up one level to app/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'hospitals.json')
    
    all_districts = []
    try:
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                all_districts = json.load(f)
    except Exception as e:
        print(f"Error loading hospital data: {e}")
    
    results = []
    
    if search_query:
        # Flat list of matching hospitals
        for district_data in all_districts:
            district_name = district_data.get('district', '')
            
            for hospital in district_data.get('hospitals', []):
                h_name = hospital.get('hospital_name', '').lower()
                h_loc = hospital.get('location', '').lower()
                h_type = hospital.get('type', '').lower()
                d_name = district_name.lower()
                
                if (search_query in h_name or 
                    search_query in h_loc or 
                    search_query in h_type or 
                    search_query in d_name):
                    
                    hospital_entry = hospital.copy()
                    hospital_entry['district'] = district_name
                    results.append(hospital_entry)
    else:
        # Prepare data for "all hospitals" view if needed, 
        # or just pass the structured data to iterate by district
        results = all_districts

    return render_template('features/emergency.html', 
                         results=results, 
                         search_query=search_query,
                         is_search=bool(search_query))

@features_bp.route('/schedule')
@login_required
def schedule():
    """Doctor Smart Schedule & Calendar"""
    # Fetch events from DB
    db_events = DoctorEvent.query.all()
    events = []
    for event in db_events:
        events.append({
            'title': event.title,
            'start': event.start_time.strftime('%H:%M'),
            'end': event.end_time.strftime('%H:%M'),
            'type': event.event_type
        })
    return render_template('features/schedule.html', events=events)

@features_bp.route('/nurse-tasks')
@login_required
def nurse_tasks():
    """Nurse Task Management System"""
    tasks_db = NurseTask.query.all()
    # Serialize for template
    tasks = []
    for t in tasks_db:
        tasks.append({
            'id': t.id,
            'patient': t.patient_name,
            'bed': t.bed_number,
            'task': t.task_description,
            'time': t.due_time,
            'status': t.status,
            'priority': t.priority
        })
    return render_template('features/nurse_tasks.html', tasks=tasks)

@features_bp.route('/api/nurse/complete-task', methods=['POST'])
@login_required
def complete_nurse_task():
    """API to Complete Nurse Task"""
    data = request.get_json()
    task_id = data.get('id')
    
    if not task_id:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    task = NurseTask.query.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'})
        
    task.status = 'Completed'
    db.session.commit()
    
    return jsonify({'success': True})

@features_bp.route('/blood-bank')
@login_required
def blood_bank():
    """Blood Bank Management"""
    inventory_items = BloodInventory.query.all()
    stock = {}
    for item in inventory_items:
        stock[item.blood_group] = {
            'units': item.units,
            'status': item.status
        }
    return render_template('features/blood_bank.html', stock=stock)

@features_bp.route('/blood-bank/donate', methods=['POST'])
@login_required
def donate_blood():
    """Register a new blood donation"""
    blood_group = request.form.get('blood_group')
    units = int(request.form.get('units', 1))
    donor_name = request.form.get('donor_name')
    
    inventory = BloodInventory.query.filter_by(blood_group=blood_group).first()
    if inventory:
        inventory.units += units
        inventory.last_updated = datetime.now()
    else:
        new_inv = BloodInventory(blood_group=blood_group, units=units)
        db.session.add(new_inv)
        
    db.session.commit()
    flash('✅ Donation registered successfully!', 'success')
    return redirect(url_for('features.blood_bank'))


@features_bp.route('/hr-payroll')
@login_required
def hr_payroll():
    """HR & Staff Payroll Dashboard"""
    total_staff = Staff.query.count()
    present_today = Staff.query.filter_by(status='Present').count()
    on_leave = Staff.query.filter_by(status='On Leave').count()
    
    stats = {
        'total_staff': total_staff,
        'present_today': present_today,
        'on_leave': on_leave,
        'payroll_due': '5 Days'
    }
    return render_template('features/hr_dashboard.html', stats=stats)


# ============================================================================
# DOCTOR CHECK-IN MANAGEMENT ROUTES
# ============================================================================

@features_bp.route('/doctor/pending-checkins')
@login_required
def doctor_pending_checkins():
    """Doctor view all pending patient check-ins"""
    from app.routes.auth import doctor_required
    
    # Get current doctor
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor:
        flash('❌ Access denied. Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all pending check-ins for this doctor
    pending_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id, 
        status='pending'
    ).order_by(PatientCheckIn.created_at.desc()).all()
    
    # Get accepted check-ins
    accepted_checkins = PatientCheckIn.query.filter_by(
        doctor_id=doctor.id,
        status='accepted'
    ).order_by(PatientCheckIn.acceptance_time.desc()).limit(10).all()
    
    # Statistics
    stats = {
        'pending_count': len(pending_checkins),
        'accepted_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='accepted').count(),
        'rejected_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='rejected').count(),
        'completed_count': PatientCheckIn.query.filter_by(doctor_id=doctor.id, status='completed').count()
    }
    
    return render_template('doctor/pending_checkins.html',
                         pending_checkins=pending_checkins,
                         accepted_checkins=accepted_checkins,
                         stats=stats)


@features_bp.route('/doctor/checkin/<int:checkin_id>/accept', methods=['POST'])
@login_required
def accept_checkin(checkin_id):
    """Doctor accepts a patient check-in"""
    from datetime import datetime
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor or checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get doctor notes
    notes = request.form.get('notes', '') or request.json.get('notes', '')
    
    # Update check-in
    checkin.status = 'accepted'
    checkin.acceptance_time = datetime.utcnow()
    checkin.doctor_notes = notes
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ Check-in from {checkin.patient.user.username} accepted!',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>/reject', methods=['POST'])
@login_required
def reject_checkin(checkin_id):
    """Doctor rejects a patient check-in"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor or checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get rejection reason
    reason = request.form.get('reason', '') or request.json.get('reason', '')
    
    # Update check-in
    checkin.status = 'rejected'
    checkin.doctor_notes = f'Rejected: {reason}'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'❌ Check-in from {checkin.patient.user.username} rejected.',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>/complete', methods=['POST'])
@login_required
def complete_checkin(checkin_id):
    """Doctor marks a check-in as completed"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor or checkin.doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get completion notes
    notes = request.form.get('notes', '') or request.json.get('notes', '')
    
    # Update check-in
    checkin.status = 'completed'
    if notes:
        checkin.doctor_notes = notes
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'✅ Check-in marked as completed!',
        'checkin_id': checkin.id
    })


@features_bp.route('/doctor/checkin/<int:checkin_id>', methods=['GET'])
@login_required
def view_checkin_detail(checkin_id):
    """View detailed check-in information"""
    
    checkin = PatientCheckIn.query.get(checkin_id)
    
    if not checkin:
        return jsonify({'error': 'Check-in not found'}), 404
    
    doctor = current_user.doctor if hasattr(current_user, 'doctor') else None
    
    if not doctor or checkin.doctor_id != doctor.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Prepare check-in data
    checkin_data = {
        'id': checkin.id,
        'patient_name': checkin.patient.user.full_name if checkin.patient.user else 'Unknown',
        'patient_id': checkin.patient_id,
        'reason': checkin.check_in_reason,
        'visit_type': checkin.visit_type,
        'symptoms': checkin.symptoms,
        'severity': checkin.severity,
        'status': checkin.status,
        'priority': checkin.priority,
        'temperature': checkin.temperature,
        'blood_pressure': checkin.blood_pressure,
        'heart_rate': checkin.heart_rate,
        'doctor_notes': checkin.doctor_notes,
        'created_at': checkin.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'acceptance_time': checkin.acceptance_time.strftime('%Y-%m-%d %H:%M:%S') if checkin.acceptance_time else None
    }
    
    return jsonify(checkin_data)

@features_bp.route('/api/operations/bed/update', methods=['POST'])
@login_required
def update_bed_status():
    """API to Update Bed Status"""
    data = request.get_json()
    bed_id = data.get('bed_id')
    status = data.get('status') # 'Occupied' or 'Vacant'
    patient_name = data.get('patient_name')
    
    if not bed_id or not status:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'error': 'Bed not found'})
        
    bed.is_occupied = (status == 'Occupied')
    
    # In a real app, we would link to a patient ID. 
    # For this dashboard demo, we might just store the name in a temporary way 
    # or find a patient with that name.
    # Since Bed model links to patient_id, let's try to find the patient or create a dummy one if we really had to.
    # But strictly, the Bed model has `patient_id`. 
    # If the user enters a name, we can try to search for a patient.
    
    if status == 'Occupied' and patient_name:
        # Try to find patient by name
        parts = patient_name.split()
        if len(parts) >= 2:
            fname, lname = parts[0], parts[1]
            patient = Patient.query.filter_by(first_name=fname, last_name=lname).first()
            if patient:
                bed.patient_id = patient.id
    else:
        bed.patient_id = None
        
    db.session.commit()
    
    return jsonify({'success': True})

@features_bp.route('/api/operations/ambulance/dispatch', methods=['POST'])
@login_required
def dispatch_ambulance():
    """API to Dispatch Ambulance"""
    from app.models.models import Ambulance
    data = request.get_json()
    ambulance_id = data.get('ambulance_id')
    location = data.get('location')
    
    if not ambulance_id:
        return jsonify({'success': False, 'error': 'Invalid data'})
        
    ambulance = Ambulance.query.get(ambulance_id)
    if not ambulance:
        return jsonify({'success': False, 'error': 'Ambulance not found'})
        
    ambulance.status = 'On Mission'
    if location:
        ambulance.current_location = location
        
    db.session.commit()
    return jsonify({'success': True})
