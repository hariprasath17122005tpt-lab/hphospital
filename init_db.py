"""
Database Initialization Script
Run this to set up and populate the database with sample data
"""

from app import create_app, db
from app.models.models import User, Patient, Doctor, UserRole, Hospital
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text

def init_database():
    """Initialize database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        # Create all tables if they don't exist
        print("📊 Creating tables if they don't exist...")
        db.create_all()
        print("✅ Tables ready!")
        
        # Check if default hospital already exists
        default_hospital = Hospital.query.first()
        if default_hospital:
            print(f"\n🏥 Hospital already exists: {default_hospital.name}")
        else:
            # Create Default Hospital only if it doesn't exist
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
            db.session.commit()
            db.session.commit()
        
        print("\n" + "="*50)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("="*50)
        print(f"\n🏥 Hospital: {default_hospital.name}")
        print("\n🚀 Patient Portal is ready!")
        print("  • Visit: http://localhost:5000/patient/register")
        print("  • Or: http://localhost:5000/patient/login")
        print("="*50)

if __name__ == '__main__':
    init_database()

