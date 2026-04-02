#!/usr/bin/env python
"""
Add missing uhid column to patients table
"""
import os
import sys
from app import create_app, db
from sqlalchemy import text, inspect

def add_uhid_column():
    """Add uhid column to patients table if it doesn't exist"""
    app = create_app('development')
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('patients')]
            
            if 'uhid' in columns:
                print("✅ Column 'uhid' already exists in patients table")
                return True
            
            print("Adding 'uhid' column to patients table...")
            
            # Add the uhid column
            with db.engine.connect() as connection:
                # First, add the column as nullable
                connection.execute(text(
                    'ALTER TABLE patients ADD COLUMN uhid VARCHAR(20) UNIQUE'
                ))
                connection.commit()
                print("✅ Column 'uhid' added (nullable)")
            
            # Now populate with PAT-YYYY-XXXX format for existing patients
            print("\nPopulating uhid for existing patients...")
            from app.services.patient_service import PatientService
            from app.models.models import Patient
            
            with db.engine.connect() as connection:
                # Get all patients without uhid
                patients = Patient.query.filter(Patient.uhid.is_(None)).all()
                
                if patients:
                    print(f"Found {len(patients)} patients without uhid")
                    
                    for idx, patient in enumerate(patients, 1):
                        # Generate uhid using the same logic
                        uhid = PatientService.generate_uhid()
                        patient.uhid = uhid
                        print(f"  {idx}. Patient #{patient.id}: {uhid}")
                    
                    db.session.commit()
                    print(f"\n✅ Updated {len(patients)} patients with uhid values")
                else:
                    print("No patients found without uhid")
            
            # Now make the column NOT NULL
            print("\nMaking uhid column NOT NULL...")
            with db.engine.connect() as connection:
                connection.execute(text(
                    'ALTER TABLE patients MODIFY COLUMN uhid VARCHAR(20) NOT NULL UNIQUE'
                ))
                connection.commit()
                print("✅ Column 'uhid' is now NOT NULL and UNIQUE")
            
            print("\n" + "="*70)
            print("✅ PATIENTS TABLE MIGRATION COMPLETE")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = add_uhid_column()
    sys.exit(0 if success else 1)
