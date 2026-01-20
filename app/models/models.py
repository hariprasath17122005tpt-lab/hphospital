from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"  # Hospital Admin
    HOST = "HOST"    # Super Admin / Host
    NURSE = "NURSE"
    LAB_STAFF = "LAB_STAFF"

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
    
    def __repr__(self):
        return f'<User {self.username}>'


class Patient(db.Model):
    """Patient profile model"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Float)  # in kg
    height = db.Column(db.Float)  # in cm
    blood_type = db.Column(db.String(10))
    medical_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
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
        return f'<Patient {self.first_name} {self.last_name}>'


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
    medicines = db.Column(db.Text, nullable=False)  # JSON format or text
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
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
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
    
    test_name = db.Column(db.String(100), nullable=False)
    result_value = db.Column(db.String(255))
    reference_range = db.Column(db.String(100))
    unit = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Pending')  # Pending, Completed
    notes = db.Column(db.Text)
    
    report_file = db.Column(db.String(255))  # Path to PDF/Image
    critical_alert = db.Column(db.Boolean, default=False)
    conducted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='lab_reports')
    doctor = db.relationship('Doctor', backref='lab_reports')

    def __repr__(self):
        return f'<LabReport {self.test_name}>'


class Medicine(db.Model):
    """Pharmacy Inventory Model"""
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float)
    expiry_date = db.Column(db.String(20)) # Storing as YYYY-MM for simplicity or Date
    batch_number = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))
    
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
    """Nurse Task Management"""
    __tablename__ = 'nurse_tasks'

    id = db.Column(db.Integer, primary_key=True)
    assigned_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    patient_name = db.Column(db.String(100)) # Can link to Patient model ideally, keeping simple for now
    bed_number = db.Column(db.String(20))
    task_description = db.Column(db.String(255), nullable=False)
    due_time = db.Column(db.String(50)) # Keeping as string for "10:00 AM" simplicity or DateTime
    status = db.Column(db.String(20), default='Pending') # Pending, Completed
    priority = db.Column(db.String(20)) # High, Medium, Low

    def __repr__(self):
        return f'<Task {self.task_description}>'


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
        return f'<Progress P:{self.patient_id} V:{self.video_id}>'
