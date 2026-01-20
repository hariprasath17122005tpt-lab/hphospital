from app import create_app, db
from sqlalchemy import text

app = create_app()

def update_schema():
    with app.app_context():
        # Prescriptions
        try:
            db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN image_path VARCHAR(255)"))
            print("Added image_path to prescriptions")
        except Exception as e:
            print(f"Skipped prescriptions.image_path: {e}")

        try:
            db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
            print("Added is_verified to prescriptions")
        except Exception as e:
            print(f"Skipped prescriptions.is_verified: {e}")

        try:
            db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN refill_requested BOOLEAN DEFAULT 0"))
            print("Added refill_requested to prescriptions")
        except Exception as e:
            print(f"Skipped prescriptions.refill_requested: {e}")

        try:
            db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN refill_status VARCHAR(50)"))
            print("Added refill_status to prescriptions")
        except Exception as e:
            print(f"Skipped prescriptions.refill_status: {e}")

        # Lab Reports
        try:
            db.session.execute(text("ALTER TABLE lab_reports ADD COLUMN critical_alert BOOLEAN DEFAULT 0"))
            print("Added critical_alert to lab_reports")
        except Exception as e:
            print(f"Skipped lab_reports.critical_alert: {e}")

        # Patient Checkins
        try:
            db.session.execute(text("ALTER TABLE patient_checkins ADD COLUMN qr_code_path VARCHAR(255)"))
            print("Added qr_code_path to patient_checkins")
        except Exception as e:
            print(f"Skipped patient_checkins.qr_code_path: {e}")

        try:
            db.session.execute(text("ALTER TABLE patient_checkins ADD COLUMN estimated_wait_time INTEGER"))
            print("Added estimated_wait_time to patient_checkins")
        except Exception as e:
            print(f"Skipped patient_checkins.estimated_wait_time: {e}")

        db.session.commit()
        
        # Create new tables if they don't exist
        db.create_all()
        print("Ensured all tables exist.")

if __name__ == "__main__":
    update_schema()
