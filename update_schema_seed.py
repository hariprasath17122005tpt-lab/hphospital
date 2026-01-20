
from app import create_app, db
from app.models.models import User, UserRole, Doctor, Patient, AuditLog, SystemSettings
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect, text, or_

app = create_app()

with app.app_context():
    print("--- STARTING DB UPDATE (MySQL Safe) ---")
    
    try:
        with db.engine.connect() as conn:
            # 0. Update User Role Enum in MySQL
            print("Updating User Role Enum to include HOST, NURSE, LAB_STAFF...")
            conn.execute(text("ALTER TABLE users MODIFY COLUMN role ENUM('PATIENT', 'DOCTOR', 'ADMIN', 'HOST', 'NURSE', 'LAB_STAFF') NOT NULL"))
            
            # 1. Add Columns to Doctor Table using Inspector
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('doctors')]
            
            if 'is_suspended' not in columns:
                print("Adding is_suspended column to doctors...")
                conn.execute(text("ALTER TABLE doctors ADD COLUMN is_suspended BOOLEAN DEFAULT 0"))
            
            if 'suspension_reason' not in columns:
                print("Adding suspension_reason column to doctors...")
                conn.execute(text("ALTER TABLE doctors ADD COLUMN suspension_reason TEXT"))

            if 'is_deleted' not in columns:
                print("Adding is_deleted column to doctors...")
                conn.execute(text("ALTER TABLE doctors ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))

            # Check SystemSettings columns (if table exists)
            try:
                sys_columns = [col['name'] for col in inspector.get_columns('system_settings')]
                if 'disclaimer_text' not in sys_columns:
                    print("Adding disclaimer_text to system_settings...")
                    conn.execute(text("ALTER TABLE system_settings ADD COLUMN disclaimer_text TEXT"))
            except:
                pass # Table might not exist yet, created in db.create_all()
        
        print("Schema columns check complete.")
                
    except Exception as e:
        print(f"Error updating schema (might be already updated): {e}")

    # 2. Create New Tables
    db.create_all()
    print("All tables checked/created.")

    # 3. Seed Users
    users_to_seed = [
        {"username": "hari", "email": "hari@hospital.ai", "password": "hari123", "role": UserRole.PATIENT},
        {"username": "doctor", "email": "doctor@hospital.ai", "password": "doctor123", "role": UserRole.DOCTOR},
        {"username": "host", "email": "host@hospital.ai", "password": "host95972", "role": UserRole.HOST},
    ]

    for u_data in users_to_seed:
        # Check by username OR email
        user = User.query.filter(or_(User.username == u_data['username'], User.email == u_data['email'])).first()
        hashed_pw = generate_password_hash(u_data['password'])
        
        if not user:
            print(f"Creating user {u_data['username']}...")
            try:
                user = User(
                    username=u_data['username'],
                    email=u_data['email'],
                    password_hash=hashed_pw,
                    role=u_data['role']
                )
                db.session.add(user)
                db.session.flush()

                if u_data['role'] == UserRole.PATIENT:
                    if not Patient.query.filter_by(user_id=user.id).first():
                        patient = Patient(
                            user_id=user.id,
                            first_name="Hari",
                            last_name="Prasad",
                            age=30,
                            gender="Male",
                            phone="+919876543210"
                        )
                        db.session.add(patient)
                
                elif u_data['role'] == UserRole.DOCTOR:
                    if not Doctor.query.filter_by(user_id=user.id).first():
                        doctor = Doctor(
                            user_id=user.id,
                            first_name="Doctor",
                            last_name="Strange",
                            specialization="Cardiology",
                            license_number="LIC-HOST-TEST",
                            verified=False
                        )
                        db.session.add(doctor)
                
                db.session.commit()
                print(f"User {u_data['username']} created successfully.")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating user {u_data['username']}: {e}")
        
        else:
            # Update password and role
            try:
                user.password_hash = hashed_pw
                user.role = u_data['role']
                # Update username if it matched by email but username is different (edge case)
                user.username = u_data['username'] 
                db.session.commit()
                print(f"Updated user {u_data['username']} password & role.")
            except Exception as e:
                print(f"Error updating user {u_data['username']}: {e}")

    # 4. Initialize Settings
    settings = SystemSettings.query.first()
    if not settings:
        settings = SystemSettings(emergency_mode=False, maintenance_mode=False, ai_enabled=True)
        db.session.add(settings)
        db.session.commit()
        print("Initialized System Settings.")

    print("--- SEEDING COMPLETE ---")
