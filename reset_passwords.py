"""Reset patient passwords to 'password123' for all patient accounts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('.env.production' if os.path.exists('.env.production') else '.env')

from app import create_app
from app.models.models import db, User, UserRole
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    patients = User.query.filter_by(role=UserRole.PATIENT).all()
    for p in patients:
        p.password_hash = generate_password_hash('password123')
        print(f"Reset password for: {p.username} (id={p.id}) -> password123")
    db.session.commit()
    print(f"\nDone! All {len(patients)} patient passwords set to: password123")
