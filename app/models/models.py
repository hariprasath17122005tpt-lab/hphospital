from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum
import json

db = SQLAlchemy()

class UserRole(enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"  # Hospital Admin
    HOST = "HOST"    # Super Admin / Host
    NURSE = "NURSE"
    LAB_STAFF = "LAB_STAFF"
    PHARMACIST = "PHARMACIST"
    RECEPTIONIST = "RECEPTIONIST"

class Hospital(db.Model):
    """Hospital Tenant Model"""
    __tablename__ = 'hospitals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    domain_prefix = db.Column(db.String(50), unique=True)  # For subdomains like apollo.health.ai
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    branding_config = db.Column(db.Text)  # JSON for logo, colors
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', back_populates='hospital')
    patients = db.relationship('Patient', back_populates='hospital')
    doctors = db.relationship('Doctor', back_populates='hospital')
    nurses = db.relationship('Nurse', back_populates='hospital')

    def __repr__(self):
        return f'<Hospital {self.name}>'

class User(UserMixin, db.Model):
    """Base User model for both doctor and patient"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True) # Valid only for multi-tenant users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    hospital = db.relationship('Hospital', back_populates='users')
    patient = db.relationship('Patient', back_populates='user', uselist=False)
    doctor = db.relationship('Doctor', back_populates='user', uselist=False)
    nurse = db.relationship('Nurse', back_populates='user', foreign_keys='Nurse.user_id', uselist=False)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Patient(db.Model):
    """Patient profile model - supports both login and walk-in patients"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)  # Optional - walk-in patients don't need login
    uhid = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Unique Hospital ID: PAT-YYYY-XXXX
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    # Canonical patient identity fields (independent of login accounts)
    name = db.Column(db.String(120), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    # Backward-compatible split name fields used by older templates/routes.
    first_name = db.Column(db.String(80), nullable=False, default='')
    last_name = db.Column(db.String(80), nullable=False, default='')
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Float)  # in kg
    height = db.Column(db.Float)  # in cm
    blood_type = db.Column(db.String(10))
    medical_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    phone = db.Column(db.String(20), index=True)  # Index for search
    address = db.Column(db.Text)
    is_walk_in = db.Column(db.Boolean, default=False)  # True if patient registered manually without user account
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    hospital = db.relationship('Hospital', back_populates='patients')
    user = db.relationship('User', back_populates='patient')
    health_data = db.relationship('HealthData', back_populates='patient', cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', back_populates='patient', cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', back_populates='patient', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='patient', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.uhid}: {self.full_name}>'
    
    @property
    def full_name(self):
        """Get patient's full name"""
        if self.name and self.name.strip():
            return self.name.strip()
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self):
        """Get patient display name with UHID"""
        return f"{self.full_name} ({self.uhid})"

    def sync_legacy_name_fields(self):
        """
        Keep first_name/last_name and canonical name synchronized.
        Safe to call before save from API/service layers.
        """
        if self.name and self.name.strip():
            parts = [p for p in self.name.strip().split(' ') if p]
            self.first_name = parts[0] if parts else (self.first_name or '')
            self.last_name = ' '.join(parts[1:]) if len(parts) > 1 else (self.last_name or '')
        else:
            merged = f"{self.first_name or ''} {self.last_name or ''}".strip()
            self.name = merged
    
    def is_registered_user(self):
        """Check if patient has a user account (login capability)"""
        return self.user_id is not None


class Visit(db.Model):
    """Centralized patient visit ledger for OP, LAB, and PHARMACY touchpoints."""
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_type = db.Column(db.String(20), nullable=False)  # OP / LAB / PHARMACY
    visit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('visits', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('visits', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_visits_patient_date', 'patient_id', 'visit_date'),
    )

    def __repr__(self):
        return f'<Visit {self.visit_type} P:{self.patient_id}>'


class Doctor(db.Model):
    """Doctor profile model"""
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(200))
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    experience_years = db.Column(db.Integer)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    phone = db.Column(db.String(20))
    clinic_address = db.Column(db.Text)
    consultation_fee = db.Column(db.Float)
    availability_hours = db.Column(db.String(200))
    
    # Approval & Status
    verified = db.Column(db.Boolean, default=False)
    is_suspended = db.Column(db.Boolean, default=False)
    suspension_reason = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False) # Soft delete
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    hospital = db.relationship('Hospital', back_populates='doctors')
    user = db.relationship('User', back_populates='doctor')
    appointments = db.relationship('Appointment', back_populates='doctor', cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', back_populates='doctor', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='doctor', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Doctor {self.first_name} {self.last_name}>'


class Nurse(db.Model):
    """Nurse profile model"""
    __tablename__ = 'nurses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    specialization = db.Column(db.String(100))  # General, Surgical, ICU, Pediatric, etc.
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    phone = db.Column(db.String(20))
    
    # Approval & Status
    verified = db.Column(db.Boolean, default=False)  # Host approval required
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = db.Column(db.DateTime)  # When host approved
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Which host approved
    
    # Relationships
    hospital = db.relationship('Hospital', back_populates='nurses')
    user = db.relationship('User', back_populates='nurse', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<Nurse {self.first_name} {self.last_name}>'


class AuditLog(db.Model):
    """System Audit Logs for Host/Admin"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Who performed the action (None if system)
    actor_name = db.Column(db.String(100)) # Snapshot of name
    action = db.Column(db.String(100), nullable=False) # e.g., "APPROVE_DOCTOR", "PRESCRIBE_MED"
    target_id = db.Column(db.String(50)) # ID of object affected
    details = db.Column(db.Text) # JSON or text
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Audit {self.action} by {self.actor_name}>'

class SystemSettings(db.Model):
    """Global System Settings (Controlled by Host)"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    emergency_mode = db.Column(db.Boolean, default=False) # Locks down system, shows banner
    maintenance_mode = db.Column(db.Boolean, default=False) # Preventive maintenance
    ai_enabled = db.Column(db.Boolean, default=True)
    disclaimer_text = db.Column(db.Text)
    ai_daily_limit = db.Column(db.Integer, default=1000)
    whatsapp_number = db.Column(db.String(20), default='919443966329')

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HealthData(db.Model):
    """Patient health parameters"""
    __tablename__ = 'health_data'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # BP
    systolic_bp = db.Column(db.Integer)
    diastolic_bp = db.Column(db.Integer)
    
    # Blood Sugar
    fasting_sugar = db.Column(db.Float)
    random_sugar = db.Column(db.Float)
    
    # Heart
    heart_rate = db.Column(db.Integer)
    
    # ECG (optional)
    ecg_slope = db.Column(db.String(50))
    st_depression = db.Column(db.Float)
    
    # Body Temperature
    temperature = db.Column(db.Float) # in Fahrenheit
    
    # Symptoms
    symptoms = db.Column(db.Text)
    
    # Risk predictions (AI results)
    diabetes_risk = db.Column(db.Float)  # 0-100%
    heart_disease_risk = db.Column(db.Float)  # 0-100%
    hypertension_risk = db.Column(db.Float)  # 0-100%
    bmi = db.Column(db.Float)
    bmi_category = db.Column(db.String(50))  # Underweight, Normal, Overweight, Obese
    
    # Lifestyle
    smoking = db.Column(db.Boolean)
    alcohol = db.Column(db.Boolean)
    exercise_minutes = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    stress_level = db.Column(db.String(50))  # Low, Medium, High
    
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    patient = db.relationship('Patient', back_populates='health_data')
    
    def __repr__(self):
        return f'<HealthData Patient:{self.patient_id} at {self.recorded_at}>'


class Appointment(db.Model):
    """Doctor-Patient appointments"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', back_populates='appointments')
    doctor = db.relationship('Doctor', back_populates='appointments')
    
    def __repr__(self):
        return f'<Appointment P:{self.patient_id} D:{self.doctor_id}>'


class Prescription(db.Model):
    """Doctor prescriptions"""
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    
    # Prescription details
    diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)
    medicines = db.Column(db.Text, nullable=False, default="[]")  # Legacy or quick notes
    dosage = db.Column(db.Text)
    frequency = db.Column(db.String(200))
    duration = db.Column(db.String(100))
    instructions = db.Column(db.Text)
    diet_recommendations = db.Column(db.Text)
    exercise_recommendations = db.Column(db.Text)
    
    prescribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    # New Features
    image_path = db.Column(db.String(255)) # For handwritten prescription
    is_verified = db.Column(db.Boolean, default=False)
    refill_requested = db.Column(db.Boolean, default=False)
    refill_status = db.Column(db.String(50)) # Pending, Approved, Denied
    
    # Relationships
    patient = db.relationship('Patient', back_populates='prescriptions')
    doctor = db.relationship('Doctor', back_populates='prescriptions')
    
    def __repr__(self):
        return f'<Prescription P:{self.patient_id} D:{self.doctor_id}>'

class PrescriptionMedicine(db.Model):
    """Individual medicines mapped to a specific prescription"""
    __tablename__ = 'prescription_medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    instruction = db.Column(db.Text)
    food_relation = db.Column(db.String(100)) # Before Food, After Food, etc.

    prescription = db.relationship('Prescription', backref=db.backref('medicine_items', lazy='dynamic'))


class Message(db.Model):
    """Chat messages between Doctor and Patient"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'doctor' or 'patient'
    message_text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', back_populates='messages')
    doctor = db.relationship('Doctor', back_populates='messages')
    
    def __repr__(self):
        return f'<Message from {self.sender_type}>'


class DietPlan(db.Model):
    """AI-Generated diet plans"""
    __tablename__ = 'diet_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Meal plans
    breakfast = db.Column(db.Text)
    lunch = db.Column(db.Text)
    dinner = db.Column(db.Text)
    snacks = db.Column(db.Text)
    
    # Recommendations
    water_intake = db.Column(db.String(100))
    foods_to_avoid = db.Column(db.Text)
    foods_to_eat = db.Column(db.Text)
    
    diet_type = db.Column(db.String(100))  # diabetic, high-bp, weight-loss, etc.
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<DietPlan Patient:{self.patient_id}>'


class ExercisePlan(db.Model):
    """AI-Generated exercise plans"""
    __tablename__ = 'exercise_plans'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)

    exercises = db.Column(db.Text)  # JSON or text description
    duration_minutes = db.Column(db.Integer)
    frequency = db.Column(db.String(100))  # daily, thrice-weekly, etc.
    intensity = db.Column(db.String(50))  # low, moderate, high
    precautions = db.Column(db.Text)

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)

    def __repr__(self):
        return f'<ExercisePlan Patient:{self.patient_id}>'


class MedicalImage(db.Model):
    """Medical images uploaded by patients"""
    __tablename__ = 'medical_images'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)

    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    image_type = db.Column(db.String(50), nullable=False)  # xray, ct, mri, etc.
    clinical_context = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)

    # Analysis results
    analysis_results = db.Column(db.Text)  # JSON format
    detected_conditions = db.Column(db.Text)  # JSON format
    confidence_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))  # Low, Medium, High

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyzed_at = db.Column(db.DateTime)

    # Relationships
    patient = db.relationship('Patient', backref='medical_images')

    def __repr__(self):
        return f'<MedicalImage {self.filename} Patient:{self.patient_id}>'


class Billing(db.Model):
    """Patient Billing and Invoices"""
    __tablename__ = 'billings'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    # Nullable for walk-in laboratory-only visits (no referring doctor on the bill)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Unpaid')  # Unpaid, Paid, Cancelled
    description = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50))
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='billings')
    doctor = db.relationship('Doctor', backref='billings')
    appointment = db.relationship('Appointment', backref='billing')

    def __repr__(self):
        return f'<Billing {self.id} - {self.status}>'


class LabReport(db.Model):
    """Patient Lab Test Reports"""
    __tablename__ = 'lab_reports'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    lab_order_id = db.Column(db.Integer, db.ForeignKey('lab_orders.id'), nullable=True)
    
    test_name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    report_data = db.Column(db.JSON, nullable=True) # Structured dynamic fields
    
    result_value = db.Column(db.String(255))
    reference_range = db.Column(db.String(100))
    unit = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Pending')  # Pending, In Progress, Completed
    notes = db.Column(db.Text)
    remarks = db.Column(db.Text)  # Lab staff remarks
    
    critical_alert = db.Column(db.Boolean, default=False)
    conducted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='lab_reports', foreign_keys=[patient_id])
    doctor = db.relationship('Doctor', backref='lab_reports', foreign_keys=[doctor_id])
    lab_order = db.relationship('LabOrder', backref='generated_reports')

    def __repr__(self):
        return f'<LabReport {self.test_name}>'


class LabTestTemplate(db.Model):
    __tablename__ = 'lab_test_templates'

    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), unique=True, nullable=False)
    fields = db.Column(db.JSON, nullable=False)
    normal_ranges = db.Column(db.JSON, nullable=True)



class LabOrder(db.Model):
    """
    Unified laboratory workflow order (doctor-referred or walk-in).
    source_type: DOCTOR | WALK_IN — doctor_id must be set iff DOCTOR.
    status: PENDING → SAMPLE_COLLECTED → PROCESSING → COMPLETED
    """
    __tablename__ = 'lab_orders'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)

    source_type = db.Column(db.String(20), nullable=False)  # DOCTOR, WALK_IN
    test_name = db.Column(db.String(200), nullable=False)
    test_category = db.Column(db.String(100), nullable=False, default='General')

    status = db.Column(db.String(32), nullable=False, default='PENDING')
    result_data = db.Column(db.Text)  # JSON: narrative, structured values, optional file path

    billing_id = db.Column(db.Integer, db.ForeignKey('billings.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('lab_orders', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('lab_orders', lazy='dynamic'))
    billing = db.relationship('Billing', foreign_keys=[billing_id], backref=db.backref('lab_order_row', uselist=False))

    def result_preview(self):
        """Short text for EMR / doctor lists."""
        if not self.result_data:
            return ''
        try:
            d = json.loads(self.result_data)
            if isinstance(d, dict):
                # Primary narrative field support
                for key in ('narrative', 'summary', 'text'):
                    value = d.get(key)
                    if value and str(value).strip():
                        return str(value).strip()[:400]

                # Fallback structured field preview (top 3 entries)
                parts = []
                for key, value in d.items():
                    if key in ('narrative', 'summary', 'text'):
                        continue
                    if value is None:
                        continue
                    text = str(value).strip()
                    if not text:
                        continue
                    parts.append(f"{key}: {text}")
                    if len(parts) >= 3:
                        break
                return (', '.join(parts)[:400]) if parts else ''

            return str(d)[:400]
        except (json.JSONDecodeError, TypeError):
            return (self.result_data or '')[:400]

    def result_attachment_rel_path(self):
        """Return file path from result_data JSON if present, else check generated reports."""
        if self.result_data:
            try:
                d = json.loads(self.result_data) if isinstance(self.result_data, str) else self.result_data
                if isinstance(d, dict):
                    for key in ('file_path', 'attachment', 'pdf_path', 'report_path'):
                        if d.get(key):
                            return d[key]
            except (json.JSONDecodeError, TypeError):
                pass
        # Check if any generated LabReport has a file_path
        for report in (self.generated_reports or []):
            if report.file_path:
                return report.file_path
        return None


class Medicine(db.Model):
    """Pharmacy medicine master for bulk import + fast search."""
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    brand = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=True)
    stock = db.Column(db.Integer, default=0)
    supplier = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Legacy optional fields retained for backward compatibility with old inventory pages.
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    expiry_date = db.Column(db.String(20))
    batch_number = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))

    __table_args__ = (
        db.UniqueConstraint('name', 'brand', name='unique_medicine'),
    )

    # Backward-compatible alias used by older code.
    @property
    def unit_price(self):
        return self.price

    @unit_price.setter
    def unit_price(self, value):
        self.price = value
    
    # helper property to determine status
    @property
    def status(self):
        if self.stock == 0:
            return "Out of Stock"
        elif self.stock < 50:
            return "Low"
        return "Adequate"

    def __repr__(self):
        return f'<Medicine {self.name}>'


class BloodInventory(db.Model):
    """Blood Bank Inventory"""
    __tablename__ = 'blood_inventory'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    
    blood_group = db.Column(db.String(5), nullable=False) # A+, B-, etc.
    units = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status(self):
        if self.units < 5:
            return "Critical"
        elif self.units < 10:
            return "Low"
        return "Adequate"

    def __repr__(self):
        return f'<BloodInventory {self.blood_group}: {self.units}>'


class Bed(db.Model):
    """Hospital Bed Management"""
    __tablename__ = 'beds'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    
    ward_type = db.Column(db.String(50), nullable=False) # ICU, General Ward, Emergency
    bed_number = db.Column(db.String(20), nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    
    # helper for categorization
    @property
    def label(self):
        return f"{self.ward_type} - {self.bed_number}"

    @property
    def status(self):
        return "Occupied" if self.is_occupied else "Vacant"

    def __repr__(self):
        return f'<Bed {self.bed_number} ({self.ward_type})>'


class Ambulance(db.Model):
    """Ambulance Fleet Management"""
    __tablename__ = 'ambulances'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(50), default='Basic Life Support') # BLS, ALS
    status = db.Column(db.String(50), default='Available') # Available, On Mission, Maintenance
    current_location = db.Column(db.String(100), default='Hospital Base')
    driver_name = db.Column(db.String(100))
    driver_phone = db.Column(db.String(20))

    def __repr__(self):
        return f'<Ambulance {self.vehicle_number}>'


class DoctorEvent(db.Model):
    """Doctor Schedule/Calendar Events"""
    __tablename__ = 'doctor_events'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True) # If null, general event
    
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.String(50)) # surgery, opd, meeting

    def __repr__(self):
        return f'<Event {self.title}>'


class NurseTask(db.Model):
    """Nurse Task Management - Tasks assigned to nurses by doctors"""
    __tablename__ = 'nurse_tasks'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    assigned_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Specific nurse (optional)
    created_by_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)  # Doctor who created
    
    # Task details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50))  # medication, dressing, observation, measurement, check_vitals, etc.
    
    # Priority and scheduling
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    due_date = db.Column(db.DateTime)
    frequency = db.Column(db.String(100))  # once, daily, twice_daily, 4_hourly, as_needed
    
    # Status tracking
    status = db.Column(db.String(50), default='Pending')  # Pending, In Progress, Completed, Cancelled
    is_completed = db.Column(db.Boolean, default=False)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nurse who completed
    completion_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='nurse_tasks')
    assigned_nurse = db.relationship('User', foreign_keys=[assigned_nurse_id], backref='assigned_nurse_tasks')
    created_by_doctor = db.relationship('Doctor', foreign_keys=[created_by_doctor_id], backref='created_nurse_tasks')
    completed_by = db.relationship('User', foreign_keys=[completed_by_id], backref='completed_nurse_tasks')

    __table_args__ = (
        db.Index('idx_nurse_tasks_patient', 'patient_id'),
        db.Index('idx_nurse_tasks_status', 'status'),
        db.Index('idx_nurse_tasks_due_date', 'due_date'),
    )

    def __repr__(self):
        return f'<NurseTask {self.title} - {self.status}>'


class NurseNote(db.Model):
    """Nursing notes about patient care"""
    __tablename__ = 'nurse_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Nurse who wrote the note
    
    # Note content
    note_type = db.Column(db.String(50), default='general')  # general, observation, care_plan, handover, etc.
    content = db.Column(db.Text, nullable=False)
    
    # Categories
    is_critical = db.Column(db.Boolean, default=False)  # Flag critical observations
    related_vitals_id = db.Column(db.Integer, db.ForeignKey('patient_vitals.id'), nullable=True)  # Link to vitals observation
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='nurse_notes')
    nurse = db.relationship('User', backref='nurse_notes', foreign_keys=[nurse_id])
    related_vitals = db.relationship('PatientVitals', backref='associated_notes', foreign_keys=[related_vitals_id])
    
    __table_args__ = (
        db.Index('idx_nurse_notes_patient', 'patient_id'),
        db.Index('idx_nurse_notes_date', 'created_at'),
    )
    
    def __repr__(self):
        return f'<NurseNote Patient:{self.patient_id} Nurse:{self.nurse_id}>'


class Staff(db.Model):
    """General Staff for HR"""
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    department = db.Column(db.String(50))
    status = db.Column(db.String(20)) # Present, On Leave
    
    def __repr__(self):
        return f'<Staff {self.name}>'


class ChatHistory(db.Model):
    """AI Chatbot Chat History"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), default='neural-chat')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='chat_history')
    
    def __repr__(self):
        return f'<ChatHistory {self.user_id} - {self.timestamp}>'


class ClinicalDietPlan(db.Model):
    """Professional clinical diet plans generated by AI Dietician"""
    __tablename__ = 'clinical_diet_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, unique=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    
    # Patient health metrics
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    
    # Clinical conditions (stored as JSON for flexibility)
    medical_conditions = db.Column(db.Text, nullable=False)  # JSON array: ["DIABETES_TYPE2", "HYPERTENSION"]
    activity_level = db.Column(db.String(50), nullable=False)  # SEDENTARY, LIGHTLY_ACTIVE, MODERATELY_ACTIVE, etc.
    
    # Current medications (stored as JSON)
    medications = db.Column(db.Text, nullable=True)  # JSON array
    
    # Recent lab values (stored as JSON)
    recent_labs = db.Column(db.Text, nullable=True)  # JSON: {"HbA1c": 8.2, "LDL_C": 145}
    
    # Diet plan details
    diet_type = db.Column(db.String(100), nullable=False)  # e.g., "Low Glycemic Index + DASH"
    
    # Caloric targets
    caloric_maintenance = db.Column(db.Float, nullable=False)
    caloric_target_weight_loss = db.Column(db.Float, nullable=False)
    
    # Macronutrient distribution (JSON)
    macro_distribution = db.Column(db.Text, nullable=False)  # {"carbs": 45-50%, "protein": 25-30%, "fat": 20-25%}
    
    # Meal plan (JSON)
    meal_plan = db.Column(db.Text, nullable=False)  # Structured breakfast, lunch, dinner, snacks
    
    # Food lists (JSON)
    restricted_foods = db.Column(db.Text, nullable=False)  # Foods to avoid
    recommended_foods = db.Column(db.Text, nullable=False)  # Foods to consume
    
    # Drug interactions (JSON)
    drug_interactions = db.Column(db.Text, nullable=True)  # Drug-nutrient interactions & warnings
    
    # Safety notes and precautions
    safety_notes = db.Column(db.Text, nullable=True)  # JSON array of safety precautions
    
    # Expected clinical outcomes
    expected_outcomes = db.Column(db.Text, nullable=True)  # JSON with timeline
    
    # Complete formatted plan (for display)
    full_plan_text = db.Column(db.Text, nullable=False)  # Complete professional report
    
    # Metadata
    generated_by_system = db.Column(db.String(50), default='AI-Dietician')  # System that generated the plan
    physician_notes = db.Column(db.Text, nullable=True)  # Additional notes from physician
    is_active = db.Column(db.Boolean, default=True)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    next_review_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    patient = db.relationship('Patient', backref='clinical_diet_plans')
    doctor = db.relationship('Doctor', backref='prescribed_diet_plans')
    
    def __repr__(self):
        return f'<ClinicalDietPlan Patient:{self.patient_id} Type:{self.diet_type}>'


class PatientCheckIn(db.Model):
    """Patient Express Check-in System - Doctor can accept/reject check-ins"""
    __tablename__ = 'patient_checkins'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)  # Assigned doctor
    
    # Check-in details
    check_in_reason = db.Column(db.String(255), nullable=False)  # Why patient is checking in
    visit_type = db.Column(db.String(50), default='follow-up')  # follow-up, new-complaint, emergency, etc.
    
    # Patient reported symptoms
    symptoms = db.Column(db.Text, nullable=True)  # JSON array of symptoms
    severity = db.Column(db.String(50), nullable=True)  # mild, moderate, severe
    
    # Patient vital signs (if available)
    temperature = db.Column(db.Float, nullable=True)
    blood_pressure = db.Column(db.String(50), nullable=True)  # e.g., "120/80"
    heart_rate = db.Column(db.Integer, nullable=True)
    
    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, accepted, rejected, completed
    priority = db.Column(db.String(50), default='normal')  # low, normal, urgent
    
    # Doctor's response
    doctor_notes = db.Column(db.Text, nullable=True)  # Doctor's notes when accepting/rejecting
    acceptance_time = db.Column(db.DateTime, nullable=True)  # When doctor accepted
    qr_code_path = db.Column(db.String(255))
    estimated_wait_time = db.Column(db.Integer) # in minutes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='check_ins')
    doctor = db.relationship('Doctor', backref='pending_check_ins')
    
    def __repr__(self):
        return f'<PatientCheckIn Patient:{self.patient_id} Status:{self.status} Created:{self.created_at}>'

class HealthVideo(db.Model):
    """Educational Health Videos"""
    __tablename__ = 'health_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500), nullable=False) # YouTube ID or file path
    duration = db.Column(db.String(20)) # e.g. "3:45"
    thumbnail_url = db.Column(db.String(500))
    
    # Categories / Tags
    category = db.Column(db.String(50)) # Cardiology, Wellness, etc.
    condition_tags = db.Column(db.String(200)) # e.g. "hypertension, diabetes"
    is_doctor_recorded = db.Column(db.Boolean, default=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('Doctor', backref='recorded_videos')

    def __repr__(self):
        return f'<Video {self.title}>'

class VideoProgress(db.Model):
    """Track patient video progress"""
    __tablename__ = 'video_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('health_videos.id'), nullable=False)
    
    watched_seconds = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='video_progress')
    video = db.relationship('HealthVideo', backref='progress_records')

    def __repr__(self):
        return f'<VideoProgress Patient:{self.patient_id} Video:{self.video_id}>'


# ===================== MEDICAL STAFF MODULES =====================

class PatientVitals(db.Model):
    """Patient vital signs recorded by nurses"""
    __tablename__ = 'patient_vitals'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Vital signs
    temperature = db.Column(db.Float, nullable=False)
    systolic_bp = db.Column(db.Integer, nullable=False)
    diastolic_bp = db.Column(db.Integer, nullable=False)
    heart_rate = db.Column(db.Integer, nullable=False)
    oxygen_level = db.Column(db.Float, nullable=False)

    # Optional fields
    respiratory_rate = db.Column(db.Integer)
    blood_sugar = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float)
    notes = db.Column(db.Text)

    # Timestamps
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='vitals')
    nurse = db.relationship('User', backref='recorded_vitals', foreign_keys=[nurse_id])

    __table_args__ = (
        db.Index('idx_vitals_patient_date', 'patient_id', 'recorded_at'),
    )

    @property
    def has_alerts(self):
        alerts = []
        if self.temperature and self.temperature > 100.4:
            alerts.append('fever')
        if self.systolic_bp and self.systolic_bp > 140:
            alerts.append('high_bp')
        if self.systolic_bp and self.systolic_bp < 90:
            alerts.append('low_bp')
        if self.oxygen_level and self.oxygen_level < 94:
            alerts.append('low_oxygen')
        if self.heart_rate and self.heart_rate > 100:
            alerts.append('tachycardia')
        if self.heart_rate and self.heart_rate < 60:
            alerts.append('bradycardia')
        if self.blood_sugar and self.blood_sugar > 200:
            alerts.append('high_sugar')
        return alerts

    def __repr__(self):
        return f'<PatientVitals Patient:{self.patient_id} Temp:{self.temperature} HR:{self.heart_rate}bpm>'


class MedicationAdministration(db.Model):
    """Track actual medication administration by nurses"""
    __tablename__ = 'medication_administration'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    medicine_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    scheduled_time = db.Column(db.DateTime, nullable=True)
    administered_by_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    administration_status = db.Column(db.String(20), default='Pending')  # Pending, Given, Missed, Delayed
    administration_time = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='medication_records')
    prescription = db.relationship('Prescription', backref='administration_records')
    administered_by = db.relationship('User', backref='administered_medications', foreign_keys=[administered_by_nurse_id])

    __table_args__ = (
        db.Index('idx_med_admin_patient', 'patient_id'),
        db.Index('idx_med_admin_status', 'administration_status'),
    )

    def __repr__(self):
        return f'<MedAdmin {self.medicine_name} - {self.administration_status}>'


class NurseHandover(db.Model):
    """Shift handover notes between nurses"""
    __tablename__ = 'nurse_handovers'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    from_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    pending_tasks = db.Column(db.Text)
    urgent_concerns = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='handovers')
    from_nurse = db.relationship('User', foreign_keys=[from_nurse_id], backref='handovers_given')
    to_nurse = db.relationship('User', foreign_keys=[to_nurse_id], backref='handovers_received')

    def __repr__(self):
        return f'<NurseHandover Patient:{self.patient_id} From:{self.from_nurse_id}>'


class NursePatientAssignment(db.Model):
    """Tracks which nurse has claimed/taken which patient.
    Once a nurse claims a patient, other nurses cannot see that patient."""
    __tablename__ = 'nurse_patient_assignments'

    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    released_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    nurse = db.relationship('User', backref='patient_assignments', foreign_keys=[nurse_id])
    patient = db.relationship('Patient', backref='nurse_assignments')

    __table_args__ = (
        db.Index('idx_npa_nurse_active', 'nurse_id', 'is_active'),
        db.Index('idx_npa_patient_active', 'patient_id', 'is_active'),
    )

    def __repr__(self):
        return f'<NursePatientAssignment Nurse:{self.nurse_id} Patient:{self.patient_id}>'


class FrontpageDoctor(db.Model):
    """Doctors displayed on the hospital homepage — managed by Host"""
    __tablename__ = 'frontpage_doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    specialization = db.Column(db.String(200), nullable=False)
    qualification = db.Column(db.String(300))
    experience_years = db.Column(db.Integer)
    photo_path = db.Column(db.String(500))
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FrontpageDoctor {self.name}>'


class SymptomLog(db.Model):
    """Log of patient-reported symptoms for tracking and analysis"""
    __tablename__ = 'symptom_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    symptom_name = db.Column(db.String(100), nullable=False)  # headache, fever, etc.
    severity = db.Column(db.Integer)  # 1-10 scale
    notes = db.Column(db.Text)  # Additional patient notes
    
    # Extracted from chatbot conversations automatically
    from_chatbot = db.Column(db.Boolean, default=False)
    
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='symptom_logs')
    
    def __repr__(self):
        return f'<SymptomLog P:{self.patient_id} {self.symptom_name}>'


class PharmacyOrder(db.Model):
    """Pharmacy dispensing orders linked to prescriptions"""
    __tablename__ = 'pharmacy_orders'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)

    medicine_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    dosage = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Pending')  # Pending, Dispensed
    notes = db.Column(db.Text)

    dispensed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='pharmacy_orders')
    doctor = db.relationship('Doctor', backref='pharmacy_orders')
    prescription = db.relationship('Prescription', backref='pharmacy_orders')

    def __repr__(self):
        return f'<PharmacyOrder {self.medicine_name} P:{self.patient_id}>'


class PharmacySale(db.Model):
    """Actual medicine sale ledger created when pharmacy dispenses medicines."""
    __tablename__ = 'pharmacy_sales'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    pharmacy_order_id = db.Column(db.Integer, db.ForeignKey('pharmacy_orders.id'), nullable=True)
    medicine_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0.0)
    sold_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref=db.backref('pharmacy_sales', lazy='dynamic'))
    pharmacy_order = db.relationship('PharmacyOrder', backref=db.backref('sale_records', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_pharmacy_sales_patient_date', 'patient_id', 'sold_at'),
    )

    def __repr__(self):
        return f'<PharmacySale {self.medicine_name} P:{self.patient_id}>'


class ReceptionQueue(db.Model):
    """Reception queue / token management for walk-in and appointment patients"""
    __tablename__ = 'reception_queue'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)

    token_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Waiting')  # Waiting, Accepted by Reception, Sent to Doctor, Accepted by Doctor, Rejected by Doctor, In Consultation, Completed, Cancelled
    visit_reason = db.Column(db.String(255))
    patient_type = db.Column(db.String(50), default='Walk-in')  # Walk-in, Appointment, Check-in

    # Link to original appointment or check-in
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    checkin_id = db.Column(db.Integer, db.ForeignKey('patient_checkins.id'), nullable=True)

    # Reception handling
    reception_status = db.Column(db.String(50), default='Pending')  # Pending, Accepted, Rejected
    reception_notes = db.Column(db.Text, nullable=True)
    accepted_by_reception_at = db.Column(db.DateTime, nullable=True)

    # Doctor handling
    doctor_status = db.Column(db.String(50), default='Pending')  # Pending, Accepted, Cancelled
    doctor_notes = db.Column(db.Text, nullable=True)
    sent_to_doctor_at = db.Column(db.DateTime, nullable=True)
    doctor_responded_at = db.Column(db.DateTime, nullable=True)

    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)
    consultation_time = db.Column(db.DateTime, nullable=True)
    completed_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='queue_entries')
    doctor = db.relationship('Doctor', backref='queue_entries')
    appointment = db.relationship('Appointment', backref='queue_entry', uselist=False)
    checkin = db.relationship('PatientCheckIn', backref='queue_entry', uselist=False)

    def __repr__(self):
        return f'<ReceptionQueue Token:{self.token_number} P:{self.patient_id}>'


class PatientConsent(db.Model):
    """Patient Legal Consent & Digital Signatures (HIPAA/GDPR)"""
    __tablename__ = 'patient_consents'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    form_type = db.Column(db.String(100), nullable=False) # e.g., "HIPAA Privacy Notice", "General Treatment Consent"
    consent_text = db.Column(db.Text, nullable=False) # Snapshot of what they agreed to
    signature_base64 = db.Column(db.Text, nullable=False) # Base64 encoded PNG of the canvas signature
    ip_address = db.Column(db.String(50))
    signed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='consents')
    
    def __repr__(self):
        return f'<Consent {self.form_type} P:{self.patient_id}>'

