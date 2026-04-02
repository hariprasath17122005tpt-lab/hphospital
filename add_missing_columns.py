#!/usr/bin/env python
"""
Add all missing columns to patients table
"""
import os
import sys
from app import create_app, db
from sqlalchemy import text, inspect

def add_missing_columns():
    """Add all missing columns to patients table"""
    app = create_app('development')
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = {col['name']: col for col in inspector.get_columns('patients')}
            
            print("Current columns in patients table:")
            for col_name in sorted(columns.keys()):
                print(f"  ✓ {col_name}")
            
            # Define required columns for Patient model
            required_columns = {
                'uhid': "VARCHAR(20) UNIQUE",
                'is_walk_in': "BOOLEAN DEFAULT 0",
            }
            
            missing_columns = {}
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    missing_columns[col_name] = col_def
            
            if not missing_columns:
                print("\n✅ All required columns exist!")
                return True
            
            print(f"\nMissing {len(missing_columns)} column(s):")
            for col_name in missing_columns:
                print(f"  ✗ {col_name}")
            
            print("\nAdding missing columns...")
            with db.engine.connect() as connection:
                for col_name, col_def in missing_columns.items():
                    try:
                        sql = f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}"
                        print(f"  Running: {sql}")
                        connection.execute(text(sql))
                        connection.commit()
                        print(f"  ✅ Added {col_name}")
                    except Exception as e:
                        print(f"  ⚠️  {col_name}: {str(e)[:100]}")
            
            # Now populate missing values
            print("\nPopulating default values...")
            
            # Populate uhid if still needed
            with db.engine.connect() as connection:
                result = connection.execute(text(
                    "SELECT COUNT(*) as cnt FROM patients WHERE uhid IS NULL"
                ))
                null_count = result.scalar()
                
                if null_count > 0:
                    print(f"  Populating uhid for {null_count} patients...")
                    
                    from app.services.patient_service import PatientService
                    from app.models.models import Patient
                    
                    patients = Patient.query.filter(Patient.uhid.is_(None)).all()
                    for idx, patient in enumerate(patients, 1):
                        uhid = PatientService.generate_uhid()
                        patient.uhid = uhid
                        print(f"    {idx}. Patient #{patient.id}: {uhid}")
                    
                    db.session.commit()
                    print(f"  ✅ Updated uhid values")
                else:
                    print(f"  ✓ All patients have uhid")
            
            print("\n" + "="*70)
            print("✅ PATIENTS TABLE SCHEMA UPDATED SUCCESSFULLY")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = add_missing_columns()
    sys.exit(0 if success else 1)
