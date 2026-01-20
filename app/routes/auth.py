from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.models import db, User, Patient, Doctor, UserRole, Hospital
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def doctor_required(f):
    """Decorator to require doctor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.DOCTOR:
            flash('Access denied. Doctor login required.', 'danger')
            return redirect(url_for('auth.doctor_login'))
        
        if current_user.doctor:
            if not current_user.doctor.verified:
                logout_user()
                flash('Your account is pending verification.', 'warning')
                return redirect(url_for('auth.doctor_login'))
            
            if current_user.doctor.is_suspended:
                reason = current_user.doctor.suspension_reason
                logout_user()
                flash(f'ACCOUNT SUSPENDED: {reason or "Contact Administration"}', 'danger')
                return redirect(url_for('auth.doctor_login'))
                
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    """Decorator to require patient role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.PATIENT:
            flash('Access denied. Patient login required.', 'danger')
            return redirect(url_for('auth.patient_login'))
        return f(*args, **kwargs)
    return decorated_function

# ================== PATIENT ROUTES ==================

@auth_bp.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    """Patient registration"""
    from app.models.models import SystemSettings
    settings = SystemSettings.query.first()
    if settings and settings.maintenance_mode:
        flash('System is currently under maintenance. New registrations are paused.', 'warning')
        return redirect(url_for('auth.patient_login'))

    if current_user.is_authenticated:
        if current_user.role.value == 'patient':
            return redirect(url_for('patient.dashboard'))
        else:
            logout_user()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        
        # Validation
        if not all([username, email, password, first_name, last_name, age, gender]):
            flash('All fields are required', 'danger')
            return render_template('patient_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('patient_register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('patient_register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('patient_register.html')
        
        # Get default hospital (for now)
        default_hospital = Hospital.query.first()
        if not default_hospital:
            # Fallback if no hospital exists (shouldn't happen if init_db run)
            flash('System Error: No hospital configured.', 'danger')
            return render_template('patient_register.html')

        # Create user and patient
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=UserRole.PATIENT,
            hospital_id=default_hospital.id
        )
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        patient = Patient(
            user_id=user.id,
            hospital_id=default_hospital.id,
            first_name=first_name,
            last_name=last_name,
            age=int(age),
            gender=gender,
            phone=phone
        )
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.patient_login'))
    
    return render_template('patient_register.html')

@auth_bp.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    """Patient login"""
    if current_user.is_authenticated:
        if current_user.role.value == 'patient':
            return redirect(url_for('patient.dashboard'))
        else:
            logout_user()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.role == UserRole.PATIENT and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated', 'danger')
                return render_template('patient_login.html')
            
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('patient.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('patient_login.html')
    
    return render_template('patient_login.html')

# ================== DOCTOR ROUTES ==================

@auth_bp.route('/doctor/register', methods=['GET', 'POST'])
def doctor_register():
    """Doctor registration"""
    if current_user.is_authenticated:
        if current_user.role.value == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        else:
            logout_user()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        license_number = request.form.get('license_number')
        specialization = request.form.get('specialization')
        qualification = request.form.get('qualification')
        phone = request.form.get('phone')
        registration_code = request.form.get('registration_code')
        
        # Validation
        if not all([username, email, password, first_name, last_name, license_number, specialization]):
            flash('All fields are required', 'danger')
            return render_template('doctor_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('doctor_register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('doctor_register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('doctor_register.html')
        
        if Doctor.query.filter_by(license_number=license_number).first():
            flash('License number already registered', 'danger')
            return render_template('doctor_register.html')
        
        # Get default hospital
        default_hospital = Hospital.query.first()
        if not default_hospital:
            flash('System Error: No hospital configured.', 'danger')
            return render_template('doctor_register.html')
        
        # Check verification code
        is_verified = False
        valid_codes = ['95972', '44055', '94439']
        if registration_code and registration_code.strip() in valid_codes:
            is_verified = True

        # Create user and doctor
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=UserRole.DOCTOR,
            hospital_id=default_hospital.id
        )
        db.session.add(user)
        db.session.flush()
        
        doctor = Doctor(
            user_id=user.id,
            hospital_id=default_hospital.id,
            first_name=first_name,
            last_name=last_name,
            license_number=license_number,
            specialization=specialization,
            qualification=qualification,
            phone=phone,
            verified=is_verified
        )
        db.session.add(doctor)
        db.session.commit()
        
        if is_verified:
            flash('Registration successful! Code accepted. Account verified.', 'success')
        else:
            flash('Registration successful! Your account is pending admin verification.', 'info')
        
        return redirect(url_for('auth.doctor_login'))
    
    return render_template('doctor_register.html')

@auth_bp.route('/host/login', methods=['GET', 'POST'])
def host_login():
    """Host Login"""
    if current_user.is_authenticated:
        if current_user.role == UserRole.HOST:
            return redirect(url_for('host.dashboard'))
        else:
            logout_user()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.role == UserRole.HOST and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('ACCESS GRANTED: Host Protocol Initiated.', 'success')
            return redirect(url_for('host.dashboard'))
        else:
            flash('ACCESS DENIED: Invalid Credentials.', 'danger')
            return render_template('host_login.html')
            
    return render_template('host_login.html')

@auth_bp.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login"""
    if current_user.is_authenticated:
        if current_user.role.value == 'DOCTOR':
            return redirect(url_for('doctor.dashboard'))
        elif current_user.role.value == 'HOST':
             return redirect(url_for('host.dashboard'))
        else:
            logout_user()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # SPECIAL CHECK FOR HOST LOGIN ON THIS PAGE (Optimization)
        if user and user.role == UserRole.HOST and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Host Access Granted. Welcome, Admin.', 'success')
            return redirect(url_for('host.dashboard'))
        
        if user and user.role == UserRole.DOCTOR and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated', 'danger')
                return render_template('doctor_login.html')
            
            doctor = user.doctor
            if not doctor.verified:
                flash('Your account is pending admin verification', 'info')
                return render_template('doctor_login.html')
            
            if doctor.is_suspended:
                 flash(f'ACCOUNT SUSPENDED: {doctor.suspension_reason or "Contact Admin"}', 'danger')
                 return render_template('doctor_login.html')
            
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('doctor_login.html')
    
    return render_template('doctor_login.html')

@auth_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))
