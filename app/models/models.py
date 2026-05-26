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
    allergy_history = db.Column(db.Text)       # Detailed allergy records
    chronic_conditions = db.Column(db.Text)    # Long-term chronic conditions
    family_history = db.Column(db.Text)        # Family medical history
    current_medications = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    phone = db.Column(db.String(20), index=True)  # Index for search
    aadhaar = db.Column(db.String(12), nullable=True, index=True)  # Aadhaar number (optional)
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
    """Centralized patient visit ledger for OP, IP, LAB, and PHARMACY touchpoints."""
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_type = db.Column(db.String(20), nullable=False)  # OP / IP / LAB / PHARMACY
    visit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    notes = db.Column(db.Text)
    token_number = db.Column(db.Integer, nullable=True)
    visit_status = db.Column(db.String(30), default='Active')  # Active / Completed / Cancelled
    visit_reason = db.Column(db.String(255), nullable=True)
    consultation_type = db.Column(db.String(50), nullable=True)  # New / Follow-up / Special
    qr_token = db.Column(db.String(255), unique=True, nullable=True, index=True)  # Unique QR token per visit
    qr_image_path = db.Column(db.String(255), nullable=True)  # Path to generated QR image
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
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultations.id'), nullable=True)

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
    route = db.Column(db.String(50))              # Oral, IV, IM, Topical, etc.
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    instruction = db.Column(db.Text)
    food_relation = db.Column(db.String(100))     # Before Food, After Food, etc.
    special_instruction = db.Column(db.Text)      # Additional special instructions

    prescription = db.relationship('Prescription', backref=db.backref('medicine_items', lazy='dynamic'))


class Consultation(db.Model):
    """Doctor consultation record — one per visit/encounter. Separates visit data from permanent patient history."""
    __tablename__ = 'consultations'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Current visit data
    chief_complaint = db.Column(db.Text)
    present_condition = db.Column(db.Text)
    past_medication = db.Column(db.Text)
    examination_notes = db.Column(db.Text)
    provisional_diagnosis = db.Column(db.Text)
    final_diagnosis = db.Column(db.Text)
    clinical_notes = db.Column(db.Text)          # Additional clinical notes

    # Vitals recorded during consultation
    vitals_bp_systolic = db.Column(db.Integer)
    vitals_bp_diastolic = db.Column(db.Integer)
    vitals_pulse = db.Column(db.Integer)
    vitals_temperature = db.Column(db.Float)
    vitals_spo2 = db.Column(db.Integer)
    vitals_respiratory_rate = db.Column(db.Integer)
    vitals_weight = db.Column(db.Float)
    vitals_grbs = db.Column(db.Float)           # Blood sugar / GRBS

    # Treatment plan
    treatment_plan = db.Column(db.Text)
    advice = db.Column(db.Text)
    diet_advice = db.Column(db.Text)
    rest_activity_advice = db.Column(db.Text)
    investigation_suggested = db.Column(db.Text)
    procedures_advised = db.Column(db.Text)      # Procedures / interventions advised
    followup_date = db.Column(db.Date, nullable=True)

    # Doctor internal notes (not visible to patient)
    doctor_internal_notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('consultations', lazy='dynamic', order_by='Consultation.created_at.desc()'))
    doctor = db.relationship('Doctor', backref=db.backref('consultations', lazy='dynamic'))
    prescriptions = db.relationship('Prescription', backref='consultation', lazy='dynamic',
                                    foreign_keys='Prescription.consultation_id')

    __table_args__ = (
        db.Index('idx_consultations_patient_date', 'patient_id', 'created_at'),
    )

    def __repr__(self):
        return f'<Consultation {self.id} P:{self.patient_id} D:{self.doctor_id}>'


class PatientMedicalHistory(db.Model):
    """Structured medical history entries — multiple entries per patient for granular tracking."""
    __tablename__ = 'patient_medical_history'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    condition = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # medical / allergy / chronic / family
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('structured_history', lazy='dynamic',
                                                             order_by='PatientMedicalHistory.created_at.desc()'))

    def __repr__(self):
        return f'<PatientMedicalHistory {self.type}: {self.condition}>'


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
    """Patient Billing and Invoices — supports OP and IP billing."""
    __tablename__ = 'billings'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)
    admission_id = db.Column(db.Integer, nullable=True)  # FK to ip_admissions (added after table exists)

    billing_type = db.Column(db.String(10), default='OP')  # OP / IP
    bill_number = db.Column(db.String(30), nullable=True, index=True)  # BILL-YYYY-XXXX
    amount = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    grand_total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Unpaid')  # Unpaid / Paid / Partial / Cancelled / Draft
    description = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50))  # Cash / Card / UPI / Insurance / Mixed
    paid_at = db.Column(db.DateTime)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='billings')
    doctor = db.relationship('Doctor', backref='billings')
    appointment = db.relationship('Appointment', backref='billing')
    items = db.relationship('BillItem', backref='bill', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Billing {self.id} {self.billing_type} - {self.status}>'


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
    # Link to IP medication order (nullable for backward compat with OP records)
    ip_medication_id = db.Column(db.Integer, db.ForeignKey('ip_medications.id'), nullable=True, index=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=True, index=True)
    medicine_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    route = db.Column(db.String(50))
    frequency = db.Column(db.String(100))
    scheduled_time = db.Column(db.DateTime, nullable=True)
    administered_by_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    administration_status = db.Column(db.String(20), default='Pending')  # Pending, Given, Missed, Delayed
    administration_time = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='medication_records')
    prescription = db.relationship('Prescription', backref='administration_records')
    ip_medication = db.relationship('IPMedication', backref=db.backref('administration_records', lazy='dynamic'))
    admission = db.relationship('IPAdmission', backref=db.backref('medication_administrations', lazy='dynamic'))
    administered_by = db.relationship('User', backref='administered_medications', foreign_keys=[administered_by_nurse_id])

    __table_args__ = (
        db.Index('idx_med_admin_patient', 'patient_id'),
        db.Index('idx_med_admin_status', 'administration_status'),
        db.Index('idx_med_admin_ip_med', 'ip_medication_id'),
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


# ═══════════════════════════════════════════════════════════════════════════════
# IP ADMISSION, BILL ITEMS, DISCHARGE SUMMARY, CONSULTATION FEES
# ═══════════════════════════════════════════════════════════════════════════════

class IPAdmission(db.Model):
    """Inpatient admission record — tracks full IP stay from admission to discharge."""
    __tablename__ = 'ip_admissions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)

    ip_number = db.Column(db.String(30), unique=True, nullable=False, index=True)  # IP-YYYY-XXXX
    admission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    discharge_date = db.Column(db.DateTime, nullable=True)
    admission_reason = db.Column(db.Text)
    admission_status = db.Column(db.String(30), default='Admitted')  # Admitted / Discharged / LAMA / Expired / Transferred

    # Ward/Bed
    ward_type = db.Column(db.String(50), nullable=True)   # General / ICU / HDU / Private / Semi-Private
    bed_id = db.Column(db.Integer, db.ForeignKey('beds.id'), nullable=True)
    room_number = db.Column(db.String(20), nullable=True)

    # Clinical
    provisional_diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('admissions', lazy='dynamic', order_by='IPAdmission.admission_date.desc()'))
    doctor = db.relationship('Doctor', backref=db.backref('ip_admissions', lazy='dynamic'))
    bed = db.relationship('Bed', backref='admission')
    discharge_summary = db.relationship('DischargeSummary', backref='admission', uselist=False)

    @property
    def length_of_stay(self):
        end = self.discharge_date or datetime.utcnow()
        return (end - self.admission_date).days if self.admission_date else 0

    def __repr__(self):
        return f'<IPAdmission {self.ip_number} P:{self.patient_id} {self.admission_status}>'


class BillItem(db.Model):
    """Individual line item in a bill — supports dynamic hospital charges."""
    __tablename__ = 'bill_items'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('billings.id'), nullable=False, index=True)

    item_name = db.Column(db.String(255), nullable=False)
    item_category = db.Column(db.String(100), nullable=True)  # Consultation / Procedure / Nursing / Room / Oxygen / etc.
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BillItem {self.item_name} qty:{self.quantity} total:{self.total_price}>'


class DischargeSummary(db.Model):
    """IP discharge summary — complete clinical record at discharge."""
    __tablename__ = 'discharge_summaries'

    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=False, unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)

    # Clinical content
    presenting_complaints = db.Column(db.Text)
    history_of_illness = db.Column(db.Text)
    past_history = db.Column(db.Text)
    examination_findings = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    investigations = db.Column(db.Text)
    course_in_hospital = db.Column(db.Text)
    treatment_given = db.Column(db.Text)
    procedures_done = db.Column(db.Text)
    condition_at_discharge = db.Column(db.String(100))  # Stable / Improved / Unchanged / Critical
    medicines_at_discharge = db.Column(db.Text)
    discharge_advice = db.Column(db.Text)
    diet_advice = db.Column(db.Text)
    follow_up_instructions = db.Column(db.Text)
    follow_up_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('discharge_summaries', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('discharge_summaries', lazy='dynamic'))

    def __repr__(self):
        return f'<DischargeSummary Adm:{self.admission_id} P:{self.patient_id}>'


class ConsultationFee(db.Model):
    """Configurable consultation fees per doctor or hospital-wide."""
    __tablename__ = 'consultation_fees'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)  # NULL = hospital default
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    consultation_type = db.Column(db.String(50), nullable=False)  # New / Follow-up / Special / Emergency
    fee_amount = db.Column(db.Float, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('Doctor', backref='fee_config')

    def __repr__(self):
        return f'<ConsultationFee {self.consultation_type}: {self.fee_amount}>'


# ═══════════════════════════════════════════════════════════════════════════════
# IP MEDICATIONS & PROGRESS NOTES (Doctor IP Workflow)
# ═══════════════════════════════════════════════════════════════════════════════

class IPMedication(db.Model):
    """Ongoing medication order for an IP patient — distinct from OP PrescriptionMedicine."""
    __tablename__ = 'ip_medications'

    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)

    # Prescription batch — groups medicines prescribed at the same time
    order_batch = db.Column(db.String(40), nullable=True, index=True)  # e.g. "RX-2026-0001"
    order_time = db.Column(db.DateTime, default=datetime.utcnow)       # when this batch was ordered

    medicine_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    route = db.Column(db.String(50))             # Oral, IV, IM, SC, Topical, Nebulization
    frequency = db.Column(db.String(100))        # BD, TDS, QID, SOS, STAT, OD, HS
    duration = db.Column(db.String(100))
    special_instruction = db.Column(db.Text)
    food_relation = db.Column(db.String(50))     # Before Food, After Food, With Food

    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active')  # Active / Stopped / Completed
    stopped_reason = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    admission = db.relationship('IPAdmission', backref=db.backref('medications', lazy='dynamic',
                                order_by='IPMedication.created_at.desc()'))
    patient = db.relationship('Patient', backref=db.backref('ip_medications', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('ip_medications', lazy='dynamic'))

    def to_dict(self):
        d = {
            'id': self.id, 'admission_id': self.admission_id,
            'order_batch': self.order_batch or '',
            'order_time': self.order_time.strftime('%d %b %Y, %I:%M %p') if self.order_time else '',
            'order_time_short': self.order_time.strftime('%d %b %H:%M') if self.order_time else '',
            'medicine_name': self.medicine_name, 'dosage': self.dosage or '',
            'route': self.route or '', 'frequency': self.frequency or '',
            'duration': self.duration or '', 'special_instruction': self.special_instruction or '',
            'food_relation': self.food_relation or '',
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else '',
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else '',
            'status': self.status, 'stopped_reason': self.stopped_reason or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }
        # Include downstream status from nurse + pharmacy
        disp = self.dispensing_records.first()
        d['pharmacy_status'] = disp.dispensing_status if disp else 'Pending'
        d['stock_status'] = disp.stock_status if disp else 'Pending'
        admin = self.administration_records.order_by(MedicationAdministration.created_at.desc()).first()
        d['nurse_status'] = admin.administration_status if admin else 'Pending'
        d['nurse_remarks'] = admin.remarks if admin else ''
        return d

    def __repr__(self):
        return f'<IPMedication {self.medicine_name} [{self.status}] Adm:{self.admission_id}>'


class IPProgressNote(db.Model):
    """Daily progress note / round note for an admitted IP patient (SOAP format)."""
    __tablename__ = 'ip_progress_notes'

    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)

    note_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    note_time = db.Column(db.DateTime, default=datetime.utcnow)

    # SOAP format
    subjective = db.Column(db.Text)     # Patient complaints / how they feel
    objective = db.Column(db.Text)      # Examination findings
    assessment = db.Column(db.Text)     # Doctor assessment / diagnosis
    plan = db.Column(db.Text)           # Treatment plan changes

    # General
    clinical_notes = db.Column(db.Text)
    instructions_to_nurse = db.Column(db.Text)
    procedure_notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    admission = db.relationship('IPAdmission', backref=db.backref('progress_notes', lazy='dynamic',
                                order_by='IPProgressNote.note_time.desc()'))
    patient = db.relationship('Patient', backref=db.backref('ip_progress_notes', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('ip_progress_notes', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id, 'admission_id': self.admission_id,
            'note_date': self.note_date.strftime('%Y-%m-%d') if self.note_date else '',
            'note_time': self.note_time.strftime('%Y-%m-%d %H:%M') if self.note_time else '',
            'subjective': self.subjective or '', 'objective': self.objective or '',
            'assessment': self.assessment or '', 'plan': self.plan or '',
            'clinical_notes': self.clinical_notes or '',
            'instructions_to_nurse': self.instructions_to_nurse or '',
            'procedure_notes': self.procedure_notes or '',
            'doctor_name': f"Dr. {self.doctor.first_name} {self.doctor.last_name}" if self.doctor else '',
        }

    def __repr__(self):
        return f'<IPProgressNote {self.note_date} Adm:{self.admission_id}>'


class HospitalCharge(db.Model):
    """Master list of chargeable items — used by billing to pick charges."""
    __tablename__ = 'hospital_charges'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    charge_name = db.Column(db.String(255), nullable=False)
    charge_category = db.Column(db.String(100), nullable=False)  # Consultation / Room / Nursing / Procedure / Oxygen / Ambulance / Misc
    default_price = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<HospitalCharge {self.charge_name}: {self.default_price}>'


class MedicationDispensing(db.Model):
    """Pharmacy dispensing record for an IP medication order."""
    __tablename__ = 'medication_dispensing'

    id = db.Column(db.Integer, primary_key=True)
    ip_medication_id = db.Column(db.Integer, db.ForeignKey('ip_medications.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=False, index=True)
    pharmacist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    medicine_name = db.Column(db.String(255), nullable=False)
    requested_quantity = db.Column(db.String(100))      # e.g. "10 tablets", "3 days supply"
    dispensed_quantity = db.Column(db.String(100))
    unit_price = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, default=0)
    stock_status = db.Column(db.String(30), default='Pending')    # Pending / Available / Partial / Out of Stock
    dispensing_status = db.Column(db.String(30), default='Pending')  # Pending / Dispensed / Partially Dispensed / Not Available
    dispensed_at = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ip_medication = db.relationship('IPMedication', backref=db.backref('dispensing_records', lazy='dynamic'))
    patient = db.relationship('Patient', backref=db.backref('medication_dispensing_records', lazy='dynamic'))
    admission = db.relationship('IPAdmission', backref=db.backref('medication_dispensings', lazy='dynamic'))
    pharmacist = db.relationship('User', backref='dispensed_medications', foreign_keys=[pharmacist_id])

    def __repr__(self):
        return f'<MedicationDispensing {self.medicine_name} [{self.dispensing_status}]>'


# ═══════════════════════════════════════════════════════════════════════════════
# NEW MODULES — OT, Emergency, Insurance, Inventory, Telemedicine, Feedback, Notifications
# ═══════════════════════════════════════════════════════════════════════════════

class OTBooking(db.Model):
    """Operation Theatre Booking & Scheduling"""
    __tablename__ = 'ot_bookings'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)

    surgery_name = db.Column(db.String(255), nullable=False)
    surgery_type = db.Column(db.String(100))  # Major, Minor, Emergency, Day-Care
    ot_room = db.Column(db.String(50))  # OT-1, OT-2, etc.
    scheduled_date = db.Column(db.DateTime, nullable=False, index=True)
    estimated_duration = db.Column(db.Integer)  # minutes
    actual_start = db.Column(db.DateTime, nullable=True)
    actual_end = db.Column(db.DateTime, nullable=True)

    anesthesia_type = db.Column(db.String(100))  # General, Spinal, Local, Epidural
    anesthetist_name = db.Column(db.String(100))
    assistant_surgeon = db.Column(db.String(100))
    scrub_nurse = db.Column(db.String(100))

    pre_op_diagnosis = db.Column(db.Text)
    post_op_diagnosis = db.Column(db.Text)
    procedure_notes = db.Column(db.Text)
    complications = db.Column(db.Text)

    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, In Progress, Completed, Cancelled, Postponed
    priority = db.Column(db.String(20), default='Elective')  # Emergency, Urgent, Elective

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('ot_bookings', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('ot_bookings', lazy='dynamic'))

    def __repr__(self):
        return f'<OTBooking {self.surgery_name} [{self.status}]>'


class EmergencyCase(db.Model):
    """Emergency Department / Triage Cases"""
    __tablename__ = 'emergency_cases'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True, index=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)

    # Triage Info
    triage_level = db.Column(db.String(20), nullable=False)  # Critical, Urgent, Semi-Urgent, Non-Urgent
    triage_color = db.Column(db.String(20))  # Red, Orange, Yellow, Green, Blue
    chief_complaint = db.Column(db.Text, nullable=False)
    arrival_mode = db.Column(db.String(50))  # Walk-in, Ambulance, Referred, Police

    # Patient Info (for unregistered walk-ins)
    patient_name = db.Column(db.String(120))
    patient_age = db.Column(db.Integer)
    patient_gender = db.Column(db.String(20))
    patient_phone = db.Column(db.String(20))

    # Vitals on arrival
    bp_systolic = db.Column(db.Integer)
    bp_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    spo2 = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    gcs_score = db.Column(db.Integer)  # Glasgow Coma Scale (3-15)

    # Management
    attending_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    attending_nurse = db.Column(db.String(100))
    treatment_given = db.Column(db.Text)
    disposition = db.Column(db.String(50))  # Admitted, Discharged, Referred, LAMA, Expired

    status = db.Column(db.String(50), default='Active')  # Active, Stabilized, Admitted, Discharged, Transferred

    arrival_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    stabilized_at = db.Column(db.DateTime, nullable=True)
    discharged_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('emergency_cases', lazy='dynamic'))
    attending_doctor = db.relationship('Doctor', backref=db.backref('emergency_cases', lazy='dynamic'))

    @property
    def wait_time_minutes(self):
        if self.stabilized_at and self.arrival_time:
            return int((self.stabilized_at - self.arrival_time).total_seconds() / 60)
        if self.arrival_time:
            return int((datetime.utcnow() - self.arrival_time).total_seconds() / 60)
        return 0

    def __repr__(self):
        return f'<EmergencyCase {self.triage_level} [{self.status}]>'


class InsurancePolicy(db.Model):
    """Patient Insurance Policies"""
    __tablename__ = 'insurance_policies'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)

    provider_name = db.Column(db.String(200), nullable=False)  # e.g., Star Health, ICICI Lombard
    policy_number = db.Column(db.String(100), nullable=False)
    policy_type = db.Column(db.String(100))  # Individual, Family Floater, Group, Government
    tpa_name = db.Column(db.String(200))  # Third Party Administrator
    tpa_id = db.Column(db.String(100))

    sum_insured = db.Column(db.Float, default=0)
    balance_available = db.Column(db.Float, default=0)
    premium_amount = db.Column(db.Float, default=0)

    valid_from = db.Column(db.Date)
    valid_until = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)

    # Cashless network
    is_cashless_eligible = db.Column(db.Boolean, default=False)
    network_hospital = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('insurance_policies', lazy='dynamic'))

    def __repr__(self):
        return f'<InsurancePolicy {self.provider_name} #{self.policy_number}>'


class InsuranceClaim(db.Model):
    """Insurance Claims Processing"""
    __tablename__ = 'insurance_claims'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('insurance_policies.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('ip_admissions.id'), nullable=True)

    claim_number = db.Column(db.String(100), unique=True)
    claim_type = db.Column(db.String(50))  # Pre-Auth, Cashless, Reimbursement
    claim_amount = db.Column(db.Float, nullable=False)
    approved_amount = db.Column(db.Float, default=0)
    deduction_amount = db.Column(db.Float, default=0)
    deduction_reason = db.Column(db.Text)

    diagnosis = db.Column(db.Text)
    treatment_type = db.Column(db.String(100))
    admission_date = db.Column(db.Date)
    discharge_date = db.Column(db.Date)

    status = db.Column(db.String(50), default='Initiated')  # Initiated, Submitted, Under Review, Approved, Partially Approved, Rejected, Settled
    rejection_reason = db.Column(db.Text)

    submitted_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    settled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = db.relationship('InsurancePolicy', backref=db.backref('claims', lazy='dynamic'))
    patient = db.relationship('Patient', backref=db.backref('insurance_claims', lazy='dynamic'))

    def __repr__(self):
        return f'<InsuranceClaim #{self.claim_number} [{self.status}]>'


class InventoryItem(db.Model):
    """Medical Supplies & Equipment Inventory"""
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)

    item_name = db.Column(db.String(255), nullable=False, index=True)
    item_code = db.Column(db.String(50), unique=True)
    category = db.Column(db.String(100), nullable=False)  # Consumable, Equipment, Surgical, PPE, Linen, Stationery
    sub_category = db.Column(db.String(100))
    unit = db.Column(db.String(50))  # Piece, Box, Pack, Bottle, Roll
    unit_price = db.Column(db.Float, default=0)

    current_stock = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=10)
    maximum_stock = db.Column(db.Integer, default=1000)
    reorder_level = db.Column(db.Integer, default=20)

    location = db.Column(db.String(100))  # Store Room, OT Store, Ward Store, Pharmacy
    supplier = db.Column(db.String(200))
    manufacturer = db.Column(db.String(200))

    last_restocked = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'Out of Stock'
        elif self.current_stock <= self.reorder_level:
            return 'Critical'
        elif self.current_stock <= self.minimum_stock:
            return 'Low'
        return 'Adequate'

    def __repr__(self):
        return f'<InventoryItem {self.item_name}: {self.current_stock}>'


class InventoryTransaction(db.Model):
    """Inventory Stock Movement Transactions"""
    __tablename__ = 'inventory_transactions'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String(50), nullable=False)  # Purchase, Issue, Return, Adjustment, Expired, Damage
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, default=0)
    reference = db.Column(db.String(200))  # PO number, Ward name, etc.
    remarks = db.Column(db.Text)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('InventoryItem', backref=db.backref('transactions', lazy='dynamic'))

    def __repr__(self):
        return f'<InventoryTransaction {self.transaction_type}: {self.quantity}>'


class TelemedicineSession(db.Model):
    """Telemedicine / Video Consultation Sessions"""
    __tablename__ = 'telemedicine_sessions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)

    session_type = db.Column(db.String(50))  # Video, Audio, Chat
    room_id = db.Column(db.String(100), unique=True)  # Unique room identifier
    meeting_link = db.Column(db.String(500))

    scheduled_time = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, default=0)

    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, Waiting, In Progress, Completed, No Show, Cancelled
    consultation_notes = db.Column(db.Text)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)

    patient_rating = db.Column(db.Integer)  # 1-5
    patient_feedback = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('telemedicine_sessions', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('telemedicine_sessions', lazy='dynamic'))

    def __repr__(self):
        return f'<TelemedicineSession {self.session_type} [{self.status}]>'


class PatientFeedback(db.Model):
    """Patient Feedback & Doctor Ratings"""
    __tablename__ = 'patient_feedback'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)

    feedback_type = db.Column(db.String(50))  # Consultation, Facility, Staff, Overall
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text)

    # Specific ratings
    doctor_rating = db.Column(db.Integer)
    staff_rating = db.Column(db.Integer)
    facility_rating = db.Column(db.Integer)
    cleanliness_rating = db.Column(db.Integer)
    wait_time_rating = db.Column(db.Integer)

    would_recommend = db.Column(db.Boolean, default=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)

    response_text = db.Column(db.Text)  # Hospital response
    responded_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('feedback_records', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('feedback_records', lazy='dynamic'))

    def __repr__(self):
        return f'<PatientFeedback {self.rating}* [{self.feedback_type}]>'


class Notification(db.Model):
    """Real-time Notification System"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # appointment, lab_result, prescription, billing, emergency, system
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    icon = db.Column(db.String(50))  # Font Awesome icon class

    action_url = db.Column(db.String(500))  # Link to relevant page
    reference_type = db.Column(db.String(50))  # appointment, prescription, lab_report, etc.
    reference_id = db.Column(db.Integer)

    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.title} [{self.notification_type}]>'


class PatientReferral(db.Model):
    __tablename__ = 'patient_referrals'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    referring_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    referred_to_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    referred_to_department = db.Column(db.String(100))
    referred_to_external = db.Column(db.String(255))  # External hospital name
    referral_type = db.Column(db.String(50))  # Internal, External, Second Opinion
    reason = db.Column(db.Text, nullable=False)
    clinical_notes = db.Column(db.Text)
    urgency = db.Column(db.String(20), default='Routine')  # Routine, Urgent, Emergency
    status = db.Column(db.String(50), default='Pending')  # Pending, Accepted, Completed, Declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    patient = db.relationship('Patient', backref=db.backref('referrals', lazy='dynamic'))
    referring_doctor = db.relationship('Doctor', foreign_keys=[referring_doctor_id], backref='outgoing_referrals')
    referred_doctor = db.relationship('Doctor', foreign_keys=[referred_to_doctor_id], backref='incoming_referrals')


class DutyRoster(db.Model):
    """Staff Duty Roster / Scheduling"""
    __tablename__ = 'duty_roster'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    staff_name = db.Column(db.String(100))
    staff_role = db.Column(db.String(50))  # Doctor, Nurse, Lab, Pharmacy, Reception
    shift = db.Column(db.String(20))  # Morning, Afternoon, Night
    duty_date = db.Column(db.Date, nullable=False, index=True)
    ward = db.Column(db.String(50))  # General, ICU, Emergency, OPD, Pharmacy, Lab
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('User', backref=db.backref('duty_shifts', lazy='dynamic'))

    def __repr__(self):
        return f'<DutyRoster {self.staff_name} {self.shift} {self.duty_date}>'
