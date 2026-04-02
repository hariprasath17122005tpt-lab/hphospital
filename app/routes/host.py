
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.models.models import db, User, UserRole, Doctor, Nurse, Patient, AuditLog, SystemSettings, Hospital
from functools import wraps
from datetime import datetime

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
    
    return render_template('host/dashboard.html', 
                         total_doctors=total_doctors,
                         pending_doctors=pending_doctors,
                         total_patients=total_patients,
                         settings=settings,
                         recent_logs=recent_logs)

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
        # settings.ai_enabled = request.form.get('ai_enabled') == 'on' # Removed per user request
        settings.disclaimer_text = request.form.get('disclaimer_text')
        
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


# --- Emergency Override (Global) ---
# This is a bit tricky to implement globally without middleware, 
# but we can simulate it by checking it in main decorators or context processors.
