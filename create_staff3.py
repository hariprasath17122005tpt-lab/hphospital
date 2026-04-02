from app import create_app, db
from app.models.models import User, UserRole, Hospital
from werkzeug.security import generate_password_hash
from sqlalchemy import text
import traceback

try:
    app = create_app()
    with app.app_context():
        # Update the enum definition in the database
        print("Altering table to update enum...")
        db.session.execute(text("ALTER TABLE users MODIFY COLUMN role ENUM('PATIENT', 'DOCTOR', 'ADMIN', 'HOST', 'LAB_STAFF', 'PHARMACIST', 'RECEPTIONIST') NOT NULL"))
        db.session.commit()
        print("Enum updated.")

        h = Hospital.query.first()
        h_id = h.id if h else None

        staff_accounts = [
            ('lab_demo', 'password123', UserRole.LAB_STAFF),
            ('pharm_demo', 'password123', UserRole.PHARMACIST),
            ('recep_demo', 'password123', UserRole.RECEPTIONIST)
        ]
        
        for username, pwd, role in staff_accounts:
            user = User.query.filter_by(username=username).first()
            if not user:
                new_user = User(
                    username=username,
                    email=username + '@hospital.com',
                    password_hash=generate_password_hash(pwd),
                    role=role,
                    hospital_id=h_id
                )
                db.session.add(new_user)
                print(f'Created {username}')
            else:
                user.password_hash = generate_password_hash(pwd)
                print(f'{username} already exists')
        
        db.session.commit()
        print('Done.')
except Exception as e:
    with open('error3.txt', 'w') as f:
        f.write(traceback.format_exc())
