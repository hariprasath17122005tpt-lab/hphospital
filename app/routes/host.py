
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.models.models import (db, User, UserRole, Doctor, Nurse, Patient, AuditLog,
                                SystemSettings, Hospital, FrontpageDoctor,
                                Billing, Bed, Appointment, IPAdmission)
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func

host_bp = Blueprint('host', __name__, url_prefix='/host')

def host_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.HOST:
            flash('Unauthorized access. Host privileges required.', 'danger')
            return redirect(url_for('auth.patient_login'))
        return f(*args, **kwargs)
    return decorated_function

def log_audit(action, target_id=None, details=None):
    """Helper to log actions"""
    try:
        log = AuditLog(
            actor_id=current_user.id,
            actor_name=current_user.username,
            action=action,
            target_id=str(target_id) if target_id else None,
            details=str(details) if details else None,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit Log Error: {e}")

@host_bp.route('/dashboard')
@login_required
@host_required
def dashboard():
    """Main Host Dashboard"""
    # Quick Stats - Doctors
    total_doctors = Doctor.query.filter_by(is_deleted=False).count()
    pending_doctors = Doctor.query.filter_by(verified=False, is_deleted=False).count()

    # Quick Stats - Patients
    total_patients = Patient.query.count()
    suspicious_activities = 0 # Placeholder for logic

    settings = SystemSettings.query.first()

    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    # ── Financial Stats ──
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    # Revenue today (sum of grand_total for Paid bills created today)
    revenue_today = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status == 'Paid',
        func.date(Billing.created_at) == today
    ).scalar() or 0

    # Revenue this month
    revenue_month = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status == 'Paid',
        func.date(Billing.created_at) >= month_start
    ).scalar() or 0

    # Outstanding bills (Unpaid / Partial)
    outstanding_bills = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status.in_(['Unpaid', 'Partial'])
    ).scalar() or 0

    # ── Staff Counts ──
    total_nurses = Nurse.query.filter_by(is_deleted=False).count()
    staff_by_role = {}
    role_counts = db.session.query(User.role, func.count(User.id)).filter(
        User.is_active == True
    ).group_by(User.role).all()
    for role_enum, cnt in role_counts:
        staff_by_role[role_enum.value] = cnt

    # ── Bed Occupancy ──
    beds_total = Bed.query.count()
    beds_occupied = Bed.query.filter_by(is_occupied=True).count()
    bed_occupancy_pct = round((beds_occupied / beds_total * 100), 1) if beds_total > 0 else 0

    # ── IP & Appointments ──
    active_ip = IPAdmission.query.filter_by(admission_status='Admitted').count()
    appointments_today = Appointment.query.filter(
        func.date(Appointment.appointment_date) == today
    ).count()

    # ── Department-wise Patient Count (from Doctor specialization -> Appointments) ──
    dept_patient_counts = db.session.query(
        Doctor.specialization,
        func.count(func.distinct(Appointment.patient_id))
    ).join(Appointment, Appointment.doctor_id == Doctor.id).filter(
        Doctor.is_deleted == False
    ).group_by(Doctor.specialization).all()
    department_stats = {spec: cnt for spec, cnt in dept_patient_counts if spec}

    return render_template('host/dashboard.html',
                         total_doctors=total_doctors,
                         pending_doctors=pending_doctors,
                         total_patients=total_patients,
                         total_nurses=total_nurses,
                         settings=settings,
                         recent_logs=recent_logs,
                         revenue_today=revenue_today,
                         revenue_month=revenue_month,
                         outstanding_bills=outstanding_bills,
                         staff_by_role=staff_by_role,
                         beds_total=beds_total,
                         beds_occupied=beds_occupied,
                         bed_occupancy_pct=bed_occupancy_pct,
                         active_ip=active_ip,
                         appointments_today=appointments_today,
                         department_stats=department_stats)

@host_bp.route('/departments')
@login_required
@host_required
def departments():
    """Department Management — overview of all hospital departments."""
    DEPARTMENTS = [
        {'name': 'General Medicine', 'icon': 'fa-stethoscope', 'color': '#3b82f6'},
        {'name': 'Pediatrics', 'icon': 'fa-baby', 'color': '#8b5cf6'},
        {'name': 'Cardiology', 'icon': 'fa-heartbeat', 'color': '#ef4444'},
        {'name': 'Orthopedics', 'icon': 'fa-bone', 'color': '#f59e0b'},
        {'name': 'ENT', 'icon': 'fa-ear-listen', 'color': '#10b981'},
        {'name': 'Dermatology', 'icon': 'fa-hand-dots', 'color': '#ec4899'},
        {'name': 'Ophthalmology', 'icon': 'fa-eye', 'color': '#06b6d4'},
        {'name': 'Gynecology', 'icon': 'fa-venus', 'color': '#d946ef'},
        {'name': 'Emergency', 'icon': 'fa-truck-medical', 'color': '#dc2626'},
        {'name': 'ICU', 'icon': 'fa-bed-pulse', 'color': '#b91c1c'},
        {'name': 'Radiology', 'icon': 'fa-x-ray', 'color': '#6366f1'},
        {'name': 'Pathology', 'icon': 'fa-microscope', 'color': '#0d9488'},
        {'name': 'Pharmacy', 'icon': 'fa-pills', 'color': '#16a34a'},
    ]

    # Doctor count per specialization
    doc_counts = db.session.query(
        Doctor.specialization,
        func.count(Doctor.id)
    ).filter(Doctor.is_deleted == False, Doctor.verified == True).group_by(
        Doctor.specialization
    ).all()
    doc_count_map = {spec.strip(): cnt for spec, cnt in doc_counts if spec}

    # Patient count per department (through appointments with doctors of that specialty)
    patient_counts = db.session.query(
        Doctor.specialization,
        func.count(func.distinct(Appointment.patient_id))
    ).join(Appointment, Appointment.doctor_id == Doctor.id).filter(
        Doctor.is_deleted == False
    ).group_by(Doctor.specialization).all()
    patient_count_map = {spec.strip(): cnt for spec, cnt in patient_counts if spec}

    # IP admissions per department (through doctor specialization)
    ip_counts = db.session.query(
        Doctor.specialization,
        func.count(IPAdmission.id)
    ).join(IPAdmission, IPAdmission.doctor_id == Doctor.id).filter(
        Doctor.is_deleted == False,
        IPAdmission.admission_status == 'Admitted'
    ).group_by(Doctor.specialization).all()
    ip_count_map = {spec.strip(): cnt for spec, cnt in ip_counts if spec}

    dept_data = []
    for dept in DEPARTMENTS:
        name = dept['name']
        doctors = doc_count_map.get(name, 0)
        patients = patient_count_map.get(name, 0)
        ip_active = ip_count_map.get(name, 0)
        dept_data.append({
            'name': name,
            'icon': dept['icon'],
            'color': dept['color'],
            'doctor_count': doctors,
            'patient_count': patients,
            'ip_active': ip_active,
            'active': doctors > 0,
        })

    return render_template('host/departments.html', departments=dept_data)


@host_bp.route('/doctors')
@login_required
@host_required
def doctor_management():
    """List and Manage Doctors"""
    pending_docs = Doctor.query.filter_by(verified=False, is_suspended=False, is_deleted=False).all()
    active_docs = Doctor.query.filter_by(verified=True, is_suspended=False, is_deleted=False).all()
    suspended_docs = Doctor.query.filter_by(is_suspended=True, is_deleted=False).all()
    
    return render_template('host/doctors.html', 
                         pending_docs=pending_docs,
                         active_docs=active_docs,
                         suspended_docs=suspended_docs)

@host_bp.route('/doctor/<action>/<int:doctor_id>', methods=['POST'])
@login_required
@host_required
def doctor_action(action, doctor_id):
    """Approve, Reject, Suspend, Unsuspend, Delete Doctors"""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if action == 'approve':
        doctor.verified = True
        doctor.is_suspended = False
        flash(f'Dr. {doctor.last_name} has been APPROVED.', 'success')
        log_audit("APPROVE_DOCTOR", doctor_id, f"Approved {doctor.first_name}")
        
    elif action == 'reject':
        doctor.verified = False
        flash(f'Dr. {doctor.last_name} application rejected.', 'warning')
        log_audit("REJECT_DOCTOR", doctor_id, "Application Rejected")
        
    elif action == 'suspend':
        reason = request.form.get('reason', 'No reason provided')
        doctor.is_suspended = True
        # Ensure verified is true if they are suspended from active list, or handle pending suspension
        doctor.suspension_reason = reason
        flash(f'Dr. {doctor.last_name} has been SUSPENDED.', 'danger')
        log_audit("SUSPEND_DOCTOR", doctor_id, f"Reason: {reason}")
        
    elif action == 'unsuspend':
        doctor.is_suspended = False
        doctor.suspension_reason = None
        flash(f'Dr. {doctor.last_name} ban lifted.', 'success')
        log_audit("UNSUSPEND_DOCTOR", doctor_id, "Suspension lifted")
        
    elif action == 'delete':
        doctor.is_deleted = True
        # Also deactivate the user account
        if doctor.user:
            doctor.user.is_active = False
        
        flash(f'Dr. {doctor.last_name} account has been PERMANENTLY DELETED.', 'dark')
        log_audit("DELETE_DOCTOR", doctor_id, "Soft deleted doctor and deactivated user")
        
    db.session.commit()
    return redirect(url_for('host.doctor_management'))

@host_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@host_required
def settings():
    """System-wide Settings"""
    settings = SystemSettings.query.first()
    if not settings:
        settings = SystemSettings(emergency_mode=False, maintenance_mode=False)
        db.session.add(settings)
        db.session.commit()
        
    if request.method == 'POST':
        settings.emergency_mode = request.form.get('emergency_mode') == 'on'
        settings.maintenance_mode = request.form.get('maintenance_mode') == 'on'
        settings.disclaimer_text = request.form.get('disclaimer_text')
        wa = request.form.get('whatsapp_number', '').strip()
        if wa:
            settings.whatsapp_number = wa.replace('+', '').replace(' ', '').replace('-', '')
        
        db.session.commit()
        flash('System settings updated.', 'success')
        log_audit("UPDATE_SETTINGS", None, "Updated System Settings")
        return redirect(url_for('host.dashboard'))
        
    return render_template('host/settings.html', settings=settings)

@host_bp.route('/audit')
@login_required
@host_required
def audit_logs():
    """View full audit logs"""
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('host/audit.html', logs=logs)

@host_bp.route('/staff/create', methods=['GET', 'POST'])
@login_required
@host_required
def create_staff():
    """Create new staff accounts"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role_name = request.form.get('role')
        
        # Auto-generate dummy email for internal staff
        # Format: staff.username@hospital.internal
        email = f"staff.{username}@hospital.internal"

        # Validate role
        try:
            role = UserRole[role_name]
            if role not in [UserRole.LAB_STAFF, UserRole.DOCTOR, UserRole.ADMIN, UserRole.PHARMACIST, UserRole.RECEPTIONIST]:
                raise ValueError("Invalid role assignment")
        except:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('host.create_staff'))

        if User.query.filter(User.username==username).first():
            flash('User already exists.', 'danger')
            return redirect(url_for('host.create_staff'))
            
        # Create User
        user = User(
            username=username, 
            email=email, 
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.flush()
        
        # If Doctor, create empty doctor profile for them to fill?
        # For Lab/Pharmacy/Reception, UserRole is enough for login.
        if role == UserRole.DOCTOR:
            doctor = Doctor(user_id=user.id, first_name="New", last_name="Doctor", verified=True)
            db.session.add(doctor)
            
        db.session.commit()
        log_audit("CREATE_USER", user.id, f"Created {role_name} user: {username}")
        flash(f'User {username} created as {role_name}.', 'success')
        return redirect(url_for('host.dashboard'))
        
    return render_template('host/create_staff.html')


@host_bp.route('/nurse/create', methods=['GET', 'POST'])
@login_required
@host_required
def create_nurse():
    """Create new Nurse accounts with Nurse profile"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        registration_number = request.form.get('registration_number')
        specialization = request.form.get('specialization', 'General')
        phone = request.form.get('phone', '')
        
        # Auto-generate email
        email = f"nurse.{username}@hospital.internal"
        
        if User.query.filter(User.username==username).first():
            flash('User already exists.', 'danger')
            return redirect(url_for('host.create_nurse'))
        
        try:
            # Create User account
            user = User(
                username=username, 
                email=email, 
                password_hash=generate_password_hash(password),
                role=UserRole.NURSE
            )
            db.session.add(user)
            db.session.flush()
            
            # Create Nurse profile linked to User
            nurse = Nurse(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                registration_number=registration_number,
                specialization=specialization,
                phone=phone,
                verified=True,  # Auto-verified since created by host
                is_active=True
            )
            db.session.add(nurse)
            db.session.commit()
            
            log_audit("CREATE_NURSE", user.id, f"Created Nurse: {first_name} {last_name}")
            flash(f'Nurse {username} ({first_name} {last_name}) created successfully.', 'success')
            return redirect(url_for('host.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating nurse: {str(e)}', 'danger')
            return redirect(url_for('host.create_nurse'))
    
    return render_template('host/create_nurse.html')


# ═══ FRONTPAGE DOCTOR MANAGEMENT ═══
DOCTOR_PHOTO_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img', 'doctors')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@host_bp.route('/frontpage-doctors')
@login_required
@host_required
def frontpage_doctors():
    doctors = FrontpageDoctor.query.order_by(FrontpageDoctor.display_order.asc(), FrontpageDoctor.id.asc()).all()
    return render_template('host/frontpage_doctors.html', doctors=doctors)


@host_bp.route('/frontpage-doctors/add', methods=['POST'])
@login_required
@host_required
def frontpage_doctor_add():
    name = request.form.get('name', '').strip()
    specialization = request.form.get('specialization', '').strip()
    qualification = request.form.get('qualification', '').strip()
    experience = request.form.get('experience_years', '')
    display_order = request.form.get('display_order', '0')

    if not name or not specialization:
        flash('Doctor name and specialization are required.', 'danger')
        return redirect(url_for('host.frontpage_doctors'))

    photo_path = None
    photo = request.files.get('photo')
    if photo and photo.filename and _allowed_file(photo.filename):
        os.makedirs(DOCTOR_PHOTO_FOLDER, exist_ok=True)
        fname = secure_filename(f"dr_{name.lower().replace(' ','_')}_{int(datetime.utcnow().timestamp())}.{photo.filename.rsplit('.',1)[1].lower()}")
        photo.save(os.path.join(DOCTOR_PHOTO_FOLDER, fname))
        photo_path = f"img/doctors/{fname}"

    doc = FrontpageDoctor(
        name=name,
        specialization=specialization,
        qualification=qualification or None,
        experience_years=int(experience) if experience.isdigit() else None,
        photo_path=photo_path,
        display_order=int(display_order) if display_order.isdigit() else 0,
        is_active=True,
    )
    db.session.add(doc)
    db.session.commit()
    flash(f'Dr. {name} added to homepage.', 'success')
    log_audit('frontpage_doctor_add', target_id=doc.id, details=f'Added {name}')
    return redirect(url_for('host.frontpage_doctors'))


@host_bp.route('/frontpage-doctors/edit/<int:doc_id>', methods=['POST'])
@login_required
@host_required
def frontpage_doctor_edit(doc_id):
    doc = FrontpageDoctor.query.get_or_404(doc_id)
    doc.name = request.form.get('name', doc.name).strip()
    doc.specialization = request.form.get('specialization', doc.specialization).strip()
    doc.qualification = request.form.get('qualification', '').strip() or doc.qualification
    exp = request.form.get('experience_years', '')
    if exp.isdigit():
        doc.experience_years = int(exp)
    order = request.form.get('display_order', '')
    if order.isdigit():
        doc.display_order = int(order)

    photo = request.files.get('photo')
    if photo and photo.filename and _allowed_file(photo.filename):
        os.makedirs(DOCTOR_PHOTO_FOLDER, exist_ok=True)
        fname = secure_filename(f"dr_{doc.name.lower().replace(' ','_')}_{int(datetime.utcnow().timestamp())}.{photo.filename.rsplit('.',1)[1].lower()}")
        photo.save(os.path.join(DOCTOR_PHOTO_FOLDER, fname))
        doc.photo_path = f"img/doctors/{fname}"

    db.session.commit()
    flash(f'Dr. {doc.name} updated.', 'success')
    return redirect(url_for('host.frontpage_doctors'))


@host_bp.route('/frontpage-doctors/delete/<int:doc_id>', methods=['POST'])
@login_required
@host_required
def frontpage_doctor_delete(doc_id):
    doc = FrontpageDoctor.query.get_or_404(doc_id)
    name = doc.name
    db.session.delete(doc)
    db.session.commit()
    flash(f'Dr. {name} removed from homepage.', 'success')
    return redirect(url_for('host.frontpage_doctors'))


@host_bp.route('/frontpage-doctors/toggle/<int:doc_id>', methods=['POST'])
@login_required
@host_required
def frontpage_doctor_toggle(doc_id):
    doc = FrontpageDoctor.query.get_or_404(doc_id)
    doc.is_active = not doc.is_active
    db.session.commit()
    flash(f'Dr. {doc.name} {"shown" if doc.is_active else "hidden"} on homepage.', 'success')
    return redirect(url_for('host.frontpage_doctors'))


# ══════════════════════════════════════════════════════════════════════════
# DETAILED MANAGEMENT PAGES — Full hospital activity tracking
# ══════════════════════════════════════════════════════════════════════════

@host_bp.route('/activity/logins')
@login_required
@host_required
def login_activity():
    """All doctor, patient, staff login activity with timestamps."""
    try:
        from app.models.auth_models import LoginActivity
        activities = LoginActivity.query.order_by(LoginActivity.login_time.desc()).limit(200).all()
    except Exception:
        activities = []

    # Also get from AuditLog for login actions
    login_logs = AuditLog.query.filter(
        AuditLog.action.in_(['LOGIN', 'LOGOUT', 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'REGISTER'])
    ).order_by(AuditLog.timestamp.desc()).limit(200).all()

    return render_template('host/login_activity.html',
                           activities=activities, login_logs=login_logs)


@host_bp.route('/activity/registrations')
@login_required
@host_required
def patient_registrations():
    """All patient registrations with date, time, details."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    query = Patient.query.order_by(Patient.created_at.desc())
    total = query.count()
    patients = query.offset((page - 1) * per_page).limit(per_page).all()
    return render_template('host/patient_registrations.html',
                           patients=patients, total=total, page=page, per_page=per_page)


@host_bp.route('/activity/doctors')
@login_required
@host_required
def doctor_activity():
    """All doctor details — logins, patients seen, prescriptions, revenue."""
    doctors = Doctor.query.filter_by(is_deleted=False).all()
    doctor_data = []
    for doc in doctors:
        appt_count = Appointment.query.filter_by(doctor_id=doc.id).count()
        from app.models.models import Prescription
        rx_count = Prescription.query.filter_by(doctor_id=doc.id).count()
        revenue = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
            Billing.doctor_id == doc.id, Billing.status == 'Paid'
        ).scalar() or 0
        ip_count = IPAdmission.query.filter_by(doctor_id=doc.id, admission_status='Admitted').count()
        doctor_data.append({
            'doctor': doc,
            'appointments': appt_count,
            'prescriptions': rx_count,
            'revenue': revenue,
            'ip_patients': ip_count,
        })
    return render_template('host/doctor_activity.html', doctor_data=doctor_data)


@host_bp.route('/activity/staff')
@login_required
@host_required
def staff_activity():
    """All staff details — nurses, lab, pharmacy, reception with their activity."""
    nurses = Nurse.query.filter_by(is_deleted=False).all()
    staff_users = User.query.filter(
        User.role.in_([UserRole.LAB_STAFF, UserRole.PHARMACIST, UserRole.RECEPTIONIST, UserRole.NURSE])
    ).order_by(User.role, User.username).all()
    return render_template('host/staff_activity.html',
                           nurses=nurses, staff_users=staff_users)


@host_bp.route('/finance/billing')
@login_required
@host_required
def billing_report():
    """Complete billing report — all patient payments, pending, by type."""
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    # All bills
    bills = Billing.query.order_by(Billing.created_at.desc()).limit(200).all()

    # Summary stats
    total_revenue = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status == 'Paid').scalar() or 0
    revenue_today = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status == 'Paid', func.date(Billing.created_at) == today).scalar() or 0
    revenue_month = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status == 'Paid', func.date(Billing.created_at) >= month_start).scalar() or 0
    outstanding = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.status.in_(['Unpaid', 'Partial'])).scalar() or 0
    total_bills = Billing.query.count()
    paid_bills = Billing.query.filter_by(status='Paid').count()
    unpaid_bills = Billing.query.filter(Billing.status.in_(['Unpaid', 'Partial'])).count()

    # By type (OP vs IP)
    op_revenue = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.billing_type == 'OP', Billing.status == 'Paid').scalar() or 0
    ip_revenue = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.billing_type == 'IP', Billing.status == 'Paid').scalar() or 0

    return render_template('host/billing_report.html',
                           bills=bills, total_revenue=total_revenue,
                           revenue_today=revenue_today, revenue_month=revenue_month,
                           outstanding=outstanding, total_bills=total_bills,
                           paid_bills=paid_bills, unpaid_bills=unpaid_bills,
                           op_revenue=op_revenue, ip_revenue=ip_revenue)


@host_bp.route('/finance/pharmacy')
@login_required
@host_required
def pharmacy_report():
    """Pharmacy sales & orders — all medicines dispensed, revenue."""
    from app.models.models import PharmacyOrder, PharmacySale

    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    orders = PharmacyOrder.query.order_by(PharmacyOrder.created_at.desc()).limit(200).all()

    # Revenue from pharmacy sales
    total_pharmacy_revenue = db.session.query(
        func.coalesce(func.sum(PharmacySale.price * PharmacySale.quantity), 0)
    ).scalar() or 0
    pharmacy_today = db.session.query(
        func.coalesce(func.sum(PharmacySale.price * PharmacySale.quantity), 0)
    ).filter(func.date(PharmacySale.sold_at) == today).scalar() or 0
    pharmacy_month = db.session.query(
        func.coalesce(func.sum(PharmacySale.price * PharmacySale.quantity), 0)
    ).filter(func.date(PharmacySale.sold_at) >= month_start).scalar() or 0

    total_orders = PharmacyOrder.query.count()
    dispensed = PharmacyOrder.query.filter_by(status='Dispensed').count()
    pending = PharmacyOrder.query.filter_by(status='Pending').count()

    # Top medicines
    top_meds = db.session.query(
        PharmacyOrder.medicine_name, func.count(PharmacyOrder.id)
    ).group_by(PharmacyOrder.medicine_name).order_by(
        func.count(PharmacyOrder.id).desc()
    ).limit(15).all()

    return render_template('host/pharmacy_report.html',
                           orders=orders, total_pharmacy_revenue=total_pharmacy_revenue,
                           pharmacy_today=pharmacy_today, pharmacy_month=pharmacy_month,
                           total_orders=total_orders, dispensed=dispensed,
                           pending=pending, top_meds=top_meds)


@host_bp.route('/finance/lab')
@login_required
@host_required
def lab_report():
    """Lab orders & revenue — all tests ordered, completed, revenue."""
    from app.models.models import LabOrder

    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    orders = LabOrder.query.order_by(LabOrder.created_at.desc()).limit(200).all()

    total_orders = LabOrder.query.count()
    completed = LabOrder.query.filter_by(status='COMPLETED').count()
    pending = LabOrder.query.filter(LabOrder.status.in_(['CREATED', 'SAMPLE_COLLECTED', 'PROCESSING'])).count()
    today_orders = LabOrder.query.filter(func.date(LabOrder.created_at) == today).count()
    month_orders = LabOrder.query.filter(func.date(LabOrder.created_at) >= month_start).count()

    # Revenue from lab billing
    lab_revenue = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
        Billing.description.ilike('%lab%'), Billing.status == 'Paid'
    ).scalar() or 0

    # Top tests ordered
    top_tests = db.session.query(
        LabOrder.test_name, func.count(LabOrder.id)
    ).group_by(LabOrder.test_name).order_by(
        func.count(LabOrder.id).desc()
    ).limit(15).all()

    return render_template('host/lab_report.html',
                           orders=orders, total_orders=total_orders,
                           completed=completed, pending=pending,
                           today_orders=today_orders, month_orders=month_orders,
                           lab_revenue=lab_revenue, top_tests=top_tests)


@host_bp.route('/patients/all')
@login_required
@host_required
def all_patients():
    """Complete patient directory with all details and payment history."""
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50

    query = Patient.query
    if search:
        query = query.filter(db.or_(
            Patient.name.ilike(f'%{search}%'),
            Patient.uhid.ilike(f'%{search}%'),
            Patient.phone.ilike(f'%{search}%')
        ))
    query = query.order_by(Patient.created_at.desc())
    total = query.count()
    patients = query.offset((page - 1) * per_page).limit(per_page).all()

    # Get total paid per patient
    patient_payments = {}
    for p in patients:
        paid = db.session.query(func.coalesce(func.sum(Billing.grand_total), 0)).filter(
            Billing.patient_id == p.id, Billing.status == 'Paid'
        ).scalar() or 0
        patient_payments[p.id] = paid

    return render_template('host/all_patients.html',
                           patients=patients, patient_payments=patient_payments,
                           total=total, page=page, per_page=per_page, search=search)
