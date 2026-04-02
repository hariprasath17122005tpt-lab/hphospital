from app import create_app
from app.models.models import db, Prescription, PrescriptionMedicine
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Attempt to add columns to the prescriptions table safely
    try:
        db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN diagnosis TEXT;"))
    except Exception as e:
        print("Column diagnosis might already exist or error:", e)

    try:
        db.session.execute(text("ALTER TABLE prescriptions ADD COLUMN notes TEXT;"))
    except Exception as e:
        print("Column notes might already exist or error:", e)

    db.session.commit()
    db.create_all()
    print("Database updated for new Prescription Module")
