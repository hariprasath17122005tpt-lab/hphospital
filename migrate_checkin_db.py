#!/usr/bin/env python3
"""
Database Migration Script - Create PatientCheckIn Table
This script creates the new PatientCheckIn table for Express Check-in feature
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.models import PatientCheckIn

def migrate_database():
    """Migrate database and create new tables"""
    print("=" * 70)
    print("🔄 DATABASE MIGRATION - EXPRESS CHECK-IN FEATURE")
    print("=" * 70)
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n📊 Checking database status...")
            
            # Create all tables
            print("📝 Creating tables...")
            db.create_all()
            
            print("✅ Database migration completed successfully!")
            print("\n📋 Tables created/updated:")
            print("  ✓ PatientCheckIn - Express check-in system")
            
            # Verify the table was created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'patient_checkins' in tables:
                print("\n✅ Verified: 'patient_checkins' table exists")
                columns = inspector.get_columns('patient_checkins')
                print("   Columns:")
                for col in columns:
                    print(f"     - {col['name']}: {col['type']}")
            else:
                print("\n⚠️ Warning: 'patient_checkins' table not found")
                return False
            
            print("\n" + "=" * 70)
            print("🎉 Migration successful! Express Check-in feature ready.")
            print("=" * 70)
            return True
            
        except Exception as e:
            print(f"\n❌ Error during migration: {str(e)}")
            print("=" * 70)
            return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
