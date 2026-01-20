from app import create_app
from app.models.models import db

app = create_app()
with app.app_context():
    try:
        # First update the data values
        db.session.execute(db.text("UPDATE users SET role = 'PATIENT' WHERE role = 'patient'"))
        db.session.execute(db.text("UPDATE users SET role = 'DOCTOR' WHERE role = 'doctor'"))
        db.session.execute(db.text("UPDATE users SET role = 'ADMIN' WHERE role = 'admin'"))
        db.session.commit()
        
        # Then alter the enum definition
        db.session.execute(db.text("ALTER TABLE users MODIFY COLUMN role ENUM('PATIENT', 'DOCTOR', 'ADMIN') NOT NULL"))
        db.session.commit()
        print("✅ Successfully updated MySQL enum definition and values to uppercase")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
