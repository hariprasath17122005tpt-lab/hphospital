#!/usr/bin/env python
"""
Startup script using Waitress WSGI server
This avoids Flask's native server issues on Windows
"""
import os
import sys
import ssl

# Fix SSL issues
try:
    _create_unverified_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_context

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

from app import create_app, db
from app.models.models import User, Patient, Doctor, UserRole, Hospital, SystemSettings
from werkzeug.security import generate_password_hash
from waitress import serve
from sqlalchemy import text

app = create_app(os.getenv('FLASK_ENV', 'development'))

def ensure_health_data_schema():
    """Ensure HealthData columns exist (handles older SQLite schema)."""
    columns_to_add = [
        ("temperature", "FLOAT"),
        ("diabetes_risk", "FLOAT"),
        ("heart_disease_risk", "FLOAT"),
        ("hypertension_risk", "FLOAT"),
        ("bmi", "FLOAT"),
        ("bmi_category", "VARCHAR(50)"),
        ("smoking", "BOOLEAN"),
        ("alcohol", "BOOLEAN"),
        ("exercise_minutes", "INTEGER"),
        ("sleep_hours", "FLOAT"),
        ("stress_level", "VARCHAR(50)")
    ]

    with app.app_context():
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(
                    text(f"ALTER TABLE health_data ADD COLUMN {col_name} {col_type}")
                )
                db.session.commit()
                print(f"[OK] Added health_data.{col_name}")
            except Exception:
                db.session.rollback()

def ensure_lab_reports_schema():
    """Ensure LabReport columns exist (handles older SQLite schema)."""
    columns_to_add = [
        ("remarks", "TEXT"),
        ("updated_at", "DATETIME"),
    ]

    with app.app_context():
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(
                    text(f"ALTER TABLE lab_reports ADD COLUMN {col_name} {col_type}")
                )
                db.session.commit()
                print(f"[OK] Added lab_reports.{col_name}")
            except Exception:
                db.session.rollback()

def ensure_doctors_schema():
    """Ensure Doctor status columns exist (handles older schema)."""
    columns_to_add = [
        ("is_suspended", "BOOLEAN DEFAULT 0"),
        ("suspension_reason", "TEXT"),
        ("is_deleted", "BOOLEAN DEFAULT 0"),
    ]

    with app.app_context():
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(
                    text(f"ALTER TABLE doctors ADD COLUMN {col_name} {col_type}")
                )
                db.session.commit()
                print(f"[OK] Added doctors.{col_name}")
            except Exception:
                db.session.rollback()

def ensure_reception_queue_schema():
    """Ensure ReceptionQueue has the new workflow columns."""
    columns_to_add = [
        ("appointment_id", "INTEGER"),
        ("checkin_id", "INTEGER"),
        ("reception_status", "VARCHAR(50) DEFAULT 'Pending'"),
        ("reception_notes", "TEXT"),
        ("accepted_by_reception_at", "DATETIME"),
        ("doctor_status", "VARCHAR(50) DEFAULT 'Pending'"),
        ("doctor_notes", "TEXT"),
        ("sent_to_doctor_at", "DATETIME"),
        ("doctor_responded_at", "DATETIME"),
    ]

    with app.app_context():
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(
                    text(f"ALTER TABLE reception_queue ADD COLUMN {col_name} {col_type}")
                )
                db.session.commit()
                print(f"[OK] Added reception_queue.{col_name}")
            except Exception:
                db.session.rollback()

def ensure_prescriptions_schema():
    """Ensure Prescription columns exist for legacy databases."""
    columns_to_add = [
        ("diagnosis", "TEXT"),
        ("notes", "TEXT"),
    ]

    with app.app_context():
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(
                    text(f"ALTER TABLE prescriptions ADD COLUMN {col_name} {col_type}")
                )
                db.session.commit()
                print(f"[OK] Added prescriptions.{col_name}")
            except Exception:
                db.session.rollback()

def init_database_if_empty():
    """Initialize database with sample data if it's empty (for deployment)"""
    with app.app_context():
        # Check if database is already initialized
        if Hospital.query.first() is not None:
            print("[OK] Database already initialized.")
            return
        
        print("[WAIT] Initializing database with sample data...")
        
        # Create Default Hospital
        default_hospital = Hospital(
            name="City General Hospital",
            domain_prefix="city-general",
            contact_email="admin@citygeneral.com",
            address="123 Medic Lane, Healthy City"
        )
        db.session.add(default_hospital)
        db.session.flush()
        print(f"  [DONE] Hospital: {default_hospital.name}")
        
        # Create System Settings
        settings = SystemSettings(
            emergency_mode=False,
            maintenance_mode=False,
            ai_enabled=True
        )
        db.session.add(settings)
        
        # Create HOST Admin user
        host_user = User(
            username='admin',
            email='admin@hospital.com',
            password_hash=generate_password_hash('admin123'),
            role=UserRole.HOST,
            hospital_id=default_hospital.id
        )
        db.session.add(host_user)
        print("  [DONE] Host Admin: admin / admin123")
        
        # Create sample patients
        sample_patients = [
            {
                'username': 'john_patient',
                'email': 'john@patient.com',
                'password': 'password123',
                'first_name': 'John',
                'last_name': 'Doe',
                'age': 35,
                'gender': 'Male',
                'phone': '555-0101',
            },
            {
                'username': 'patient',
                'email': 'patient@test.com',
                'password': 'patient123',
                'first_name': 'Test',
                'last_name': 'Patient',
                'age': 30,
                'gender': 'Male',
                'phone': '555-0100',
            },
        ]
        
        for patient_data in sample_patients:
            user = User(
                username=patient_data['username'],
                email=patient_data['email'],
                password_hash=generate_password_hash(patient_data['password']),
                role=UserRole.PATIENT,
                hospital_id=default_hospital.id
            )
            db.session.add(user)
            db.session.flush()
            
            patient = Patient(
                user_id=user.id,
                hospital_id=default_hospital.id,
                first_name=patient_data['first_name'],
                last_name=patient_data['last_name'],
                age=patient_data['age'],
                gender=patient_data['gender'],
                phone=patient_data['phone'],
            )
            db.session.add(patient)
            print(f"  [DONE] Patient: {patient_data['username']} / {patient_data['password']}")
        
        # Create sample doctors
        sample_doctors = [
            {
                'username': 'dr_smith',
                'email': 'dr.smith@hospital.com',
                'password': 'password123',
                'first_name': 'Robert',
                'last_name': 'Smith',
                'license_number': 'MD001234',
                'specialization': 'Cardiology',
                'qualification': 'MBBS, MD (Cardiology)',
                'phone': '555-1001',
            },
            {
                'username': 'doctor',
                'email': 'doctor@test.com',
                'password': 'doctor123',
                'first_name': 'Test',
                'last_name': 'Doctor',
                'license_number': 'MD000000',
                'specialization': 'General Practice',
                'qualification': 'MBBS',
                'phone': '555-1000',
            },
        ]
        
        for doctor_data in sample_doctors:
            user = User(
                username=doctor_data['username'],
                email=doctor_data['email'],
                password_hash=generate_password_hash(doctor_data['password']),
                role=UserRole.DOCTOR,
                hospital_id=default_hospital.id
            )
            db.session.add(user)
            db.session.flush()
            
            doctor = Doctor(
                user_id=user.id,
                hospital_id=default_hospital.id,
                first_name=doctor_data['first_name'],
                last_name=doctor_data['last_name'],
                license_number=doctor_data['license_number'],
                specialization=doctor_data['specialization'],
                qualification=doctor_data['qualification'],
                phone=doctor_data['phone'],
                verified=True
            )
            db.session.add(doctor)
            print(f"  [DONE] Doctor: {doctor_data['username']} / {doctor_data['password']}")
        
        db.session.commit()
        print("[OK] Database initialization complete!")

@app.shell_context_processor
def make_shell_context():
    return {'db': db}

if __name__ == '__main__':
    print("=" * 70)
    print("HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 70)
    print("Server running at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    try:
        ensure_health_data_schema()
        ensure_lab_reports_schema()
        ensure_doctors_schema()
        ensure_reception_queue_schema()
        ensure_prescriptions_schema()
        # Initialize database with sample data if empty (for deployment)
        init_database_if_empty()
        
        print("\nStarting Waitress server...\n")
        serve(app, host='0.0.0.0', port=5000, _quiet=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
