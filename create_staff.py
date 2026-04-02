from app import create_app, db
from app.models.models import User, UserRole, Hospital
from werkzeug.security import generate_password_hash
import traceback

try:
    app = create_app()
    with app.app_context():
        default_hospital = Hospital.query.first()
        h_id = default_hospital.id if default_hospital else None

        staff_accounts = [
            ('lab_staff', 'password123', UserRole.LAB_STAFF),
            ('pharmacy_staff', 'password123', UserRole.PHARMACIST),
            ('reception_staff', 'password123', UserRole.RECEPTIONIST)
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
                print(f'{username} already exists (password updated)')
        
        db.session.commit()
        print('Done.')
except Exception as e:
    print('ERROR:', e)
    traceback.print_exc()
