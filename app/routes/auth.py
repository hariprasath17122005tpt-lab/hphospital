from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.models import db, User, Patient, Doctor, Nurse, UserRole, Hospital
from app.services.patient_service import PatientService
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def _redirect_to_own_dashboard():
    """Redirect an already-authenticated user to their own dashboard.
    CRITICAL: Never call logout_user() on a wrong-role visit — it kills
    sessions for background requests (notification polling, etc.).
    """
    role_value = getattr(current_user.role, 'value', str(current_user.role)).upper()
    destinations = {
        'PATIENT': 'patient.dashboard',
        'DOCTOR': 'doctor.dashboard',
        'HOST': 'host.dashboard',
        'ADMIN': 'host.dashboard',
        'LAB_STAFF': 'lab.dashboard',
        'PHARMACIST': 'pharmacy_ops.dashboard',
        'RECEPTIONIST': 'reception.dashboard',
        'NURSE': 'nurse.dashboard',
    }
    endpoint = destinations.get(role_value, 'main.index')
    return redirect(url_for(endpoint))


HOST_MASTER_KEYS = {
    'hari95972': '27959irah',
    'hospitalhost': 'hosthospital',
    'hospital44055': '55044hospital',
    # Permanent Host master credential (per user request)
    'host95972': 'host44055',
}

# Permanent staff master credentials for Lab / Pharmacy / Reception / Nurse
# These are always available and auto-create/update the corresponding staff users.
STAFF_MASTER_KEYS = {
    'lab123': ('labopen', UserRole.LAB_STAFF),
    'pharmacy123': ('pharmacyopen', UserRole.PHARMACIST),
    'reception123': ('receptionopen', UserRole.RECEPTIONIST),
    'nurse123': ('nurseopen', UserRole.NURSE),
}


def _get_or_create_host_user(username: str, password: str):
    """Return a guaranteed HOST user for a valid master key."""
    user = User.query.filter_by(username=username).first()
    default_hospital = Hospital.query.first()
    hospital_id = default_hospital.id if default_hospital else None

    if user:
        user.role = UserRole.HOST
        user.is_active = True
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        return user

    user = User(
        username=username,
        email=f'{username}@host.system',
        password_hash=generate_password_hash(password),
        role=UserRole.HOST,
        hospital_id=hospital_id,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return user


def _get_or_create_staff_user(username: str, password: str, role: UserRole) -> User:
    """
    Return a guaranteed staff user for a valid STAFF_MASTER_KEYS entry.
    This is used for lab123 / pharmacy123 / reception123 permanent IDs.
    """
    username_normalized = username.lower()
    user = User.query.filter(db.func.lower(User.username) == username_normalized).first()
    default_hospital = Hospital.query.first()
    hospital_id = default_hospital.id if default_hospital else None

    if user:
        user.role = role
        user.is_active = True
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        return user

    user = User(
        username=username_normalized,
        email=f'{username_normalized}@staff.system',
        password_hash=generate_password_hash(password),
        role=role,
        hospital_id=hospital_id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@auth_bp.route('/login')
def choose_login():
    """Unified login selector page (patient/doctor/host)."""
    if current_user.is_authenticated:
        if current_user.role == UserRole.PATIENT:
            return redirect(url_for('patient.dashboard'))
        if current_user.role == UserRole.DOCTOR:
            return redirect(url_for('doctor.dashboard'))
        if current_user.role == UserRole.HOST:
            return redirect(url_for('host.dashboard'))
    return render_template('choose_login.html')

def doctor_required(f):
    """Decorator to require doctor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_doctor = hasattr(current_user, 'role') and (
            current_user.role == UserRole.DOCTOR or 
            getattr(current_user.role, 'value', str(current_user.role)) == 'DOCTOR'
        )
        if not current_user.is_authenticated or not is_doctor:
            flash('Access denied. Doctor login required.', 'danger')
            return redirect(url_for('auth.doctor_login'))
        
        doctor_profile = current_user.doctor
        if not doctor_profile:
            logout_user()
            flash('Doctor profile is missing. Contact administration.', 'danger')
            return redirect(url_for('auth.doctor_login'))

        if not doctor_profile.verified:
            logout_user()
            flash('Your account is pending verification.', 'warning')
            return redirect(url_for('auth.doctor_login'))
        
        if doctor_profile.is_suspended:
            reason = doctor_profile.suspension_reason
            logout_user()
            flash(f'ACCOUNT SUSPENDED: {reason or "Contact Administration"}', 'danger')
            return redirect(url_for('auth.doctor_login'))
                
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    """Decorator to require patient role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_patient = hasattr(current_user, 'role') and (
            current_user.role == UserRole.PATIENT or
            getattr(current_user.role, 'value', str(current_user.role)) == 'PATIENT'
        )
        if not current_user.is_authenticated:
            flash('Session expired or not logged in. Please log in again.', 'warning')
            return redirect(url_for('auth.patient_login'))

        if not is_patient:
            # NEVER call logout_user() here — it destroys sessions for
            # background fetch requests (e.g. notification polling).
            # Just deny access without killing the session.
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
            return _redirect_to_own_dashboard()

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
            uhid=PatientService.generate_uhid(),
            hospital_id=default_hospital.id,
            name=f"{first_name} {last_name}".strip(),
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
        if current_user.role == UserRole.PATIENT:
            return redirect(url_for('patient.dashboard'))
        else:
            return _redirect_to_own_dashboard()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.role == UserRole.PATIENT and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated', 'danger')
                return render_template('patient_login.html')
            
            # [OK] Use Flask-Login's login_user() exclusively
            # - session.permanent ensures cookie persists for 24 hours (PERMANENT_SESSION_LIFETIME)
            # - remember=True also sets remember_me cookie for auto-login on browser restart
            # - Flask-Login automatically stores user_id in session['_user_id'] via user_loader
            session.permanent = True
            login_user(user, remember=True)
            
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
            return _redirect_to_own_dashboard()

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
            return _redirect_to_own_dashboard()

    if request.method == 'POST':
        print("[DEBUG] Handling Host Login via auth.py (Standard Auth)")
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        username_normalized = username.lower()

        if username_normalized in HOST_MASTER_KEYS and HOST_MASTER_KEYS[username_normalized] == password:
            print(f"[DEBUG] Hardcoded credentials matched for {username_normalized}")
            try:
                host_user = _get_or_create_host_user(username_normalized, password)
            except Exception as e:
                print(f"[ERROR] Failed to create/update host user: {e}")
                db.session.rollback()
                flash(f'System Error logging in: {str(e)}', 'danger')
                return render_template('host_login.html')

            # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists
            session.permanent = True
            login_user(host_user, remember=True)
            flash('ACCESS GRANTED: Host Protocol Initiated.', 'success')
            return redirect(url_for('host.dashboard'))
        
        user = User.query.filter(
            db.func.lower(User.username) == username_normalized
        ).first()
        
        if user and user.role == UserRole.HOST and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('ACCESS DENIED: Account is inactive.', 'danger')
                return render_template('host_login.html')
            # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists
            session.permanent = True
            login_user(user, remember=True)
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
            return _redirect_to_own_dashboard()
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            # SPECIAL CHECK FOR HOST LOGIN ON THIS PAGE (Optimization)
            if user and user.role == UserRole.HOST and check_password_hash(user.password_hash, password):
                # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists across forwarded URLs
                session.permanent = True
                login_user(user, remember=True)
                print(f"[DOCTOR_LOGIN] [OK] HOST login: user_id={user.id}, is_authenticated={current_user.is_authenticated}, session_keys={list(session.keys())}")
                flash('Host Access Granted. Welcome, Admin.', 'success')
                return redirect(url_for('host.dashboard'))
            
            if user and user.role == UserRole.DOCTOR and check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('Your account has been deactivated', 'danger')
                    return render_template('doctor_login.html')
                
                doctor = user.doctor
                if not doctor:
                    flash('Doctor profile is missing. Contact administration.', 'danger')
                    return render_template('doctor_login.html')
                
                if not doctor.verified:
                    flash('Your account is pending admin verification', 'info')
                    return render_template('doctor_login.html')
                
                if doctor.is_suspended:
                     flash(f'ACCOUNT SUSPENDED: {doctor.suspension_reason or "Contact Admin"}', 'danger')
                     return render_template('doctor_login.html')
                
                # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists across forwarded URLs
                session.permanent = True
                login_user(user, remember=True)
                print(f"[DOCTOR_LOGIN] [OK] DOCTOR login: user_id={user.id}, is_authenticated={current_user.is_authenticated}, session_keys={list(session.keys())}")
                flash('Login successful!', 'success')
                return redirect(url_for('doctor.dashboard'))
            else:
                flash('Invalid username or password', 'danger')
                return render_template('doctor_login.html')
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] doctor_login failed: {e}")
            flash('Internal login error. Please contact administration.', 'danger')
            return render_template('doctor_login.html')
    
    return render_template('doctor_login.html')


@auth_bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    """Staff login for Lab, Pharmacy, Reception, Nurse, Admin."""
    # Optional deep link from portal chooser: ?role=LAB_STAFF|PHARMACIST|RECEPTIONIST|NURSE
    initial_role = request.args.get('role', '').strip().upper()
    if initial_role not in ['LAB_STAFF', 'PHARMACIST', 'RECEPTIONIST', 'NURSE']:
        initial_role = ''

    if current_user.is_authenticated:
        if current_user.role == UserRole.LAB_STAFF:
            return redirect(url_for('lab.dashboard'))
        if current_user.role == UserRole.PHARMACIST:
            return redirect(url_for('pharmacy_ops.dashboard'))
        if current_user.role == UserRole.RECEPTIONIST:
            return redirect(url_for('reception.dashboard'))
        if current_user.role == UserRole.NURSE:
            return redirect(url_for('nurse.dashboard'))
        if current_user.role in [UserRole.HOST, UserRole.ADMIN]:
            return redirect(url_for('host.dashboard'))
        return _redirect_to_own_dashboard()

    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        selected_role = request.form.get('staff_role', '') or None

        print(f"[STAFF_LOGIN_AUTH] DEBUG: username_input={username_input}, selected_role={selected_role}")

        if not username_input or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('staff_login.html', initial_role=initial_role)

        username_normalized = username_input.lower()

        # First, check against permanent staff master keys
        master_entry = STAFF_MASTER_KEYS.get(username_normalized)
        print(f"[STAFF_LOGIN_AUTH] Master entry for {username_normalized}: {master_entry is not None}")
        
        if master_entry and master_entry[0] == password:
            print(f"[STAFF_LOGIN_AUTH] Master key password matched for {username_normalized}")
            master_password, master_role = master_entry

            # Enforce that the selected card matches the permanent account's role (if user already chose one)
            if selected_role and selected_role != master_role.value:
                print(f"[STAFF_LOGIN_AUTH] Role mismatch: selected={selected_role}, expected={master_role.value}")
                flash('Selected department does not match this staff ID. Please pick the correct card.', 'danger')
                return render_template('staff_login.html', initial_role=initial_role)

            try:
                print(f"[STAFF_LOGIN_AUTH] Creating/updating staff user for {username_normalized} with role {master_role}")
                user = _get_or_create_staff_user(username_normalized, master_password, master_role)
                print(f"[STAFF_LOGIN_AUTH] Staff user created: {user.username}")
            except Exception as e:
                print(f"[STAFF_LOGIN_AUTH] ERROR creating staff user: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                flash(f'System error while preparing staff account: {e}', 'danger')
                return render_template('staff_login.html', initial_role=initial_role)

            # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists
            session.permanent = True
            login_user(user, remember=True)
            flash(f'Welcome, {user.username}!', 'success')

            # Redirect based on role
            if user.role == UserRole.LAB_STAFF:
                return redirect(url_for('lab.dashboard'))
            if user.role == UserRole.PHARMACIST:
                return redirect(url_for('pharmacy_ops.dashboard'))
            if user.role == UserRole.RECEPTIONIST:
                return redirect(url_for('reception.dashboard'))
            if user.role == UserRole.NURSE:
                return redirect(url_for('nurse.dashboard'))
            return redirect(url_for('host.dashboard'))
        
        print(f"[STAFF_LOGIN_AUTH] Master key check failed for {username_normalized}")
        # Fallback: normal DB-based staff login
        user = User.query.filter(
            db.func.lower(User.username) == username_normalized
        ).first()

        print(f"[STAFF_LOGIN_AUTH] Database lookup for {username_normalized}: {user is not None}")

        staff_roles = [UserRole.LAB_STAFF, UserRole.PHARMACIST, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.ADMIN]

        # Robust role check
        is_valid_role = False
        user_enum_val = None
        if user:
            user_enum_val = user.role.value if hasattr(user.role, 'value') else str(user.role).replace('UserRole.', '')
            expected_vals = {r.value if hasattr(r, 'value') else str(r).replace('UserRole.', '') for r in staff_roles}
            if user_enum_val in expected_vals:
                is_valid_role = True

        if user and is_valid_role and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('staff_login.html')

            # [OK] FIXED: Set session.permanent BEFORE login_user() to ensure it persists
            session.permanent = True
            login_user(user, remember=True)
            flash(f'Welcome, {user.username}!', 'success')

            if user_enum_val == 'LAB_STAFF':
                return redirect(url_for('lab.dashboard'))
            if user_enum_val == 'PHARMACIST':
                return redirect(url_for('pharmacy_ops.dashboard'))
            if user_enum_val == 'RECEPTIONIST':
                return redirect(url_for('reception.dashboard'))
            if user_enum_val == 'NURSE':
                return redirect(url_for('nurse.dashboard'))
            return redirect(url_for('host.dashboard'))

        print(f"[STAFF_LOGIN_AUTH] All login checks failed for {username_normalized}")
        flash('Invalid credentials or unauthorized role.', 'danger')
        return render_template('staff_login.html', initial_role=initial_role)

    return render_template('staff_login.html', initial_role=initial_role)


@auth_bp.route('/nurse/register', methods=['GET', 'POST'])
def nurse_register():
    """Nurse registration - self-register or use bypass key"""
    if current_user.is_authenticated:
        if current_user.role == UserRole.NURSE:
            return redirect(url_for('lab.dashboard'))
        else:
            return _redirect_to_own_dashboard()
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            registration_number = request.form.get('registration_number', '').strip()
            specialization = request.form.get('specialization', '').strip()
            phone = request.form.get('phone', '').strip()
            bypass_key = request.form.get('bypass_key', '').strip()  # Optional master key
            
            # Validation
            if not all([username, email, password, first_name, last_name, registration_number]):
                flash('All required fields must be completed', 'danger')
                return render_template('nurse_register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('nurse_register.html')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return render_template('nurse_register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('nurse_register.html')
            
            if Nurse.query.filter_by(registration_number=registration_number).first():
                flash('Registration number already exists', 'danger')
                return render_template('nurse_register.html')
            
            # Get default hospital
            default_hospital = Hospital.query.first()
            if not default_hospital:
                flash('System Error: No hospital configured.', 'danger')
                return render_template('nurse_register.html')
            
            # Check if bypass key is used
            is_verified = False
            if bypass_key and bypass_key.lower() in STAFF_MASTER_KEYS:
                master_password, master_role = STAFF_MASTER_KEYS[bypass_key.lower()]
                if master_role == UserRole.NURSE:
                    is_verified = True
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role=UserRole.NURSE,
                hospital_id=default_hospital.id
            )
            db.session.add(user)
            db.session.flush()
            
            # Create nurse profile
            nurse = Nurse(
                user_id=user.id,
                hospital_id=default_hospital.id,
                first_name=first_name,
                last_name=last_name,
                registration_number=registration_number,
                specialization=specialization,
                phone=phone,
                verified=is_verified
            )
            db.session.add(nurse)
            db.session.commit()
            
            if is_verified:
                flash('Registration successful! Bypass key accepted. Account verified and ready to use.', 'success')
                return redirect(url_for('auth.nurse_login'))
            else:
                flash('Registration successful! Your account is pending host approval. You will be notified once approved.', 'info')
                return redirect(url_for('auth.nurse_login'))
                
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] nurse_register failed: {e}")
            flash(f'Registration error: {str(e)}', 'danger')
            return render_template('nurse_register.html')
    
    return render_template('nurse_register.html')


@auth_bp.route('/nurse/login', methods=['GET', 'POST'])
def nurse_login():
    """Dedicated Nurse login"""
    if current_user.is_authenticated:
        if current_user.role == UserRole.NURSE:
            return redirect(url_for('nurse.dashboard'))
        else:
            return _redirect_to_own_dashboard()
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('Please enter both username and password.', 'danger')
                return render_template('nurse_login.html')
            
            username_normalized = username.lower()
            
            # Check against permanent nurse master key first
            master_entry = STAFF_MASTER_KEYS.get(username_normalized)
            if master_entry and master_entry[0] == password:
                master_password, master_role = master_entry
                
                # Verify it's nurse role
                if master_role == UserRole.NURSE:
                    try:
                        user = _get_or_create_staff_user(username_normalized, master_password, master_role)
                        # Master key bypasses approval
                        nurse = Nurse.query.filter_by(user_id=user.id).first()
                        if not nurse:
                            # Create nurse profile if not exists
                            nurse = Nurse(
                                user_id=user.id,
                                first_name='Staff',
                                last_name='Nurse',
                                registration_number=f'MASTER-{username_normalized}',
                                verified=True
                            )
                            db.session.add(nurse)
                            db.session.commit()
                        else:
                            # Ensure verified for master key
                            nurse.verified = True
                            db.session.commit()
                        
                        login_user(user)
                        flash('Welcome to the Nurse Portal!', 'success')
                        return redirect(url_for('nurse.dashboard'))
                    except Exception as e:
                        db.session.rollback()
                        print(f"[ERROR] nurse_login failed to create staff user: {e}")
                        flash('System error while preparing account. Please contact administration.', 'danger')
                        return render_template('nurse_login.html')
                else:
                    flash('This credential is not for nurse access.', 'danger')
                    return render_template('nurse_login.html')
            
            # Fallback: check database for nurse user
            user = User.query.filter(
                db.func.lower(User.username) == username_normalized
            ).first()
            
            if user and user.role == UserRole.NURSE and check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('Your account has been deactivated.', 'danger')
                    return render_template('nurse_login.html')
                
                # Check if nurse is verified by host
                nurse = Nurse.query.filter_by(user_id=user.id).first()
                if not nurse:
                    flash('Nurse profile not found. Contact administrator.', 'danger')
                    return render_template('nurse_login.html')
                
                if not nurse.verified:
                    flash('Your account is pending host approval. Please wait for administrator to verify your credentials.', 'warning')
                    return render_template('nurse_login.html')
                
                login_user(user)
                flash('Welcome to the Nurse Portal!', 'success')
                return redirect(url_for('nurse.dashboard'))
            else:
                flash('Invalid username or password', 'danger')
                return render_template('nurse_login.html')
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] nurse_login failed: {e}")
            flash('Internal login error. Please contact administration.', 'danger')
            return render_template('nurse_login.html')
    
    return render_template('nurse_login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Fallback forgot-password page for standard auth mode."""
    email_sent = False
    if request.method == 'POST':
        # Keep non-enumerating response in standard mode.
        email_sent = True
    return render_template('forgot_password.html', email_sent=email_sent)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Fallback reset-password page for standard auth mode."""
    reset_success = False
    token_valid = True
    if request.method == 'POST':
        reset_success = False
        flash('Password reset is unavailable in standard auth mode.', 'warning')
    return render_template('reset_password.html', token=token, token_valid=token_valid, reset_success=reset_success)


@auth_bp.route('/google-login')
def google_login():
    """Fallback Google login endpoint for standard auth mode."""
    flash('Google OAuth is not enabled in standard auth mode.', 'info')
    return redirect(url_for('auth.patient_login'))


@auth_bp.route('/google-callback')
def google_callback():
    """Fallback Google callback endpoint for standard auth mode."""
    flash('Google OAuth callback received.', 'info')
    return redirect(url_for('auth.patient_login'))


@auth_bp.route('/emergency-access', methods=['POST'])
def emergency_access():
    """Fallback emergency access handler for standard auth mode."""
    flash('Emergency access is unavailable in standard auth mode.', 'warning')
    return redirect(url_for('auth.patient_login'))


@auth_bp.route('/unified-login', methods=['GET', 'POST'])
def unified_login():
    """Fallback unified login route for standard auth mode."""
    if current_user.is_authenticated:
        if current_user.role == UserRole.PATIENT:
            return redirect(url_for('patient.dashboard'))
        if current_user.role == UserRole.DOCTOR:
            return redirect(url_for('doctor.dashboard'))
        if current_user.role == UserRole.HOST:
            return redirect(url_for('host.dashboard'))
        if current_user.role == UserRole.LAB_STAFF:
            return redirect(url_for('lab.dashboard'))
        if current_user.role == UserRole.PHARMACIST:
            return redirect(url_for('pharmacy_ops.dashboard'))
        if current_user.role == UserRole.RECEPTIONIST:
            return redirect(url_for('reception.dashboard'))
        return _redirect_to_own_dashboard()

    if request.method == 'POST':
        email_or_id = request.form.get('email_or_id', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'patient')

        user = User.query.filter(
            (User.email == email_or_id) | (User.username == email_or_id)
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid credentials.', 'danger')
            return render_template('unified_login.html')

        if not user.is_active:
            flash('Your account has been deactivated.', 'danger')
            return render_template('unified_login.html')

        role_map = {
            'patient': [UserRole.PATIENT],
            'doctor': [UserRole.DOCTOR, UserRole.HOST],
            'staff': [UserRole.LAB_STAFF, UserRole.PHARMACIST, UserRole.RECEPTIONIST, UserRole.ADMIN, UserRole.HOST],
            'admin': [UserRole.HOST]
        }
        if role in role_map and user.role not in role_map[role]:
            flash('Please use the correct portal for your account type.', 'warning')
            return render_template('unified_login.html')

        if user.role == UserRole.DOCTOR:
            doctor = user.doctor
            if not doctor:
                flash('Doctor profile is missing. Contact administration.', 'danger')
                return render_template('unified_login.html')
            if not doctor.verified:
                flash('Your account is pending admin verification.', 'info')
                return render_template('unified_login.html')
            if doctor.is_suspended:
                flash(f'Account suspended: {doctor.suspension_reason or "Contact Admin"}', 'danger')
                return render_template('unified_login.html')

        login_user(user)
        flash('Login successful! Welcome back.', 'success')

        if user.role == UserRole.PATIENT:
            return redirect(url_for('patient.dashboard'))
        if user.role == UserRole.DOCTOR:
            return redirect(url_for('doctor.dashboard'))
        if user.role == UserRole.HOST:
            return redirect(url_for('host.dashboard'))
        if user.role == UserRole.LAB_STAFF:
            return redirect(url_for('lab.dashboard'))
        if user.role == UserRole.PHARMACIST:
            return redirect(url_for('pharmacy_ops.dashboard'))
        if user.role == UserRole.RECEPTIONIST:
            return redirect(url_for('reception.dashboard'))

        return redirect(url_for('main.index'))

    return render_template('unified_login.html')

@auth_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))
