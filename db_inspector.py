#!/usr/bin/env python3
"""Direct MySQL Inspector - writes results to a file."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('.env.production' if os.path.exists('.env.production') else '.env')

from app import create_app
from app.models.models import db, Prescription
from sqlalchemy import text

app = create_app()

MODEL_COLUMNS = {
    'id':                       'INT AUTO_INCREMENT PRIMARY KEY',
    'patient_id':               'INT NOT NULL',
    'doctor_id':                'INT NOT NULL',
    'appointment_id':           'INT NULL',
    'diagnosis':                'TEXT NULL',
    'notes':                    'TEXT NULL',
    'medicines':                "TEXT NOT NULL DEFAULT '[]'",
    'dosage':                   'TEXT NULL',
    'frequency':                'VARCHAR(200) NULL',
    'duration':                 'VARCHAR(100) NULL',
    'instructions':             'TEXT NULL',
    'diet_recommendations':     'TEXT NULL',
    'exercise_recommendations': 'TEXT NULL',
    'prescribed_at':            'DATETIME NULL DEFAULT CURRENT_TIMESTAMP',
    'expiry_date':              'DATETIME NULL',
    'image_path':               'VARCHAR(255) NULL',
    'is_verified':              'TINYINT(1) NULL DEFAULT 0',
    'refill_requested':         'TINYINT(1) NULL DEFAULT 0',
    'refill_status':            'VARCHAR(50) NULL',
}

output_lines = []

def log(msg):
    output_lines.append(msg)

with app.app_context():
    log("STEP 1: DESCRIBE prescriptions")
    log("-" * 60)
    
    rows = db.session.execute(text("DESCRIBE prescriptions")).fetchall()
    db_columns = {}
    for row in rows:
        field, type_, null_, key_, default_, extra_ = row
        db_columns[field] = type_
        log(f"  {field} | {type_} | null={null_} | default={default_}")

    log("")
    log("STEP 2: Compare")
    log("-" * 60)
    
    db_col_names = set(db_columns.keys())
    orm_col_names = set(MODEL_COLUMNS.keys())
    missing_in_db = orm_col_names - db_col_names
    extra_in_db = db_col_names - orm_col_names

    log(f"MISSING in DB: {sorted(missing_in_db) if missing_in_db else 'NONE'}")
    log(f"Extra in DB: {sorted(extra_in_db) if extra_in_db else 'NONE'}")

    if missing_in_db:
        log("")
        log("STEP 3: Adding missing columns")
        log("-" * 60)
        for col_name in sorted(missing_in_db):
            if col_name == 'id':
                continue
            col_ddl = MODEL_COLUMNS[col_name]
            if 'PRIMARY KEY' in col_ddl:
                continue
            alter_sql = f"ALTER TABLE prescriptions ADD COLUMN `{col_name}` {col_ddl}"
            log(f"  Running: {alter_sql}")
            try:
                db.session.execute(text(alter_sql))
                db.session.commit()
                log(f"  -> OK")
            except Exception as e:
                db.session.rollback()
                log(f"  -> ERROR: {e}")
    
    log("")
    log("STEP 4: Test ORM query")
    log("-" * 60)
    try:
        result = Prescription.query.filter_by(patient_id=2).order_by(
            Prescription.prescribed_at.desc()).limit(1).first()
        log(f"ORM QUERY: SUCCESS -> {result}")
    except Exception as e:
        log(f"ORM QUERY: FAILED -> {e}")

    log("")
    log("STEP 5: Test raw SQL")
    log("-" * 60)
    try:
        row = db.session.execute(text(
            "SELECT id, medicines, dosage, frequency, instructions FROM prescriptions LIMIT 1"
        )).first()
        log(f"RAW SQL: SUCCESS -> {row}")
    except Exception as e:
        db.session.rollback()
        log(f"RAW SQL: FAILED -> {e}")

# Write to file
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_inspect_result.txt')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"Results written to {output_path}")
