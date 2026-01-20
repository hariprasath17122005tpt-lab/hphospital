"""
Database Initialization Script
Run this to set up and populate the database with sample data
"""

from app import create_app, db
from app.models.models import User, Patient, Doctor, UserRole, Hospital
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def init_database():
    """Initialize database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables (WARNING: This will delete all data)
        print("🗑️  Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("📊 Creating all tables...")
        db.create_all()
        print("✅ Tables created successfully!")
        
        # Create Default Hospital
        print("\n🏥 Creating Default Hospital...")
        default_hospital = Hospital(
            name="City General Hospital",
            domain_prefix="city-general",
            contact_email="admin@citygeneral.com",
            address="123 Medic Lane, Healthy City"
        )
        db.session.add(default_hospital)
        db.session.flush()
        print(f"  ✓ Hospital: {default_hospital.name}")
        
        # Create sample patients
        print("\n👥 Adding sample patients...")
        
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
                'weight': 75,
                'height': 180,
            },
            {
                'username': 'sarah_patient',
                'email': 'sarah@patient.com',
                'password': 'password123',
                'first_name': 'Sarah',
                'last_name': 'Smith',
                'age': 28,
                'gender': 'Female',
                'phone': '555-0102',
                'weight': 62,
                'height': 165,
            },
            {
                'username': 'mike_patient',
                'email': 'mike@patient.com',
                'password': 'password123',
                'first_name': 'Michael',
                'last_name': 'Johnson',
                'age': 45,
                'gender': 'Male',
                'phone': '555-0103',
                'weight': 85,
                'height': 175,
            }
        ]
        
        patients = []
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
                weight=patient_data['weight'],
                height=patient_data['height']
            )
            db.session.add(patient)
            patients.append(patient)
            print(f"  ✓ Patient: {patient_data['first_name']} {patient_data['last_name']}")
        
        # Create sample doctors
        print("\n👨‍⚕️  Adding sample doctors...")
        
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
                'experience_years': 10,
            },
            {
                'username': 'dr_williams',
                'email': 'dr.williams@hospital.com',
                'password': 'password123',
                'first_name': 'Emily',
                'last_name': 'Williams',
                'license_number': 'MD005678',
                'specialization': 'Endocrinology',
                'qualification': 'MBBS, MD (Endocrinology)',
                'phone': '555-1002',
                'experience_years': 8,
            },
            {
                'username': 'dr_brown',
                'email': 'dr.brown@hospital.com',
                'password': 'password123',
                'first_name': 'James',
                'last_name': 'Brown',
                'license_number': 'MD009012',
                'specialization': 'General Practice',
                'qualification': 'MBBS',
                'phone': '555-1003',
                'experience_years': 12,
            }
        ]
        
        doctors = []
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
                experience_years=doctor_data['experience_years'],
                verified=True  # Auto-verified for testing
            )
            db.session.add(doctor)
            doctors.append(doctor)
            print(f"  ✓ Doctor: Dr. {doctor_data['first_name']} {doctor_data['last_name']} ({doctor_data['specialization']})")
        
        db.session.commit()
        
        print("\n" + "="*50)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("="*50)
        
        print("\n📋 Sample Credentials for Testing:")
        print("\n👥 PATIENT ACCOUNTS:")
        for patient_data in sample_patients:
            print(f"  • Username: {patient_data['username']}")
            print(f"    Password: {patient_data['password']}")
            print()
        
        print("👨‍⚕️  DOCTOR ACCOUNTS:")
        for doctor_data in sample_doctors:
            print(f"  • Username: {doctor_data['username']}")
            print(f"    Password: {doctor_data['password']}")
            print()
        
        print("\n🚀 Next Steps:")
        print("  1. Run: python run.py")
        print("  2. Visit: http://localhost:5000")
        print("  3. Login with one of the credentials above")
        print("="*50)

if __name__ == '__main__':
    init_database()
