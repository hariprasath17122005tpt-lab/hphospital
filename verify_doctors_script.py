
from app import create_app, db
from app.models.models import Doctor

app = create_app()

with app.app_context():
    print("Checking for pending doctors...")
    pending_doctors = Doctor.query.filter_by(verified=False).all()
    
    if not pending_doctors:
        print("No pending doctors found.")
    else:
        for doctor in pending_doctors:
            print(f"Verifying doctor: {doctor.first_name} {doctor.last_name} (License: {doctor.license_number})")
            doctor.verified = True
        
        db.session.commit()
        print("All pending doctors have been verified successfully.")
