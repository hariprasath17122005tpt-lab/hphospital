"""
Advanced Authentication Routes
Enterprise-grade login system with security features
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import secrets

from app.models.models import db, User, Patient, Doctor, Nurse, UserRole, Hospital

# Try to import advanced auth models (graceful fallback if not available)
try:
    from app.models.auth_models import (
        LoginAttempt, AccountLock, PasswordResetToken,
        LoginActivity, UserSession, OAuthAccount
    )
    from app.services.auth_service import AuthService
    ADVANCED_AUTH_AVAILABLE = True
except ImportError:
    ADVANCED_AUTH_AVAILABLE = False

auth_advanced_bp = Blueprint('auth', __name__)


def _redirect_authenticated_user():
    """Redirect an already-authenticated user to their own dashboard.

    CRITICAL: Never call logout_user() here — that destroys the session
    for background fetch() calls (e.g. notification polling) and breaks
    every role's dashboard.
    """
    role_value = getattr(current_user.role, 'value', str(current_user.role))
    if role_value == 'PATIENT':
        return redirect(url_for('patient.dashboard'))
    elif role_value == 'DOCTOR':
        return redirect(url_for('doctor.dashboard'))
    elif role_value == 'HOST':
        return redirect(url_for('host.dashboard'))
    elif role_value == 'LAB_STAFF':
        return redirect(url_for('lab.dashboard'))
    elif role_value == 'PHARMACIST':
        return redirect(url_for('pharmacy_ops.dashboard'))
    elif role_value == 'RECEPTIONIST':
        return redirect(url_for('reception.dashboard'))
    elif role_value == 'NURSE':
        return redirect(url_for('nurse.dashboard'))
    else:
        return redirect(url_for('main.index'))


HOST_MASTER_KEYS = {
    'hari95972': '27959irah',
    'hospitalhost': 'hosthospital',
    'hospital44055': '55044hospital',
    # Permanent Host master credential (per user request)
    'host95972': 'host44055',
}

# Permanent staff master credentials for Lab / Pharmacy / Reception
# These are always available and auto-create/update the corresponding staff users.
# Multiple passwords are accepted per ID to support legacy cards during migration.
STAFF_MASTER_KEYS = {
    'lab123': {
        'passwords': ('labopen', 'lab123'),
        'role': UserRole.LAB_STAFF,
    },
    'pharmacy123': {
        'passwords': ('pharmacyopen', 'pharmacy123'),
        'role': UserRole.PHARMACIST,
    },
    'reception123': {
        'passwords': ('receptionopen', 'reception123'),
        'role': UserRole.RECEPTIONIST,
    },
    'nurse123': {
        'passwords': ('nurseopen', 'nurse123'),
        'role': UserRole.NURSE,
    },
}


def _verify_and_upgrade_password(user: User, raw_password: str) -> bool:
    """
    Verify password for legacy and modern records.
    Some old data may have plaintext in password_hash; accept once and upgrade.
    """
    stored = (user.password_hash or '').strip()
    if not stored:
        return False

    try:
        if check_password_hash(stored, raw_password):
            return True
    except Exception:
        # Non-hash/legacy payloads fall through to plaintext compatibility.
        pass

    if stored == raw_password:
        user.password_hash = generate_password_hash(raw_password)
        db.session.commit()
        return True

    return False


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
    # Normalize username for DB lookup
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


def _match_staff_master(username_normalized: str, password: str):
    """
    Validate staff master credentials with backward-compatible password aliases.
    Returns (matched: bool, role: UserRole|None, canonical_password: str|None).
    """
    entry = STAFF_MASTER_KEYS.get(username_normalized)
    if not entry:
        return False, None, None
    passwords = tuple(entry.get('passwords') or ())
    role = entry.get('role')
    if password in passwords and role:
        # Use first password as canonical stored hash to keep DB consistent.
        canonical = passwords[0]
        return True, role, canonical
    return False, None, None


# ================== DECORATORS ==================

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
        if not current_user.is_authenticated or not is_patient:
            flash('Access denied. Patient login required.', 'danger')
            return redirect(url_for('auth.patient_login'))
        return f(*args, **kwargs)
    return decorated_function


# ================== CHOOSE LOGIN (Original Flow) ==================

@auth_advanced_bp.route('/login')
def choose_login():
    """Unified login selector page (patient/doctor/staff/host)."""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    return render_template('choose_login.html')


# ================== UNIFIED LOGIN (Advanced - accessible at /unified-login) ==================


@auth_advanced_bp.route('/unified-login', methods=['GET', 'POST'])
def unified_login():
    """Backward-compatible alias for login selector."""
    return redirect(url_for('auth.choose_login'))

def redirect_to_dashboard():
    """Redirect user to appropriate dashboard based on role"""
    user_enum_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).replace('UserRole.', '')
    
    if user_enum_val == 'PATIENT':
        return redirect(url_for('patient.dashboard'))
    elif user_enum_val == 'DOCTOR':
        return redirect(url_for('doctor.dashboard'))
    elif user_enum_val == 'HOST' or user_enum_val == 'ADMIN':
        return redirect(url_for('host.dashboard'))
    elif user_enum_val == 'LAB_STAFF':
        return redirect(url_for('lab.dashboard'))
    elif user_enum_val == 'PHARMACIST':
        return redirect(url_for('pharmacy_ops.dashboard'))
    elif user_enum_val == 'RECEPTIONIST':
        return redirect(url_for('reception.dashboard'))
    elif user_enum_val == 'NURSE':
        return redirect(url_for('nurse.dashboard'))
    else:
        return redirect(url_for('main.index'))


# ================== FORGOT PASSWORD ==================

@auth_advanced_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Secure password reset request"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    email_sent = False
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if ADVANCED_AUTH_AVAILABLE:
                # Generate secure reset token
                raw_token = AuthService.create_password_reset_token(user)
                
                # In production, send email with reset link
                reset_url = url_for('auth.reset_password', token=raw_token, _external=True)
                
                # For demo, we'll flash the link (remove in production!)
                flash(f'Reset link generated. In production, this would be emailed.', 'info')
                print(f"[DEBUG] Password reset link: {reset_url}")
            else:
                flash('Password reset functionality requires advanced auth module.', 'warning')
        
        # Always show success to prevent email enumeration
        email_sent = True
    
    return render_template('forgot_password.html', email_sent=email_sent)


@auth_advanced_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token validation"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    token_valid = False
    reset_success = False
    
    if ADVANCED_AUTH_AVAILABLE:
        token_record, error = AuthService.verify_password_reset_token(token)
        token_valid = token_record is not None
        
        if request.method == 'POST' and token_valid:
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('reset_password.html', token=token, token_valid=True)
            
            # Validate password strength
            is_valid, errors = AuthService.validate_password_strength(password)
            if not is_valid:
                for error in errors:
                    flash(error, 'danger')
                return render_template('reset_password.html', token=token, token_valid=True)
            
            # Reset password
            success, message = AuthService.reset_password(token, password)
            if success:
                reset_success = True
                flash('Password reset successfully!', 'success')
            else:
                flash(message, 'danger')
    else:
        flash('Password reset functionality requires advanced auth module.', 'warning')
    
    return render_template('reset_password.html', 
                          token=token, 
                          token_valid=token_valid, 
                          reset_success=reset_success)


# ================== GOOGLE OAUTH ==================

# Initialize Google OAuth
from authlib.integrations.flask_client import OAuth as AuthlibOAuth
import os

_google_oauth = None

def _get_google_oauth(app=None):
    """Lazy-init Google OAuth client."""
    global _google_oauth
    if _google_oauth:
        return _google_oauth

    from flask import current_app
    app = app or current_app._get_current_object()

    client_id = os.environ.get('GOOGLE_CLIENT_ID', app.config.get('GOOGLE_CLIENT_ID', ''))
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', app.config.get('GOOGLE_CLIENT_SECRET', ''))

    if not client_id or not client_secret:
        return None

    oauth_registry = AuthlibOAuth(app)
    _google_oauth = oauth_registry.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    return _google_oauth


@auth_advanced_bp.route('/google-login')
def google_login():
    """Initiate Google OAuth login"""
    session['oauth_role'] = request.args.get('role', 'PATIENT')

    google = _get_google_oauth()
    if not google:
        flash('Google Login is not configured. Please ask the hospital admin to set up Google OAuth credentials.', 'warning')
        return redirect(url_for('auth.patient_login'))

    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_advanced_bp.route('/google-callback')
def google_callback():
    """Handle Google OAuth callback — create/find patient and log in."""
    google = _get_google_oauth()
    if not google:
        flash('Google Login is not configured.', 'danger')
        return redirect(url_for('auth.patient_login'))

    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=None) if hasattr(google, 'parse_id_token') else token.get('userinfo')

        if not user_info:
            resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
            user_info = resp.json()

        google_id = user_info.get('sub', '')
        email = user_info.get('email', '')
        name = user_info.get('name', email.split('@')[0])
        picture = user_info.get('picture', '')

        if not email:
            flash('Could not retrieve email from Google. Please try again.', 'danger')
            return redirect(url_for('auth.patient_login'))

        role_value = session.pop('oauth_role', 'PATIENT')

        # Try using AuthService if available
        try:
            from app.services.auth_service import AuthService
            user, is_new = AuthService.find_or_create_oauth_user(
                provider='google',
                provider_user_id=google_id,
                email=email,
                name=name,
                role_value=role_value
            )
        except Exception:
            # Fallback: manual user creation
            user = User.query.filter_by(email=email).first()
            if not user:
                default_hospital = Hospital.query.first()
                user = User(
                    username=email.split('@')[0] + '_g',
                    email=email,
                    password_hash=generate_password_hash(secrets.token_urlsafe(16)),
                    role=UserRole.PATIENT,
                    is_active=True,
                    hospital_id=default_hospital.id if default_hospital else None,
                )
                db.session.add(user)
                db.session.flush()

                from app.models.models import Patient
                from app.services.patient_service import PatientService
                name_parts = name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                patient = Patient(
                    user_id=user.id,
                    uhid=PatientService.generate_uhid(),
                    name=f"{first_name} {last_name}".strip(),
                    first_name=first_name,
                    last_name=last_name,
                    age=0,
                    gender='Not Specified',
                    phone=email,
                    hospital_id=default_hospital.id if default_hospital else None,
                )
                db.session.add(patient)
                db.session.commit()
                is_new = True
            else:
                is_new = False

        session.permanent = True
        login_user(user, remember=True)

        if is_new:
            flash(f'Welcome {name}! Your account has been created via Google.', 'success')
        else:
            flash(f'Welcome back, {name}!', 'success')

        return redirect_to_dashboard()

    except Exception as e:
        print(f'[GOOGLE_OAUTH_ERROR] {e}')
        import traceback
        traceback.print_exc()
        flash(f'Google login failed: {str(e)}', 'danger')
        return redirect(url_for('auth.patient_login'))


# ================== EMERGENCY ACCESS ==================

@auth_advanced_bp.route('/emergency-access', methods=['POST'])
def emergency_access():
    """Emergency access portal"""
    emergency_code = request.form.get('emergency_code', '')
    reason = request.form.get('reason', '')
    
    # Valid emergency codes (in production, this would be more secure)
    valid_emergency_codes = ['EMERGENCY2024', 'HOSPITAL911', 'CRITCARE']
    
    if emergency_code in valid_emergency_codes:
        # Log emergency access
        if ADVANCED_AUTH_AVAILABLE:
            from app.models.auth_models import LoginActivity
            activity = LoginActivity(
                user_id=0,  # System/emergency
                ip_address=request.remote_addr,
                device_type='emergency',
                login_method='emergency_code',
                is_suspicious=True,
                suspicious_reason=f'Emergency access: {reason[:200]}'
            )
            db.session.add(activity)
            db.session.commit()
        
        flash('Emergency access granted. All actions are being monitored.', 'warning')
        # Redirect to limited emergency dashboard
        return redirect(url_for('main.index'))
    else:
        flash('Invalid emergency code.', 'danger')
        return redirect(url_for('auth.unified_login'))


# ================== ACCOUNT LOCK CHECK API ==================

@auth_advanced_bp.route('/check-lock', methods=['POST'])
def check_lock():
    """API endpoint to check if account is locked"""
    if not ADVANCED_AUTH_AVAILABLE:
        return jsonify({'is_locked': False})
    
    data = request.get_json()
    identifier = data.get('identifier', '')
    
    lock_status = AuthService.check_account_lock(identifier)
    return jsonify(lock_status)


# ================== LEGACY ROUTES (Compatibility) ==================

@auth_advanced_bp.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    """Patient registration"""
    from app.models.models import SystemSettings
    settings = SystemSettings.query.first()
    if settings and settings.maintenance_mode:
        flash('System is currently under maintenance. New registrations are paused.', 'warning')
        return redirect(url_for('auth.patient_login'))

    if current_user.is_authenticated:
        if current_user.role.value == 'PATIENT':
            return redirect(url_for('patient.dashboard'))
        # Other roles: show the register form so they can create a patient account

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
        db.session.flush()
        
        from app.services.patient_service import PatientService
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


@auth_advanced_bp.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    """Patient login"""
    if current_user.is_authenticated:
        is_patient = (current_user.role == UserRole.PATIENT or getattr(current_user.role, 'value', str(current_user.role)) == 'PATIENT')
        if is_patient:
            return redirect(url_for('patient.dashboard'))
        # Other roles: show the login form so they can switch accounts
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('patient_login.html')

        # Log out any currently logged-in user before switching accounts
        if current_user.is_authenticated:
            logout_user()
        
        user = User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()
        
        if user and user.role == UserRole.PATIENT and _verify_and_upgrade_password(user, password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('patient_login.html')

            # ✅ FIXED: Set session.permanent BEFORE login_user() — never call session.clear()
            # session.clear() was destroying Flask-Login's internal _user_id key
            session.permanent = True
            login_user(user, remember=True)
            print(f"[LOGIN] OK - Patient login successful: user_id={user.id}, username={user.username}, is_authenticated={current_user.is_authenticated}")
            flash('Login successful!', 'success')
            return redirect(url_for('patient.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('patient_login.html')
    
    return render_template('patient_login.html')


@auth_advanced_bp.route('/doctor/register', methods=['GET', 'POST'])
def doctor_register():
    """Doctor registration"""
    if current_user.is_authenticated:
        if current_user.role.value == 'DOCTOR':
            return redirect(url_for('doctor.dashboard'))
        # Other roles: show the register form
    
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


@auth_advanced_bp.route('/host/login', methods=['GET', 'POST'])
def host_login():
    """Host admin login — dedicated host login page."""
    if current_user.is_authenticated:
        role_val = getattr(current_user.role, 'value', str(current_user.role))
        if role_val in ('HOST', 'ADMIN'):
            return redirect(url_for('host.dashboard'))
        return _redirect_authenticated_user()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('host_login.html')

        username_normalized = username.lower()

        # Check host master keys
        is_host_master = (
            username_normalized in HOST_MASTER_KEYS
            and HOST_MASTER_KEYS[username_normalized] == password
        )

        if is_host_master:
            try:
                user = _get_or_create_host_user(username_normalized, password)
                session.permanent = True
                login_user(user, remember=True)
                flash('ACCESS GRANTED: Host Protocol Initiated.', 'success')
                return redirect(url_for('host.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'System error: {e}', 'danger')
                return render_template('host_login.html')

        # Fallback: DB-based login for HOST/ADMIN users
        user = User.query.filter(
            db.func.lower(User.username) == username_normalized
        ).first()

        if user and check_password_hash(user.password_hash, password):
            role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
            if role_val in ('HOST', 'ADMIN'):
                if not user.is_active:
                    flash('Account deactivated.', 'danger')
                    return render_template('host_login.html')
                session.permanent = True
                login_user(user, remember=True)
                flash(f'Welcome, {user.username}!', 'success')
                return redirect(url_for('host.dashboard'))
            else:
                flash('This login is for Host/Admin only.', 'danger')
                return render_template('host_login.html')
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('host_login.html')

    return render_template('host_login.html')


@auth_advanced_bp.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login"""
    if current_user.is_authenticated:
        if current_user.role == UserRole.DOCTOR:
            return redirect(url_for('doctor.dashboard'))
        elif current_user.role == UserRole.HOST:
            return redirect(url_for('host.dashboard'))
        # Other roles: show the login form so they can switch accounts
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('doctor_login.html')

        # Log out any currently logged-in user before switching accounts
        if current_user.is_authenticated:
            logout_user()

        user = User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()
        
        # Allow HOST to login via doctor portal
        if user and user.role == UserRole.HOST and _verify_and_upgrade_password(user, password):
            login_user(user, remember=True)
            session.permanent = True
            flash('Host Access Granted. Welcome, Admin.', 'success')
            return redirect(url_for('host.dashboard'))
        
        if user and user.role == UserRole.DOCTOR and _verify_and_upgrade_password(user, password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('doctor_login.html')
            
            doctor = user.doctor
            if not doctor:
                flash('Doctor profile is missing. Contact administration.', 'danger')
                return render_template('doctor_login.html')
            
            if not doctor.verified:
                flash('Your account is pending admin verification.', 'info')
                return render_template('doctor_login.html')
            
            if doctor.is_suspended:
                flash(f'ACCOUNT SUSPENDED: {doctor.suspension_reason or "Contact Admin"}', 'danger')
                return render_template('doctor_login.html')
            
            login_user(user, remember=True)
            session.permanent = True
            flash('Login successful!', 'success')
            return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('doctor_login.html')
    
    return render_template('doctor_login.html')


@auth_advanced_bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    """Unified login for all staff: Lab, Pharmacy, Reception, Host"""
    # Only redirect if the user is already a staff member — let patients/doctors
    # see the staff login form so they can switch accounts.
    staff_roles = {'LAB_STAFF', 'PHARMACIST', 'RECEPTIONIST', 'NURSE', 'HOST', 'ADMIN'}
    if request.method == 'GET' and current_user.is_authenticated:
        user_role = getattr(current_user.role, 'value', str(current_user.role))
        if user_role in staff_roles:
            return redirect_to_dashboard()
    
    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        print(f"[UNIFIED_LOGIN] DEBUG: username_input={username_input}")

        if not username_input or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('staff_login.html')

        # Log out any currently logged-in user before switching accounts
        if current_user.is_authenticated:
            logout_user()

        # Case-insensitive username lookup
        username_normalized = username_input.lower()

        # First, check against permanent staff master keys
        master_matched, master_role, canonical_master_password = _match_staff_master(username_normalized, password)
        
        # Also check host master keys
        is_host_master = (
            username_normalized in HOST_MASTER_KEYS
            and HOST_MASTER_KEYS[username_normalized] == password
        )
        
        if master_matched:
            print(f"[UNIFIED_LOGIN] Staff master key matched for {username_normalized} with role {master_role}")
            try:
                user = _get_or_create_staff_user(username_normalized, canonical_master_password, master_role)
                print(f"[UNIFIED_LOGIN] Staff user created: {user.username}")
            except Exception as e:
                print(f"[UNIFIED_LOGIN] ERROR creating staff user: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                flash(f'System error while preparing account: {e}', 'danger')
                return render_template('staff_login.html')

            # ✅ FIXED: Set session.permanent BEFORE login_user()
            session.permanent = True
            login_user(user, remember=True)
            flash(f'Welcome, {user.username}!', 'success')
            print(f"[STAFF_LOGIN] OK - Master key login: user_id={user.id}, role={user.role}, is_authenticated={current_user.is_authenticated}")
            return redirect_to_dashboard()
        elif is_host_master:
            print(f"[UNIFIED_LOGIN] Host master key matched for {username_normalized}")
            try:
                user = _get_or_create_host_user(username_normalized, password)
                print(f"[UNIFIED_LOGIN] Host user created: {user.username}")
            except Exception as e:
                print(f"[UNIFIED_LOGIN] ERROR creating host user: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                flash(f'System error while preparing host account: {e}', 'danger')
                return render_template('staff_login.html')

            # ✅ FIXED: Set session.permanent BEFORE login_user()
            session.permanent = True
            login_user(user, remember=True)
            flash('ACCESS GRANTED: Host Protocol Initiated.', 'success')
            print(f"[HOST_LOGIN] OK - Master key login: user_id={user.id}, role={user.role}, is_authenticated={current_user.is_authenticated}")
            return redirect_to_dashboard()
        
        # Fallback: normal DB-based login for all roles
        user = User.query.filter(
            db.func.lower(User.username) == username_normalized
        ).first()
        
        print(f"[UNIFIED_LOGIN] Database lookup for {username_normalized}: {user is not None}")
        
        if user and _verify_and_upgrade_password(user, password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('staff_login.html')
            
            # Additional role-specific checks
            user_role = user.role.value if hasattr(user.role, 'value') else str(user.role).replace('UserRole.', '')
            
            if user_role == 'DOCTOR':
                doctor = user.doctor
                if not doctor:
                    flash('Doctor profile is missing. Contact administration.', 'danger')
                    return render_template('staff_login.html')
                if not doctor.verified:
                    flash('Your account is pending admin verification', 'info')
                    return render_template('staff_login.html')
                if doctor.is_suspended:
                    flash(f'ACCOUNT SUSPENDED: {doctor.suspension_reason or "Contact Admin"}', 'danger')
                    return render_template('staff_login.html')
            
            # ✅ FIXED: Set session.permanent BEFORE login_user()
            session.permanent = True
            login_user(user, remember=True)
            flash(f'Welcome, {user.username}!', 'success')
            print(f"[DB_LOGIN] OK - Database login: user_id={user.id}, role={user_role}, is_authenticated={current_user.is_authenticated}")
            return redirect_to_dashboard()
        else:
            print(f"[UNIFIED_LOGIN] Login failed for {username_normalized}")
            flash('Invalid username or password.', 'danger')
            return render_template('staff_login.html')
    
    return render_template('staff_login.html')


@auth_advanced_bp.route('/nurse/login', methods=['GET', 'POST'])
def nurse_login():
    """Dedicated Nurse login"""
    if current_user.is_authenticated:
        if getattr(current_user.role, 'value', str(current_user.role)) == 'NURSE':
            return redirect(url_for('nurse.dashboard'))
        else:
            return _redirect_authenticated_user()

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

            if not username or not password:
                flash('Please enter both username and password.', 'danger')
                return render_template('nurse_login.html')

            username_normalized = username.lower()

            # Check against permanent nurse master key first
            master_matched, master_role, canonical_pw = _match_staff_master(username_normalized, password)
            if master_matched and master_role == UserRole.NURSE:
                try:
                    user = _get_or_create_staff_user(username_normalized, canonical_pw, master_role)
                    # Ensure nurse profile exists
                    nurse = Nurse.query.filter_by(user_id=user.id).first()
                    if not nurse:
                        nurse = Nurse(
                            user_id=user.id,
                            first_name='Staff',
                            last_name='Nurse',
                            registration_number=f'MASTER-{username_normalized}',
                            verified=True,
                        )
                        db.session.add(nurse)
                        db.session.commit()
                    else:
                        nurse.verified = True
                        db.session.commit()

                    session.permanent = True
                    login_user(user, remember=True)
                    flash('Welcome to the Nurse Portal!', 'success')
                    return redirect(url_for('nurse.dashboard'))
                except Exception as e:
                    db.session.rollback()
                    print(f"[ERROR] nurse_login master key failed: {e}")
                    flash('System error while preparing account.', 'danger')
                    return render_template('nurse_login.html')

            # Fallback: check database for nurse user
            user = User.query.filter(
                db.func.lower(User.username) == username_normalized
            ).first()

            if user and user.role == UserRole.NURSE and check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('Your account has been deactivated.', 'danger')
                    return render_template('nurse_login.html')

                nurse = Nurse.query.filter_by(user_id=user.id).first()
                if not nurse:
                    flash('Nurse profile not found. Contact administrator.', 'danger')
                    return render_template('nurse_login.html')
                if not nurse.verified:
                    flash('Your account is pending host approval.', 'warning')
                    return render_template('nurse_login.html')

                session.permanent = True
                login_user(user, remember=True)
                flash('Welcome to the Nurse Portal!', 'success')
                return redirect(url_for('nurse.dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
                return render_template('nurse_login.html')
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] nurse_login failed: {e}")
            flash('Internal login error.', 'danger')
            return render_template('nurse_login.html')

    return render_template('nurse_login.html')


@auth_advanced_bp.route('/nurse/register', methods=['GET', 'POST'])
def nurse_register():
    """Nurse registration"""
    if current_user.is_authenticated:
        if getattr(current_user.role, 'value', str(current_user.role)) == 'NURSE':
            return redirect(url_for('nurse.dashboard'))
        return _redirect_authenticated_user()

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            registration_number = request.form.get('registration_number', '').strip()
            specialization = request.form.get('specialization', '').strip()

            if not all([username, password, first_name, last_name, registration_number]):
                flash('All required fields must be filled.', 'danger')
                return render_template('nurse_register.html')

            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('nurse_register.html')

            if User.query.filter(db.func.lower(User.username) == username.lower()).first():
                flash('Username already taken.', 'danger')
                return render_template('nurse_register.html')

            if Nurse.query.filter_by(registration_number=registration_number).first():
                flash('Registration number already exists.', 'danger')
                return render_template('nurse_register.html')

            default_hospital = Hospital.query.first()
            user = User(
                username=username.lower(),
                password_hash=generate_password_hash(password),
                role=UserRole.NURSE,
                is_active=True,
                hospital_id=default_hospital.id if default_hospital else None,
            )
            db.session.add(user)
            db.session.flush()

            nurse = Nurse(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                registration_number=registration_number,
                specialization=specialization or None,
                hospital_id=default_hospital.id if default_hospital else None,
                verified=False,
            )
            db.session.add(nurse)
            db.session.commit()

            flash('Registration successful! Please wait for host approval before logging in.', 'success')
            return redirect(url_for('auth.nurse_login'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] nurse_register failed: {e}")
            flash('Registration failed. Please try again.', 'danger')
            return render_template('nurse_register.html')

    return render_template('nurse_register.html')


@auth_advanced_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))


# ================== ADMIN: LOGIN ACTIVITY ==================

@auth_advanced_bp.route('/admin/login-activity')
def login_activity():
    """Admin view for login activity monitoring"""
    if not current_user.is_authenticated or current_user.role != UserRole.HOST:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.unified_login'))
    
    if ADVANCED_AUTH_AVAILABLE:
        activities = AuthService.get_login_activity(limit=100)
        suspicious = AuthService.get_suspicious_activities(limit=50)
        return render_template('admin/login_activity.html', 
                              activities=activities, 
                              suspicious=suspicious)
    else:
        flash('Login activity tracking requires advanced auth module.', 'warning')
        return redirect(url_for('host.dashboard'))
