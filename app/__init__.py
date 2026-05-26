import os
import time
import datetime
import threading
from flask import Flask, url_for, redirect, flash, request, jsonify, session
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.routing import BuildError
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import inspect, text
from config import config
from app.models.models import db, User, UserRole

# Flask-Migrate instance (shared so CLI commands work)
migrate = Migrate()

# ── System Settings Cache ──────────────────────────────────────────────────────
# Cache SystemSettings for 60 s to avoid a DB hit on every single request.
_settings_cache = {'data': None, 'expires': 0.0}  # type: ignore[assignment]
_SETTINGS_TTL = 60  # seconds

def _ensure_prescriptions_schema_compat(app):
    """
    Backfill missing columns in legacy `prescriptions` schemas.
    Older bootstrap SQL used different column names than the current ORM model.
    This must cover EVERY column the Prescription ORM model defines.
    """
    # Complete list of columns from the Prescription model in models.py
    expected_columns = {
        'diagnosis': "TEXT",
        'notes': "TEXT",
        'medicines': "TEXT DEFAULT '[]'",
        'dosage': "TEXT",
        'frequency': "VARCHAR(200)",
        'duration': "VARCHAR(100)",
        'instructions': "TEXT",
        'diet_recommendations': "TEXT",
        'exercise_recommendations': "TEXT",
        'prescribed_at': "DATETIME DEFAULT CURRENT_TIMESTAMP",
        'expiry_date': "DATETIME",
        'image_path': "VARCHAR(255)",
        'is_verified': "BOOLEAN DEFAULT 0",
        'refill_requested': "BOOLEAN DEFAULT 0",
        'refill_status': "VARCHAR(50)",
    }

    inspector = inspect(db.engine)
    if 'prescriptions' not in inspector.get_table_names():
        return

    existing_cols = {col['name'] for col in inspector.get_columns('prescriptions')}
    added_any = False

    for col_name, col_sql in expected_columns.items():
        if col_name in existing_cols:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE prescriptions ADD COLUMN `{col_name}` {col_sql}"))
            db.session.commit()   # commit after each ADD so one failure doesn't block the rest
            added_any = True
            app.logger.info("Added missing prescriptions.%s column", col_name)
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding missing prescriptions.%s column", col_name)

    # Backfill from legacy schema names where present.
    # Re-read columns because we may have just added some.
    try:
        refreshed_cols = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}

        if 'medicines' in refreshed_cols and 'medicine_name' in existing_cols:
            db.session.execute(text(
                "UPDATE prescriptions SET medicines = medicine_name "
                "WHERE (medicines IS NULL OR medicines = '') AND medicine_name IS NOT NULL"
            ))
        if 'medicines' in refreshed_cols:
            db.session.execute(text(
                "UPDATE prescriptions SET medicines = '[]' "
                "WHERE medicines IS NULL OR medicines = ''"
            ))

        if 'duration' in refreshed_cols and 'duration_days' in existing_cols:
            db.session.execute(text(
                "UPDATE prescriptions SET duration = CONCAT(duration_days, ' days') "
                "WHERE (duration IS NULL OR duration = '') AND duration_days IS NOT NULL"
            ))

        if 'expiry_date' in refreshed_cols and 'expires_at' in existing_cols:
            db.session.execute(text(
                "UPDATE prescriptions SET expiry_date = expires_at "
                "WHERE expiry_date IS NULL AND expires_at IS NOT NULL"
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed while backfilling legacy prescriptions columns")

    # Make legacy columns that are NOT in the ORM nullable / defaulted so they
    # don't block new INSERTs (the ORM won't include them in statements).
    dialect = db.engine.dialect.name.lower()
    if dialect in ('mysql', 'mariadb'):
        legacy_alters = {
            'medicine_name': "ALTER TABLE prescriptions MODIFY COLUMN `medicine_name` VARCHAR(255) NULL DEFAULT NULL",
            'duration_days': "ALTER TABLE prescriptions MODIFY COLUMN `duration_days` INT NULL DEFAULT NULL",
            'expires_at':    "ALTER TABLE prescriptions MODIFY COLUMN `expires_at` DATETIME NULL DEFAULT NULL",
        }
        refreshed_cols = {c['name'] for c in inspect(db.engine).get_columns('prescriptions')}
        for col_name, alter_sql in legacy_alters.items():
            if col_name not in refreshed_cols:
                continue
            try:
                db.session.execute(text(alter_sql))
                db.session.commit()
                app.logger.info("Made legacy prescriptions.%s nullable", col_name)
            except Exception:
                db.session.rollback()
                # Column may already be nullable or type mismatch – safe to ignore


def _ensure_health_data_schema_compat(app):
    """
    Backfill missing columns in legacy `health_data` schemas.
    Some old DBs were created before vitals/risk extensions were added.
    """
    expected_columns = {
        'systolic_bp': "INTEGER",
        'diastolic_bp': "INTEGER",
        'fasting_sugar': "FLOAT",
        'random_sugar': "FLOAT",
        'heart_rate': "INTEGER",
        'ecg_slope': "VARCHAR(50)",
        'st_depression': "FLOAT",
        'temperature': "FLOAT",
        'symptoms': "TEXT",
        'diabetes_risk': "FLOAT",
        'heart_disease_risk': "FLOAT",
        'hypertension_risk': "FLOAT",
        'bmi': "FLOAT",
        'bmi_category': "VARCHAR(50)",
        'smoking': "BOOLEAN",
        'alcohol': "BOOLEAN",
        'exercise_minutes': "INTEGER",
        'sleep_hours': "FLOAT",
        'stress_level': "VARCHAR(50)",
        'recorded_at': "DATETIME DEFAULT CURRENT_TIMESTAMP",
    }

    inspector = inspect(db.engine)
    if 'health_data' not in inspector.get_table_names():
        return

    existing_cols = {col['name'] for col in inspector.get_columns('health_data')}
    for col_name, col_sql in expected_columns.items():
        if col_name in existing_cols:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE health_data ADD COLUMN `{col_name}` {col_sql}"))
            db.session.commit()
            app.logger.info("Added missing health_data.%s column", col_name)
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding missing health_data.%s column", col_name)


def _ensure_users_role_schema_compat(app):
    """
    Align users.role storage with current UserRole values.
    Handles legacy lowercase values and old MySQL ENUM definitions.
    """
    inspector = inspect(db.engine)
    if 'users' not in inspector.get_table_names():
        return

    cols = {c['name']: c for c in inspector.get_columns('users')}
    if 'role' not in cols:
        return

    valid_roles = [r.value for r in UserRole]
    dialect = db.engine.dialect.name.lower()

    try:
        # Normalize common legacy lowercase records first.
        for role in valid_roles:
            db.session.execute(
                text("UPDATE users SET role = :upper_role WHERE role = :lower_role"),
                {'upper_role': role, 'lower_role': role.lower()}
            )
        # Handle deprecated NURSE role by converting to LAB_STAFF
        db.session.execute(
            text("UPDATE users SET role = 'LAB_STAFF' WHERE role = 'NURSE'")
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed normalizing legacy users.role values")

    # MySQL: force enum to include every currently supported role value.
    if dialect in ('mysql', 'mariadb'):
        enum_sql = ", ".join([f"'{r}'" for r in valid_roles])
        alter_sql = f"ALTER TABLE users MODIFY COLUMN `role` ENUM({enum_sql}) NOT NULL"
        try:
            db.session.execute(text(alter_sql))
            db.session.commit()
            app.logger.info("Ensured users.role ENUM includes all current UserRole values")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed updating users.role ENUM definition")


def _ensure_new_modules_schema_compat(app):
    """
    Backfill missing columns in new module tables (OT, Emergency, Insurance,
    Inventory, Telemedicine, Feedback, Notifications) if they were created
    by an older schema or partial db.create_all().
    """
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    # Map of table -> {column_name: SQL_type}
    new_table_columns = {
        'notifications': {
            'priority': "VARCHAR(20) DEFAULT 'normal'",
            'icon': "VARCHAR(50)",
            'action_url': "VARCHAR(500)",
            'reference_type': "VARCHAR(50)",
            'reference_id': "INTEGER",
            'is_read': "BOOLEAN DEFAULT 0",
            'read_at': "DATETIME",
            'notification_type': "VARCHAR(50)",
        },
        'ot_bookings': {
            'priority': "VARCHAR(20) DEFAULT 'Elective'",
            'actual_start': "DATETIME",
            'actual_end': "DATETIME",
            'anesthesia_type': "VARCHAR(100)",
            'anesthetist_name': "VARCHAR(100)",
            'assistant_surgeon': "VARCHAR(100)",
            'scrub_nurse': "VARCHAR(100)",
            'pre_op_diagnosis': "TEXT",
            'post_op_diagnosis': "TEXT",
            'procedure_notes': "TEXT",
            'complications': "TEXT",
        },
        'emergency_cases': {
            'gcs_score': "INTEGER",
            'disposition': "VARCHAR(50)",
            'stabilized_at': "DATETIME",
            'discharged_at': "DATETIME",
            'triage_color': "VARCHAR(20)",
        },
        'insurance_claims': {
            'deduction_amount': "FLOAT DEFAULT 0",
            'deduction_reason': "TEXT",
            'rejection_reason': "TEXT",
            'submitted_at': "DATETIME",
            'approved_at': "DATETIME",
            'settled_at': "DATETIME",
        },
        'inventory_items': {
            'reorder_level': "INTEGER DEFAULT 20",
            'maximum_stock': "INTEGER DEFAULT 1000",
            'last_restocked': "DATETIME",
            'expiry_date': "DATE",
        },
        'telemedicine_sessions': {
            'duration_minutes': "INTEGER DEFAULT 0",
            'consultation_notes': "TEXT",
            'patient_rating': "INTEGER",
            'patient_feedback': "TEXT",
        },
        'patient_feedback': {
            'cleanliness_rating': "INTEGER",
            'wait_time_rating': "INTEGER",
            'would_recommend': "BOOLEAN DEFAULT 1",
            'is_anonymous': "BOOLEAN DEFAULT 0",
            'is_published': "BOOLEAN DEFAULT 1",
            'response_text': "TEXT",
            'responded_at': "DATETIME",
        },
    }

    for table_name, columns in new_table_columns.items():
        if table_name not in table_names:
            continue
        existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
        for col_name, col_sql in columns.items():
            if col_name in existing_cols:
                continue
            try:
                db.session.execute(text(
                    f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_sql}"
                ))
                db.session.commit()
                app.logger.info("Added missing %s.%s column", table_name, col_name)
            except Exception:
                db.session.rollback()


def _ensure_billing_doctor_nullable(app):
    """
    Walk-in lab bills have no referring doctor; billings.doctor_id must be nullable.
    MySQL/MariaDB only — SQLite test DBs typically recreate tables from models.
    """
    dialect = db.engine.dialect.name.lower()
    if dialect not in ('mysql', 'mariadb'):
        return
    inspector = inspect(db.engine)
    if 'billings' not in inspector.get_table_names():
        return
    try:
        db.session.execute(text(
            "ALTER TABLE billings MODIFY COLUMN doctor_id INT NULL"
        ))
        db.session.commit()
        app.logger.info("Ensured billings.doctor_id allows NULL for walk-in lab billing")
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not alter billings.doctor_id to NULL (may already be nullable)")


def _ensure_patients_schema_compat(app):
    """
    Backfill missing columns in legacy `patients` schemas.
    Walk-in upgrade added uhid/is_walk_in and older deployments may not have them.
    """
    inspector = inspect(db.engine)
    if 'patients' not in inspector.get_table_names():
        return

    dialect = db.engine.dialect.name.lower()
    cols = {c['name']: c for c in inspector.get_columns('patients')}
    indexes = {i.get('name') for i in inspector.get_indexes('patients')}
    unique_cols = {c.get('column_names', [None])[0] for c in inspector.get_unique_constraints('patients')}

    if 'uhid' not in cols:
        try:
            # Add nullable first; we backfill and tighten constraints afterward.
            db.session.execute(text("ALTER TABLE patients ADD COLUMN `uhid` VARCHAR(20) NULL"))
            db.session.commit()
            app.logger.info("Added missing patients.uhid column")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding patients.uhid column")

    if 'is_walk_in' not in cols:
        try:
            db.session.execute(text("ALTER TABLE patients ADD COLUMN `is_walk_in` BOOLEAN DEFAULT 0"))
            db.session.commit()
            app.logger.info("Added missing patients.is_walk_in column")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding patients.is_walk_in column")

    if 'name' not in cols:
        try:
            db.session.execute(text("ALTER TABLE patients ADD COLUMN `name` VARCHAR(120) NULL"))
            db.session.commit()
            app.logger.info("Added missing patients.name column")
        except Exception as e:
            db.session.rollback()
            if 'duplicate column name' not in str(e).lower():
                app.logger.exception("Failed adding patients.name column")

    if 'date_of_birth' not in cols:
        try:
            db.session.execute(text("ALTER TABLE patients ADD COLUMN `date_of_birth` DATE NULL"))
            db.session.commit()
            app.logger.info("Added missing patients.date_of_birth column")
        except Exception as e:
            db.session.rollback()
            if 'duplicate column name' not in str(e).lower():
                app.logger.exception("Failed adding patients.date_of_birth column")

    # Refresh schema snapshot after potential adds.
    cols = {c['name']: c for c in inspect(db.engine).get_columns('patients')}
    indexes = {i.get('name') for i in inspect(db.engine).get_indexes('patients')}
    unique_cols = {c.get('column_names', [None])[0] for c in inspect(db.engine).get_unique_constraints('patients')}

    # Populate missing UHIDs safely through service logic.
    if 'uhid' in cols:
        try:
            from app.models.models import Patient
            from app.services.patient_service import PatientService

            missing = Patient.query.filter(
                db.or_(Patient.uhid.is_(None), Patient.uhid == '')
            ).order_by(Patient.id.asc()).all()
            if missing:
                for patient in missing:
                    patient.uhid = PatientService.generate_uhid()
                db.session.commit()
                app.logger.info("Backfilled UHID for %s patients", len(missing))

            # Backfill canonical `name` from existing split fields.
            missing_name = Patient.query.filter(
                db.or_(Patient.name.is_(None), Patient.name == '')
            ).order_by(Patient.id.asc()).all()
            if missing_name:
                for patient in missing_name:
                    patient.name = f"{patient.first_name or ''} {patient.last_name or ''}".strip() or f"Patient {patient.id}"
                db.session.commit()
                app.logger.info("Backfilled name for %s patients", len(missing_name))
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed backfilling patients.uhid values")

    # user_id should be nullable to support walk-in patients.
    if 'user_id' in cols and (cols['user_id'].get('nullable') is False) and dialect in ('mysql', 'mariadb'):
        try:
            db.session.execute(text("ALTER TABLE patients MODIFY COLUMN `user_id` INT NULL"))
            db.session.commit()
            app.logger.info("Ensured patients.user_id allows NULL")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed setting patients.user_id to NULL")

    # Ensure useful lookup index and uniqueness for UHID.
    if 'uhid' in cols and 'idx_uhid' not in indexes:
        try:
            db.session.execute(text("CREATE INDEX idx_uhid ON patients (uhid)"))
            db.session.commit()
            app.logger.info("Added patients.uhid index")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding patients.uhid index")

    if 'uhid' in cols and ('uhid' not in unique_cols) and ('uq_patients_uhid' not in indexes):
        try:
            db.session.execute(text("CREATE UNIQUE INDEX uq_patients_uhid ON patients (uhid)"))
            db.session.commit()
            app.logger.info("Added patients.uhid unique index")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding patients.uhid unique index")

    # Tighten to NOT NULL on MySQL-like engines once backfilled.
    if 'uhid' in cols and dialect in ('mysql', 'mariadb') and cols['uhid'].get('nullable') is True:
        try:
            db.session.execute(text("ALTER TABLE patients MODIFY COLUMN `uhid` VARCHAR(20) NOT NULL"))
            db.session.commit()
            app.logger.info("Ensured patients.uhid is NOT NULL")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed setting patients.uhid to NOT NULL")

    # Ensure canonical name is NOT NULL for reliable identity across modules.
    cols = {c['name']: c for c in inspect(db.engine).get_columns('patients')}
    if 'name' in cols and dialect in ('mysql', 'mariadb') and cols['name'].get('nullable') is True:
        try:
            db.session.execute(text("UPDATE patients SET name = CONCAT(COALESCE(first_name,''), ' ', COALESCE(last_name,'')) WHERE name IS NULL OR name = ''"))
            db.session.execute(text("ALTER TABLE patients MODIFY COLUMN `name` VARCHAR(120) NOT NULL"))
            db.session.commit()
            app.logger.info("Ensured patients.name is NOT NULL")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed setting patients.name to NOT NULL")


def _ensure_medicines_schema_compat(app):
    """
    Align medicines table with bulk management model fields.
    """
    inspector = inspect(db.engine)
    if 'medicines' not in inspector.get_table_names():
        return

    cols = {c['name']: c for c in inspector.get_columns('medicines')}
    dialect = db.engine.dialect.name.lower()

    expected_columns = {
        'name': "VARCHAR(255) NOT NULL",
        'brand': "VARCHAR(255) NULL",
        'category': "VARCHAR(100) NULL",
        'price': "FLOAT NULL",
        'stock': "INT DEFAULT 0",
        'supplier': "VARCHAR(255) NULL",
        'created_at': "DATETIME DEFAULT CURRENT_TIMESTAMP",
    }

    for col_name, col_sql in expected_columns.items():
        if col_name in cols:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE medicines ADD COLUMN `{col_name}` {col_sql}"))
            db.session.commit()
            app.logger.info("Added missing medicines.%s column", col_name)
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed adding medicines.%s column", col_name)

    # Backfill price from legacy unit_price if table came from older schema.
    cols = {c['name']: c for c in inspect(db.engine).get_columns('medicines')}
    if 'price' in cols and 'unit_price' in cols:
        try:
            db.session.execute(text(
                "UPDATE medicines SET price = unit_price WHERE price IS NULL AND unit_price IS NOT NULL"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed backfilling medicines.price from unit_price")

    if dialect in ('mysql', 'mariadb'):
        try:
            db.session.execute(text(
                "CREATE UNIQUE INDEX unique_medicine ON medicines (name, brand)"
            ))
            db.session.commit()
            app.logger.info("Ensured unique_medicine index exists")
        except Exception:
            db.session.rollback()
            # Likely already exists.


def _ensure_patient_history_schema_compat(app):
    """
    Create and align history-related tables/columns used by the centralized patient timeline.
    """
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name.lower()
    tables = set(inspector.get_table_names())

    if 'lab_reports' in tables:
        lab_report_cols = {c['name'] for c in inspector.get_columns('lab_reports')}
        if 'file_path' not in lab_report_cols:
            try:
                db.session.execute(text("ALTER TABLE lab_reports ADD COLUMN `file_path` VARCHAR(500) NULL"))
                db.session.commit()
                app.logger.info("Added missing lab_reports.file_path column")
            except Exception:
                db.session.rollback()
                app.logger.exception("Failed adding lab_reports.file_path column")

    if 'visits' not in tables:
        try:
            db.session.execute(text("""
                CREATE TABLE visits (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    patient_id INTEGER NOT NULL,
                    visit_type VARCHAR(20) NOT NULL,
                    visit_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    doctor_id INTEGER NULL,
                    notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_visits_patient_id (patient_id),
                    INDEX idx_visits_patient_date (patient_id, visit_date)
                )
            """))
            db.session.commit()
            app.logger.info("Created visits table for patient history")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating visits table")

    # Ensure QR columns exist on visits table
    if 'visits' in tables or 'visits' in set(inspector.get_table_names()):
        visit_cols = {c['name'] for c in inspector.get_columns('visits')}
        for col_name, col_def in [
            ('qr_token', 'VARCHAR(255) NULL UNIQUE'),
            ('qr_image_path', 'VARCHAR(255) NULL'),
        ]:
            if col_name not in visit_cols:
                try:
                    db.session.execute(text(f"ALTER TABLE visits ADD COLUMN `{col_name}` {col_def}"))
                    db.session.commit()
                    app.logger.info(f"Added visits.{col_name} column")
                except Exception:
                    db.session.rollback()
                    app.logger.exception(f"Failed adding visits.{col_name}")

    if 'pharmacy_sales' not in tables:
        try:
            db.session.execute(text("""
                CREATE TABLE pharmacy_sales (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    patient_id INTEGER NOT NULL,
                    pharmacy_order_id INTEGER NULL,
                    medicine_name VARCHAR(200) NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    price FLOAT DEFAULT 0,
                    sold_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT NULL,
                    INDEX idx_pharmacy_sales_patient_id (patient_id),
                    INDEX idx_pharmacy_sales_patient_date (patient_id, sold_at)
                )
            """))
            db.session.commit()
            app.logger.info("Created pharmacy_sales table for patient history")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating pharmacy_sales table")

    refreshed = inspect(db.engine)
    for table_name, index_name, ddl in (
        ('prescriptions', 'idx_prescriptions_patient_id', "CREATE INDEX idx_prescriptions_patient_id ON prescriptions (patient_id)"),
        ('lab_orders', 'idx_lab_orders_patient_id', "CREATE INDEX idx_lab_orders_patient_id ON lab_orders (patient_id)"),
        ('lab_reports', 'idx_lab_reports_patient_id', "CREATE INDEX idx_lab_reports_patient_id ON lab_reports (patient_id)"),
        ('pharmacy_orders', 'idx_pharmacy_orders_patient_id', "CREATE INDEX idx_pharmacy_orders_patient_id ON pharmacy_orders (patient_id)"),
    ):
        if table_name not in refreshed.get_table_names():
            continue
        index_names = {i.get('name') for i in refreshed.get_indexes(table_name)}
        if index_name in index_names:
            continue
        try:
            db.session.execute(text(ddl))
            db.session.commit()
            app.logger.info("Ensured %s exists", index_name)
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating index %s", index_name)


def _repair_incomplete_patients(app):
    """Fix patients that were created without name or uhid (e.g. Google OAuth)."""
    with app.app_context():
        try:
            from app.models.models import Patient, db
            broken = Patient.query.filter(
                db.or_(Patient.name.is_(None), Patient.name == '',
                       Patient.uhid.is_(None), Patient.uhid == '')
            ).all()
            if not broken:
                return
            from app.services.patient_service import PatientService
            fixed = 0
            for p in broken:
                if not p.uhid:
                    try:
                        p.uhid = PatientService.generate_uhid()
                    except Exception:
                        p.uhid = f"PAT-FIX-{p.id}"
                if not p.name or not p.name.strip():
                    parts = [p.first_name or '', p.last_name or '']
                    p.name = ' '.join(pt for pt in parts if pt).strip() or f"Patient-{p.id}"
                fixed += 1
            if fixed:
                db.session.commit()
                app.logger.info("Repaired %d patients with missing name/uhid", fixed)
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to repair incomplete patients")


def _ensure_ip_billing_schema_compat(app):
    """
    Create ip_admissions, bill_items, discharge_summaries, consultation_fees,
    hospital_charges tables. Extend patients with aadhaar, visits with token/status,
    billings with new columns.
    """
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name.lower()
    tables = set(inspector.get_table_names())
    auto_inc = "AUTO_INCREMENT" if dialect in ('mysql', 'mariadb') else ""

    def _safe_add(table, col, sql):
        try:
            db.session.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {sql}"))
            db.session.commit()
            app.logger.info("Added %s.%s", table, col)
        except Exception:
            db.session.rollback()

    def _cols(table):
        return {c['name'] for c in inspect(db.engine).get_columns(table)}

    # ── patients.aadhaar ─────────────────────────────────────────────────────
    if 'patients' in tables:
        pc = _cols('patients')
        if 'aadhaar' not in pc:
            _safe_add('patients', 'aadhaar', 'VARCHAR(12) NULL')

    # ── visits: token_number, visit_status, visit_reason, consultation_type ──
    if 'visits' in tables:
        vc = _cols('visits')
        for col, sql in {
            'token_number': 'INTEGER NULL',
            'visit_status': "VARCHAR(30) DEFAULT 'Active'",
            'visit_reason': 'VARCHAR(255) NULL',
            'consultation_type': 'VARCHAR(50) NULL',
        }.items():
            if col not in vc:
                _safe_add('visits', col, sql)

    # ── billings: new columns ────────────────────────────────────────────────
    if 'billings' in tables:
        bc = _cols('billings')
        for col, sql in {
            'visit_id': 'INTEGER NULL',
            'admission_id': 'INTEGER NULL',
            'billing_type': "VARCHAR(10) DEFAULT 'OP'",
            'bill_number': 'VARCHAR(30) NULL',
            'subtotal': 'FLOAT DEFAULT 0',
            'discount': 'FLOAT DEFAULT 0',
            'tax': 'FLOAT DEFAULT 0',
            'grand_total': 'FLOAT DEFAULT 0',
            'notes': 'TEXT NULL',
            'updated_at': 'DATETIME NULL',
        }.items():
            if col not in bc:
                _safe_add('billings', col, sql)

    # ── ip_admissions ────────────────────────────────────────────────────────
    if 'ip_admissions' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE ip_admissions (
                    id INTEGER PRIMARY KEY {auto_inc},
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    visit_id INTEGER NULL,
                    ip_number VARCHAR(30) NOT NULL UNIQUE,
                    admission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    discharge_date DATETIME NULL,
                    admission_reason TEXT NULL,
                    admission_status VARCHAR(30) DEFAULT 'Admitted',
                    ward_type VARCHAR(50) NULL,
                    bed_id INTEGER NULL,
                    room_number VARCHAR(20) NULL,
                    provisional_diagnosis TEXT NULL,
                    notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ipa_patient (patient_id),
                    INDEX idx_ipa_status (admission_status),
                    INDEX idx_ipa_ip_number (ip_number)
                )
            """))
            db.session.commit()
            app.logger.info("Created ip_admissions table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating ip_admissions")

    # ── bill_items ───────────────────────────────────────────────────────────
    if 'bill_items' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE bill_items (
                    id INTEGER PRIMARY KEY {auto_inc},
                    bill_id INTEGER NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    item_category VARCHAR(100) NULL,
                    quantity INTEGER DEFAULT 1,
                    unit_price FLOAT DEFAULT 0,
                    total_price FLOAT DEFAULT 0,
                    remarks TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_bi_bill (bill_id)
                )
            """))
            db.session.commit()
            app.logger.info("Created bill_items table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating bill_items")

    # ── discharge_summaries ──────────────────────────────────────────────────
    if 'discharge_summaries' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE discharge_summaries (
                    id INTEGER PRIMARY KEY {auto_inc},
                    admission_id INTEGER NOT NULL UNIQUE,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    presenting_complaints TEXT NULL,
                    history_of_illness TEXT NULL,
                    past_history TEXT NULL,
                    examination_findings TEXT NULL,
                    diagnosis TEXT NULL,
                    investigations TEXT NULL,
                    course_in_hospital TEXT NULL,
                    treatment_given TEXT NULL,
                    procedures_done TEXT NULL,
                    condition_at_discharge VARCHAR(100) NULL,
                    medicines_at_discharge TEXT NULL,
                    discharge_advice TEXT NULL,
                    diet_advice TEXT NULL,
                    follow_up_instructions TEXT NULL,
                    follow_up_date DATE NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ds_patient (patient_id),
                    INDEX idx_ds_admission (admission_id)
                )
            """))
            db.session.commit()
            app.logger.info("Created discharge_summaries table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating discharge_summaries")

    # ── consultation_fees ────────────────────────────────────────────────────
    if 'consultation_fees' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE consultation_fees (
                    id INTEGER PRIMARY KEY {auto_inc},
                    doctor_id INTEGER NULL,
                    hospital_id INTEGER NULL,
                    consultation_type VARCHAR(50) NOT NULL,
                    fee_amount FLOAT NOT NULL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            app.logger.info("Created consultation_fees table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating consultation_fees")

    # Seed consultation fees if empty
    try:
        fee_count = db.session.execute(text("SELECT COUNT(*) FROM consultation_fees")).scalar()
        if fee_count == 0:
            for ctype, fee in [('New', 500), ('Follow-up', 300), ('Special', 1000), ('Emergency', 800)]:
                db.session.execute(text(
                    "INSERT INTO consultation_fees (consultation_type, fee_amount, is_active) VALUES (:t, :f, 1)"
                ), {'t': ctype, 'f': fee})
            db.session.commit()
            app.logger.info("Seeded default consultation fees")
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed seeding consultation_fees")

    # ── hospital_charges (master charge list) ────────────────────────────────
    if 'hospital_charges' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE hospital_charges (
                    id INTEGER PRIMARY KEY {auto_inc},
                    hospital_id INTEGER NULL,
                    charge_name VARCHAR(255) NOT NULL,
                    charge_category VARCHAR(100) NOT NULL,
                    default_price FLOAT DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            app.logger.info("Created hospital_charges table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating hospital_charges")

    # Seed hospital charges from seed_charges_v3.sql if table is empty
    try:
        charge_count = db.session.execute(text("SELECT COUNT(*) FROM hospital_charges")).scalar()
        if charge_count == 0:
            import re as _re
            _seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'seed_charges_v3.sql')
            if os.path.exists(_seed_path):
                with open(_seed_path, 'r', encoding='utf-8') as _f:
                    _content = _f.read()
                _section = _content.split("INSERT INTO hospital_charges")[1] if "INSERT INTO hospital_charges" in _content else ""
                _matches = _re.findall(r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*1\)", _section)
                for _name, _cat, _price in _matches:
                    db.session.execute(text(
                        "INSERT INTO hospital_charges (charge_name, charge_category, default_price, is_active) VALUES (:n, :c, :p, 1)"
                    ), {'n': _name, 'c': _cat, 'p': float(_price)})
                db.session.commit()
                app.logger.info("Seeded %d hospital charges from seed_charges_v3.sql", len(_matches))
            else:
                # Fallback minimal seed
                for _name, _cat, _price in [('Consultation Fee','Consultation',500), ('Miscellaneous','Misc',0)]:
                    db.session.execute(text(
                        "INSERT INTO hospital_charges (charge_name, charge_category, default_price, is_active) VALUES (:n, :c, :p, 1)"
                    ), {'n': _name, 'c': _cat, 'p': _price})
                db.session.commit()
                app.logger.info("Seeded minimal hospital charges (seed file not found)")
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed seeding hospital_charges")

    # ── ip_medications (IP doctor workflow) ──────────────────────────────────
    if 'ip_medications' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE ip_medications (
                    id INTEGER PRIMARY KEY {auto_inc},
                    admission_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    medicine_name VARCHAR(255) NOT NULL,
                    dosage VARCHAR(100) NULL,
                    route VARCHAR(50) NULL,
                    frequency VARCHAR(100) NULL,
                    duration VARCHAR(100) NULL,
                    special_instruction TEXT NULL,
                    food_relation VARCHAR(50) NULL,
                    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_date DATETIME NULL,
                    status VARCHAR(20) DEFAULT 'Active',
                    stopped_reason VARCHAR(255) NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ipmed_adm (admission_id),
                    INDEX idx_ipmed_patient (patient_id)
                )
            """))
            db.session.commit()
            app.logger.info("Created ip_medications table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating ip_medications")

    # ── ip_progress_notes (doctor round notes) ──────────────────────────────
    if 'ip_progress_notes' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE ip_progress_notes (
                    id INTEGER PRIMARY KEY {auto_inc},
                    admission_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    note_date DATE NOT NULL,
                    note_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    subjective TEXT NULL,
                    objective TEXT NULL,
                    assessment TEXT NULL,
                    plan TEXT NULL,
                    clinical_notes TEXT NULL,
                    instructions_to_nurse TEXT NULL,
                    procedure_notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ipnote_adm (admission_id),
                    INDEX idx_ipnote_patient (patient_id)
                )
            """))
            db.session.commit()
            app.logger.info("Created ip_progress_notes table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating ip_progress_notes")


def _ensure_consultation_schema_compat(app):
    """
    Create consultations and patient_medical_history tables if missing.
    Add new patient columns, prescription_medicines columns, and
    prescriptions.consultation_id FK safely.
    """
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name.lower()
    tables = set(inspector.get_table_names())
    auto_inc = "AUTO_INCREMENT" if dialect in ('mysql', 'mariadb') else ""

    def _safe_add_column(table, col_name, col_sql):
        try:
            db.session.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {col_sql}"))
            db.session.commit()
            app.logger.info("Added missing %s.%s column", table, col_name)
        except Exception:
            db.session.rollback()

    def _get_cols(table):
        return {c['name'] for c in inspect(db.engine).get_columns(table)}

    # ── New Patient columns ──────────────────────────────────────────────────
    if 'patients' in tables:
        pcols = _get_cols('patients')
        for col, sql in {
            'allergy_history': "TEXT NULL",
            'chronic_conditions': "TEXT NULL",
            'family_history': "TEXT NULL",
        }.items():
            if col not in pcols:
                _safe_add_column('patients', col, sql)

    # ── Consultations table ──────────────────────────────────────────────────
    if 'consultations' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE consultations (
                    id INTEGER PRIMARY KEY {auto_inc},
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    appointment_id INTEGER NULL,
                    visit_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    chief_complaint TEXT NULL,
                    present_condition TEXT NULL,
                    past_medication TEXT NULL,
                    examination_notes TEXT NULL,
                    provisional_diagnosis TEXT NULL,
                    final_diagnosis TEXT NULL,
                    clinical_notes TEXT NULL,
                    vitals_bp_systolic INTEGER NULL,
                    vitals_bp_diastolic INTEGER NULL,
                    vitals_pulse INTEGER NULL,
                    vitals_temperature FLOAT NULL,
                    vitals_spo2 INTEGER NULL,
                    vitals_respiratory_rate INTEGER NULL,
                    vitals_weight FLOAT NULL,
                    vitals_grbs FLOAT NULL,
                    treatment_plan TEXT NULL,
                    advice TEXT NULL,
                    diet_advice TEXT NULL,
                    rest_activity_advice TEXT NULL,
                    investigation_suggested TEXT NULL,
                    procedures_advised TEXT NULL,
                    followup_date DATE NULL,
                    doctor_internal_notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_consultations_patient_id (patient_id),
                    INDEX idx_consultations_doctor_id (doctor_id),
                    INDEX idx_consultations_patient_date (patient_id, created_at)
                )
            """))
            db.session.commit()
            app.logger.info("Created consultations table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating consultations table")
    else:
        # Backfill columns added after initial table creation
        ccols = _get_cols('consultations')
        for col, sql in {
            'visit_date': "DATETIME DEFAULT CURRENT_TIMESTAMP",
            'chief_complaint': "TEXT NULL",
            'provisional_diagnosis': "TEXT NULL",
            'final_diagnosis': "TEXT NULL",
            'vitals_grbs': "FLOAT NULL",
            'clinical_notes': "TEXT NULL",
            'diet_advice': "TEXT NULL",
            'rest_activity_advice': "TEXT NULL",
            'procedures_advised': "TEXT NULL",
            'doctor_internal_notes': "TEXT NULL",
        }.items():
            if col not in ccols:
                _safe_add_column('consultations', col, sql)

    # ── Patient medical history table ────────────────────────────────────────
    if 'patient_medical_history' not in tables:
        try:
            db.session.execute(text(f"""
                CREATE TABLE patient_medical_history (
                    id INTEGER PRIMARY KEY {auto_inc},
                    patient_id INTEGER NOT NULL,
                    `condition` VARCHAR(255) NOT NULL,
                    `type` VARCHAR(50) NOT NULL,
                    notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_pmh_patient_id (patient_id)
                )
            """))
            db.session.commit()
            app.logger.info("Created patient_medical_history table")
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed creating patient_medical_history table")

    # ── Add consultation_id to prescriptions ─────────────────────────────────
    if 'prescriptions' in tables:
        rx_cols = _get_cols('prescriptions')
        if 'consultation_id' not in rx_cols:
            _safe_add_column('prescriptions', 'consultation_id', 'INTEGER NULL')

    # ── Add route + special_instruction to prescription_medicines ─────────────
    if 'prescription_medicines' in tables:
        pm_cols = _get_cols('prescription_medicines')
        if 'route' not in pm_cols:
            _safe_add_column('prescription_medicines', 'route', 'VARCHAR(50) NULL')
        if 'special_instruction' not in pm_cols:
            _safe_add_column('prescription_medicines', 'special_instruction', 'TEXT NULL')


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # ✅ Removed ProxyFix. (No Nginx reverse proxy).
    # Using ProxyFix without a real proxy strips the normal Host headers, 
    # dropping sessions!
    # app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=0)
    
    cfg_class = config[config_name]
    app.config.from_object(cfg_class)
    app.config['APP_BUILD_ID'] = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

    # ✅ FIXED: Use the SAME secret key from config (read from env or fallback)
    # This MUST be set as app.secret_key for Flask to use it for session signing
    app.secret_key = app.config['SECRET_KEY']

    # Use cookie-based sessions that expire when the browser closes.
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # fallback if made permanent
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # localhost; set True in ProductionConfig for HTTPS

    # ── Production safety gate ────────────────────────────────────────────────
    # Validate all required RDS credentials exist BEFORE anything else starts.
    if config_name == 'production' and hasattr(cfg_class, 'validate'):
        cfg_class.validate()

    # Ensure instance directory exists (needed for log files, not SQLite)
    instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # ── Initialize extensions ─────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)  # Flask-Migrate: enables `flask db init/migrate/upgrade`
    
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    try:
        from app.events import socketio
        socketio.init_app(app, cors_allowed_origins='*')
        app.logger.info("SocketIO initialized")
    except ModuleNotFoundError as e:
        # Keep core app startup working even if realtime dependency is absent.
        if e.name == 'flask_socketio':
            app.logger.warning(
                "flask_socketio is not installed; realtime events are disabled."
            )
        else:
            raise
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    # Do not force every unauthorized request to staff portal.
    # Route by URL prefix in unauthorized_handler below.
    login_manager.login_view = 'auth.choose_login'
    login_manager.login_message_category = 'info'

    @login_manager.unauthorized_handler
    def unauthorized():
        path = (request.path or '').lower()
        print(f"[UNAUTHORIZED] path={path}, user={getattr(current_user, 'username', None)}, authenticated={current_user.is_authenticated}")

        # API and Reception usually expect JSON or specific handling
        if path.startswith('/api') or path.startswith('/reception'):
            if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'error': 'Unauthorized', 'reason': 'session_expired_or_invalid'}), 401
            return jsonify({'error': 'Unauthorized'}), 401

        # Patient-facing pages
        if path.startswith('/patient') or path.startswith('/features') or path.startswith('/ai') or path.startswith('/diet'):
            if current_user.is_authenticated:
                flash('Access denied. You do not have permission. Please log in with a patient account.', 'danger')
            else:
                flash('Session expired or not logged in. Please log in again.', 'warning')
            return redirect(url_for('auth.patient_login'))

        # Doctor-facing pages
        if path.startswith('/doctor'):
            flash('Session expired or access denied. Please log in again.', 'warning')
            return redirect(url_for('auth.doctor_login'))

        # Staff-facing pages
        if path.startswith('/lab'):
            return redirect(url_for('auth.staff_login', role='LAB_STAFF'))

        if path.startswith('/pharmacy'):
            return redirect(url_for('auth.staff_login', role='PHARMACIST'))

        if path.startswith('/host') or path.startswith('/admin'):
            return redirect(url_for('auth.staff_login'))

        # Safe fallback: login chooser (not hard-coded patient page)
        flash('Please log in to continue.', 'info')
        return redirect(url_for('auth.choose_login'))

    @app.before_request
    def debug_current_user():
        # Keep session non-permanent (expires on browser close)
        if current_user.is_authenticated:
            session.modified = True

        # Debug all requests to protected routes
        if request.path.startswith(('/lab', '/pharmacy', '/reception', '/patient', '/doctor')):
            print(f"[REQUEST] {request.method} {request.path}")
            print(f"  is_authenticated={current_user.is_authenticated}")
            print(f"  current_user={getattr(current_user, 'id', None)}/{getattr(current_user, 'username', None)}")
            if current_user.is_authenticated:
                print(f"  role={getattr(current_user, 'role', None)}")
                print(f"  role_type={type(getattr(current_user, 'role', None))}")
                print(f"  role_value={getattr(getattr(current_user, 'role', None), 'value', None)}")
            print(f"  session.permanent={session.permanent}")
            print(f"  session keys={list(session.keys())}")
            print(f"  cookies={dict(request.cookies)}")

    @login_manager.user_loader
    def load_user(user_id):
        # Use the modern SQLAlchemy 2.x API (query.get is legacy/deprecated)
        user = db.session.get(User, int(user_id))
        print(f"[USER_LOADER] Loading user_id={user_id}: found={user is not None}, user={user.username if user else 'NONE'}")
        return user

    @app.context_processor
    def inject_system_settings():
        """Inject system settings with 60-second cache to avoid DB hit on every request."""
        from app.models.models import SystemSettings
        now = time.time()
        if now > _settings_cache['expires']:
            try:
                _settings_cache['data'] = SystemSettings.query.first()
            except Exception:
                _settings_cache['data'] = None
            _settings_cache['expires'] = now + _SETTINGS_TTL
        return dict(system_settings=_settings_cache['data'])

    def has_endpoint(endpoint_name):
        return endpoint_name in app.view_functions

    def safe_url_for(endpoint_name, fallback_endpoint='main.index', **values):
        try:
            return url_for(endpoint_name, **values)
        except BuildError:
            try:
                return url_for(fallback_endpoint, **values)
            except BuildError:
                return '#'

    # Ensure helpers are always available in templates, even without context processors.
    app.jinja_env.globals['has_endpoint'] = has_endpoint
    app.jinja_env.globals['safe_url_for'] = safe_url_for

    @app.context_processor
    def inject_template_helpers():
        return dict(has_endpoint=has_endpoint, safe_url_for=safe_url_for)

    # ── Sidebar Configuration Context Processor ──
    @app.context_processor
    def inject_sidebar_config():
        """Build data-driven sidebar navigation based on user role."""
        if not current_user.is_authenticated or not hasattr(current_user, 'role') or not current_user.role:
            return {}

        role = current_user.role.value
        ep = request.endpoint or ''
        mode = request.args.get('mode', '')

        def _url(endpoint, **kw):
            return safe_url_for(endpoint, **kw)

        def _active(*endpoints):
            return ep in endpoints

        def _active_startswith(prefix):
            return ep.startswith(prefix) if ep else False

        # Role configurations
        sidebar_configs = {
            'PATIENT': {
                'brand_icon': 'fa-heartbeat',
                'brand_gradient': None,
                'home_url': _url('patient.dashboard'),
                'role_label': 'Patient',
                'display_name': current_user.username,
            },
            'DOCTOR': {
                'brand_icon': 'fa-user-md',
                'brand_gradient': 'linear-gradient(135deg, #10b981, #059669)',
                'home_url': _url('doctor.portal'),
                'role_label': 'Doctor',
                'display_name': 'Dr. ' + current_user.username,
            },
            'NURSE': {
                'brand_icon': 'fa-user-nurse',
                'brand_gradient': 'linear-gradient(135deg, #34d399, #059669)',
                'home_url': _url('nurse.dashboard'),
                'role_label': 'Nurse',
                'display_name': current_user.username,
            },
            'HOST': {
                'brand_icon': 'fa-shield-alt',
                'brand_gradient': 'linear-gradient(135deg, #ef4444, #dc2626)',
                'home_url': _url('host.dashboard'),
                'role_label': 'Super Admin',
                'display_name': current_user.username,
            },
            'LAB_STAFF': {
                'brand_icon': 'fa-flask',
                'brand_gradient': 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
                'home_url': _url('lab.dashboard'),
                'role_label': 'Lab Staff',
                'display_name': current_user.username,
            },
            'PHARMACIST': {
                'brand_icon': 'fa-prescription-bottle-alt',
                'brand_gradient': 'linear-gradient(135deg, #f59e0b, #d97706)',
                'home_url': _url('pharmacy_ops.dashboard'),
                'role_label': 'Pharmacist',
                'display_name': current_user.username,
            },
            'RECEPTIONIST': {
                'brand_icon': 'fa-clipboard-list',
                'brand_gradient': 'linear-gradient(135deg, #06b6d4, #0891b2)',
                'home_url': _url('reception.dashboard'),
                'role_label': 'Receptionist',
                'display_name': current_user.username,
            },
        }

        # Navigation items per role
        nav_items = {
            'PATIENT': [
                {'section': 'Main'},
                {'icon': 'fa-th-large', 'label': 'Dashboard', 'url': _url('patient.dashboard'), 'active': _active('patient.dashboard')},
                {'icon': 'fa-calendar-alt', 'label': 'Appointments', 'url': _url('patient.appointments'), 'active': _active('patient.appointments', 'patient.book_appointment')},
                {'icon': 'fa-pills', 'label': 'Prescriptions', 'url': _url('patient.prescriptions'), 'active': _active('patient.prescriptions')},
                {'icon': 'fa-flask', 'label': 'Lab Reports', 'url': _url('patient.lab_reports'), 'active': _active('patient.lab_reports')},
                {'icon': 'fa-prescription-bottle-alt', 'label': 'Medicine Status', 'url': safe_url_for('patient.medicine_status', 'patient.diet_plan'), 'active': _active('patient.medicine_status')},
                {'section': 'Health'},
                {'icon': 'fa-heartbeat', 'label': 'Vitals', 'url': _url('patient.enter_health_data'), 'active': _active('patient.enter_health_data')},
                {'icon': 'fa-apple-alt', 'label': 'Diet Plan', 'url': _url('patient.diet_plan'), 'active': _active('patient.diet_plan')},
                {'icon': 'fa-running', 'label': 'Exercise Plan', 'url': _url('patient.exercise_plan'), 'active': _active('patient.exercise_plan')},
                {'icon': 'fa-stethoscope', 'label': 'Symptom Checker', 'url': _url('patient.symptom_checker'), 'active': _active('patient.symptom_checker'), 'icon_color': '#ef4444'},
                {'icon': 'fa-x-ray', 'label': 'Image Analysis', 'url': _url('patient.image_analysis'), 'active': _active('patient.image_analysis'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-capsules', 'label': 'Med Tracker', 'url': _url('patient.medication_tracker'), 'active': _active('patient.medication_tracker'), 'icon_color': '#10b981'},
                {'icon': 'fa-syringe', 'label': 'Vaccinations', 'url': _url('patient.vaccination_records'), 'active': _active('patient.vaccination_records'), 'icon_color': '#06b6d4'},
                {'section': 'Tools'},
                {'icon': 'fa-comment-dots', 'label': 'Messages', 'url': _url('patient.messages'), 'active': _active('patient.messages')},
                {'icon': 'fa-file-invoice-dollar', 'label': 'Billing', 'url': _url('patient.billing'), 'active': _active('patient.billing')},
                {'icon': 'fa-video', 'label': 'Telemedicine', 'url': _url('telemedicine.dashboard'), 'active': _active_startswith('telemedicine.'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-star', 'label': 'Feedback', 'url': _url('feedback_module.dashboard'), 'active': _active_startswith('feedback_module.'), 'icon_color': '#f59e0b'},
                {'icon': 'fa-bell', 'label': 'Notifications', 'url': _url('notifications.center'), 'active': _active_startswith('notifications.')},
                {'icon': 'fa-cog', 'label': 'Settings', 'url': _url('patient.profile'), 'active': _active('patient.profile', 'patient.edit_profile')},
            ],
            'DOCTOR': [
                {'section': 'Main'},
                {'icon': 'fa-hospital-user', 'label': 'Doctor Portal', 'url': _url('doctor.portal'), 'active': _active('doctor.portal') and mode != 'op' and mode != 'ip'},
                {'icon': 'fa-bolt', 'label': 'OP Patients', 'url': _url('doctor.portal') + '?mode=op', 'active': _active('doctor.portal') and mode == 'op', 'icon_color': '#a78bfa', 'badge_id': 'sidebarOPBadge'},
                {'icon': 'fa-bed', 'label': 'IP Patients', 'url': _url('doctor.portal') + '?mode=ip', 'active': (_active('doctor.portal') and mode == 'ip') or _active('doctor.ip_patient_detail'), 'icon_color': '#67e8f9', 'badge_id': 'sidebarIPBadge'},
                {'icon': 'fa-clipboard-list', 'label': 'Reception Queue', 'url': _url('reception.dashboard'), 'active': _active_startswith('reception.')},
                {'icon': 'fa-th-large', 'label': 'Legacy Dashboard', 'url': _url('doctor.dashboard'), 'active': _active('doctor.dashboard')},
                {'icon': 'fa-users', 'label': 'Patients', 'url': _url('doctor.patient_list'), 'active': _active('doctor.patient_list', 'doctor.view_patient')},
                {'icon': 'fa-calendar-alt', 'label': 'Appointments', 'url': _url('doctor.appointments'), 'active': _active('doctor.appointments')},
                {'section': 'Clinical'},
                {'icon': 'fa-comment-medical', 'label': 'Messages', 'url': _url('doctor.messages'), 'active': _active('doctor.messages')},
                {'icon': 'fa-flask', 'label': 'Lab Requests', 'url': _url('doctor.lab_requests'), 'active': _active('doctor.lab_requests')},
                {'icon': 'fa-file-medical-alt', 'label': 'Lab Reports', 'url': _url('doctor.lab_reports_view'), 'active': _active('doctor.lab_reports_view')},
                {'icon': 'fa-pills', 'label': 'Pharmacy Orders', 'url': _url('doctor.pharmacy_orders'), 'active': _active('doctor.pharmacy_orders')},
                {'icon': 'fa-chart-line', 'label': 'Analytics', 'url': _url('doctor.analytics'), 'active': _active('doctor.analytics')},
                {'section': 'IP & Billing'},
                {'icon': 'fa-file-invoice-dollar', 'label': 'Billing Dashboard', 'url': _url('ip_billing.dashboard'), 'active': _active_startswith('ip_billing.dashboard')},
                {'icon': 'fa-bed', 'label': 'IP Admission', 'url': _url('ip_billing.admit_patient'), 'active': _active('ip_billing.admit_patient')},
                {'section': 'AI Tools'},
                {'icon': 'fa-robot', 'label': 'AI Assistant', 'url': _url('doctor.ai_assistant'), 'active': _active('doctor.ai_assistant')},
                {'section': 'Advanced'},
                {'icon': 'fa-procedures', 'label': 'OT Management', 'url': _url('ot.dashboard'), 'active': _active_startswith('ot.')},
                {'icon': 'fa-ambulance', 'label': 'Emergency', 'url': _url('emergency.dashboard'), 'active': _active_startswith('emergency.'), 'icon_color': '#ef4444'},
                {'icon': 'fa-shield-alt', 'label': 'Insurance/TPA', 'url': _url('insurance.dashboard'), 'active': _active_startswith('insurance.')},
                {'icon': 'fa-video', 'label': 'Telemedicine', 'url': _url('telemedicine.dashboard'), 'active': _active_startswith('telemedicine.'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-star', 'label': 'Feedback', 'url': _url('feedback_module.dashboard'), 'active': _active_startswith('feedback_module.')},
                {'icon': 'fa-bed', 'label': 'Bed Management', 'url': _url('bed_management.dashboard'), 'active': _active_startswith('bed_management.'), 'icon_color': '#34d399'},
                {'icon': 'fa-calendar-alt', 'label': 'Duty Roster', 'url': _url('duty_roster.dashboard'), 'active': _active_startswith('duty_roster.'), 'icon_color': '#fbbf24'},
                {'section': 'Account'},
                {'icon': 'fa-cog', 'label': 'Settings', 'url': _url('doctor.edit_profile'), 'active': _active('doctor.edit_profile')},
            ],
            'NURSE': [
                {'section': 'Nurse Portal'},
                {'icon': 'fa-th-large', 'label': 'Dashboard', 'url': _url('nurse.dashboard'), 'active': _active('nurse.dashboard')},
                {'icon': 'fa-procedures', 'label': 'Assigned Patients', 'url': _url('nurse.patients'), 'active': _active('nurse.patients')},
                {'icon': 'fa-heartbeat', 'label': 'Patient Vitals', 'url': _url('nurse.vitals'), 'active': _active('nurse.vitals')},
                {'icon': 'fa-tasks', 'label': 'Tasks / Instructions', 'url': _url('nurse.tasks'), 'active': _active('nurse.tasks', 'nurse.complete_task')},
                {'icon': 'fa-notes-medical', 'label': 'Nurse Notes', 'url': _url('nurse.notes'), 'active': _active('nurse.notes', 'nurse.add_note')},
                {'icon': 'fa-flask', 'label': 'Lab Coordination', 'url': _url('nurse.lab'), 'active': _active('nurse.lab')},
                {'section': 'Inpatient'},
                {'icon': 'fa-pills', 'label': 'IP Medications', 'url': _url('nurse.medications'), 'active': _active('nurse.medications', 'nurse.medication_update')},
                {'section': 'Shift'},
                {'icon': 'fa-exchange-alt', 'label': 'Shift Handover', 'url': _url('nurse.handover'), 'active': _active('nurse.handover', 'nurse.handover_save')},
                {'section': 'Advanced'},
                {'icon': 'fa-ambulance', 'label': 'Emergency', 'url': _url('emergency.dashboard'), 'active': _active_startswith('emergency.'), 'icon_color': '#ef4444'},
                {'icon': 'fa-procedures', 'label': 'OT Schedule', 'url': _url('ot.dashboard'), 'active': _active_startswith('ot.')},
                {'icon': 'fa-boxes', 'label': 'Inventory', 'url': _url('inventory.dashboard'), 'active': _active_startswith('inventory.')},
                {'icon': 'fa-bed', 'label': 'Bed Management', 'url': _url('bed_management.dashboard'), 'active': _active_startswith('bed_management.'), 'icon_color': '#34d399'},
            ],
            'HOST': [
                {'section': 'Admin'},
                {'icon': 'fa-tachometer-alt', 'label': 'Dashboard', 'url': _url('host.dashboard'), 'active': _active('host.dashboard')},
                {'icon': 'fa-user-md', 'label': 'Doctors', 'url': _url('host.doctor_management'), 'active': _active('host.doctor_management')},
                {'icon': 'fa-user-plus', 'label': 'Add Staff', 'url': _url('host.create_staff'), 'active': _active('host.create_staff')},
                {'icon': 'fa-id-badge', 'label': 'Homepage Doctors', 'url': _url('host.frontpage_doctors'), 'active': _active('host.frontpage_doctors')},
                {'icon': 'fa-building', 'label': 'Departments', 'url': _url('host.departments'), 'active': _active('host.departments')},
                {'section': 'Activity & Tracking'},
                {'icon': 'fa-sign-in-alt', 'label': 'Login Activity', 'url': _url('host.login_activity'), 'active': _active('host.login_activity'), 'icon_color': '#06b6d4'},
                {'icon': 'fa-user-plus', 'label': 'Registrations', 'url': _url('host.patient_registrations'), 'active': _active('host.patient_registrations'), 'icon_color': '#10b981'},
                {'icon': 'fa-user-md', 'label': 'Doctor Activity', 'url': _url('host.doctor_activity'), 'active': _active('host.doctor_activity'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-id-card', 'label': 'Staff Activity', 'url': _url('host.staff_activity'), 'active': _active('host.staff_activity')},
                {'icon': 'fa-users', 'label': 'All Patients', 'url': _url('host.all_patients'), 'active': _active('host.all_patients')},
                {'section': 'Finance'},
                {'icon': 'fa-file-invoice-dollar', 'label': 'Billing Report', 'url': _url('host.billing_report'), 'active': _active('host.billing_report'), 'icon_color': '#10b981'},
                {'icon': 'fa-pills', 'label': 'Pharmacy Report', 'url': _url('host.pharmacy_report'), 'active': _active('host.pharmacy_report'), 'icon_color': '#f59e0b'},
                {'icon': 'fa-flask', 'label': 'Lab Report', 'url': _url('host.lab_report'), 'active': _active('host.lab_report'), 'icon_color': '#06b6d4'},
                {'section': 'Department Views'},
                {'icon': 'fa-flask', 'label': 'Laboratory', 'url': _url('lab.dashboard'), 'active': 'lab.' in ep},
                {'icon': 'fa-pills', 'label': 'Pharmacy Ops', 'url': _url('pharmacy_ops.dashboard'), 'active': 'pharmacy' in ep},
                {'icon': 'fa-concierge-bell', 'label': 'Reception', 'url': _url('reception.dashboard'), 'active': 'reception.' in ep},
                {'icon': 'fa-user-nurse', 'label': 'Nursing', 'url': _url('nurse.dashboard'), 'active': 'nurse.' in ep},
                {'section': 'Hospital Modules'},
                {'icon': 'fa-procedures', 'label': 'OT Management', 'url': _url('ot.dashboard'), 'active': _active_startswith('ot.')},
                {'icon': 'fa-ambulance', 'label': 'Emergency', 'url': _url('emergency.dashboard'), 'active': _active_startswith('emergency.'), 'icon_color': '#ef4444'},
                {'icon': 'fa-shield-alt', 'label': 'Insurance/TPA', 'url': _url('insurance.dashboard'), 'active': _active_startswith('insurance.')},
                {'icon': 'fa-boxes', 'label': 'Inventory', 'url': _url('inventory.dashboard'), 'active': _active_startswith('inventory.')},
                {'icon': 'fa-video', 'label': 'Telemedicine', 'url': _url('telemedicine.dashboard'), 'active': _active_startswith('telemedicine.'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-chart-bar', 'label': 'Analytics', 'url': _url('analytics_dashboard.dashboard'), 'active': _active_startswith('analytics_dashboard.')},
                {'icon': 'fa-star', 'label': 'Feedback', 'url': _url('feedback_module.dashboard'), 'active': _active_startswith('feedback_module.'), 'icon_color': '#f59e0b'},
                {'icon': 'fa-bed', 'label': 'Bed Management', 'url': _url('bed_management.dashboard'), 'active': _active_startswith('bed_management.'), 'icon_color': '#34d399'},
                {'icon': 'fa-calendar-alt', 'label': 'Duty Roster', 'url': _url('duty_roster.dashboard'), 'active': _active_startswith('duty_roster.'), 'icon_color': '#fbbf24'},
                {'section': 'Governance'},
                {'icon': 'fa-clipboard-list', 'label': 'Audit Logs', 'url': _url('host.audit_logs'), 'active': _active('host.audit_logs')},
                {'icon': 'fa-cogs', 'label': 'Settings', 'url': _url('host.settings'), 'active': _active('host.settings')},
            ],
            'LAB_STAFF': [
                {'section': 'Laboratory'},
                {'icon': 'fa-th-large', 'label': 'Dashboard', 'url': _url('lab.dashboard'), 'active': _active('lab.dashboard')},
                {'icon': 'fa-clock', 'label': 'Pending', 'url': _url('lab.dashboard', status='PENDING'), 'active': False},
                {'icon': 'fa-spinner', 'label': 'Processing', 'url': _url('lab.dashboard', status='PROCESSING'), 'active': False},
                {'icon': 'fa-check-circle', 'label': 'Completed', 'url': _url('lab.dashboard', status='COMPLETED'), 'active': False},
                {'section': 'Source'},
                {'icon': 'fa-user-md', 'label': 'Doctor Referrals', 'url': _url('lab.dashboard', filter='doctor'), 'active': False},
                {'icon': 'fa-vial', 'label': 'Walk-in Only', 'url': _url('lab.dashboard', filter='walkin'), 'active': False},
            ],
            'PHARMACIST': [
                {'section': 'Pharmacy'},
                {'icon': 'fa-th-large', 'label': 'Dashboard', 'url': _url('pharmacy_ops.dashboard'), 'active': _active('pharmacy_ops.dashboard')},
                {'icon': 'fa-clock', 'label': 'Pending Orders', 'url': _url('pharmacy_ops.dashboard') + '?status=Pending', 'active': False},
                {'icon': 'fa-check-circle', 'label': 'Dispensed', 'url': _url('pharmacy_ops.dashboard') + '?status=Dispensed', 'active': False},
                {'icon': 'fa-user-clock', 'label': 'Patient History', 'url': _url('pharmacy_ops.patient_history_page'), 'active': _active('pharmacy_ops.patient_history_page')},
                {'section': 'Inpatient'},
                {'icon': 'fa-hospital-user', 'label': 'IP Med Requests', 'url': _url('pharmacy_ops.ip_medication_requests'), 'active': _active('pharmacy_ops.ip_medication_requests')},
                {'section': 'Inventory'},
                {'icon': 'fa-capsules', 'label': 'Medicine Stock', 'url': _url('features.pharmacy'), 'active': _active('features.pharmacy')},
                {'icon': 'fa-boxes', 'label': 'Supply Inventory', 'url': _url('inventory.dashboard'), 'active': _active_startswith('inventory.')},
            ],
            'RECEPTIONIST': [
                {'section': 'Reception'},
                {'icon': 'fa-th-large', 'label': 'Dashboard', 'url': _url('reception.dashboard'), 'active': _active('reception.dashboard')},
                {'icon': 'fa-tv', 'label': 'Queue Display', 'url': _url('reception.queue_display'), 'active': _active('reception.queue_display')},
                {'icon': 'fa-notes-medical', 'label': 'Patient History', 'url': _url('reception.patient_history'), 'active': _active('reception.patient_history')},
                {'section': 'IP & Billing'},
                {'icon': 'fa-file-invoice-dollar', 'label': 'Billing Dashboard', 'url': _url('ip_billing.dashboard'), 'active': _active_startswith('ip_billing.dashboard')},
                {'icon': 'fa-bed', 'label': 'IP Admission', 'url': _url('ip_billing.admit_patient'), 'active': _active('ip_billing.admit_patient')},
                {'section': 'Advanced'},
                {'icon': 'fa-ambulance', 'label': 'Emergency', 'url': _url('emergency.dashboard'), 'active': _active_startswith('emergency.'), 'icon_color': '#ef4444'},
                {'icon': 'fa-shield-alt', 'label': 'Insurance/TPA', 'url': _url('insurance.dashboard'), 'active': _active_startswith('insurance.')},
                {'icon': 'fa-video', 'label': 'Telemedicine', 'url': _url('telemedicine.dashboard'), 'active': _active_startswith('telemedicine.'), 'icon_color': '#8b5cf6'},
                {'icon': 'fa-bed', 'label': 'Bed Management', 'url': _url('bed_management.dashboard'), 'active': _active_startswith('bed_management.'), 'icon_color': '#34d399'},
            ],
        }

        config = sidebar_configs.get(role, {
            'brand_icon': 'fa-heartbeat',
            'brand_gradient': None,
            'home_url': '/',
            'role_label': role.replace('_', ' ').title(),
            'display_name': current_user.username,
        })
        items = nav_items.get(role, [])

        return dict(sidebar_config=config, sidebar_nav=items)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.features import features_bp
    from app.routes.ai_chatbot import ai_bp
    from app.routes.diet_plan import diet_plan_bp
    from app.routes.diet_plan_dashboard import diet_plan_dashboard_bp
    
    # Use advanced auth system with unified login
    try:
        from app.routes.auth_advanced import auth_advanced_bp as auth_bp
        print("[AUTH] Using advanced authentication system with unified login")
    except ImportError:
        from app.routes.auth import auth_bp
        print("[AUTH] Fallback to standard authentication")
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(features_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(diet_plan_bp)

    app.register_blueprint(diet_plan_dashboard_bp)

    from app.routes.host import host_bp
    app.register_blueprint(host_bp)

    # New operational modules
    from app.routes.lab import lab_bp
    from app.routes.pharmacy_ops import pharmacy_ops_bp
    from app.routes.pharmacy import pharmacy_bp
    from app.routes.reception import reception_bp
    from app.routes.walkin import walkin_bp
    from app.routes.patients_api import patients_api_bp, patients_bp
    app.register_blueprint(lab_bp)
    app.register_blueprint(pharmacy_ops_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(walkin_bp)
    app.register_blueprint(patients_api_bp)
    app.register_blueprint(patients_bp)

    # QR Visit System
    from app.routes.qr_visit import qr_bp
    app.register_blueprint(qr_bp)
    csrf.exempt(qr_bp)
    print('[MODULES] QR Visit System registered')

    # IP Billing & Discharge Module
    from app.routes.ip_billing import ip_billing_bp
    app.register_blueprint(ip_billing_bp)

    # Nurse Portal
    from app.routes.nurse import nurse_bp
    app.register_blueprint(nurse_bp)

    # AI Voice Prescription System (Whisper)
    from app.routes.voice_api import voice_bp
    app.register_blueprint(voice_bp)
    csrf.exempt(voice_bp)  # Audio uploads can't carry CSRF tokens easily
    print('[VOICE] AI Voice Prescription System registered (Faster-Whisper)')

    # ── New Modules (World-Class Hospital Features) ──
    from app.routes.ot_management import ot_bp
    from app.routes.emergency import emergency_bp
    from app.routes.insurance import insurance_bp
    from app.routes.inventory import inventory_bp
    from app.routes.telemedicine import telemedicine_bp
    from app.routes.feedback import feedback_bp
    from app.routes.notifications import notifications_bp
    from app.routes.analytics import analytics_bp
    app.register_blueprint(ot_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(insurance_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(telemedicine_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)
    from app.routes.health_tools import health_tools_bp
    from app.routes.health_packages import health_packages_bp
    app.register_blueprint(health_tools_bp)
    app.register_blueprint(health_packages_bp)
    csrf.exempt(health_tools_bp)
    # health_packages_bp is NOT csrf-exempt: booking form sends csrf_token
    print('[MODULES] OT, Emergency, Insurance, Inventory, Telemedicine, Feedback, Notifications, Analytics, Health Tools, Health Packages registered')

    # Bed Management & Duty Roster
    from app.routes.bed_management import bed_management_bp
    from app.routes.duty_roster import duty_roster_bp
    app.register_blueprint(bed_management_bp)
    app.register_blueprint(duty_roster_bp)
    csrf.exempt(bed_management_bp)
    csrf.exempt(duty_roster_bp)
    print('[MODULES] Bed Management, Duty Roster registered')

    # Doctor Search (public) & Referral System
    from app.routes.doctor_search import doctor_search_bp
    from app.routes.referral import referral_bp
    app.register_blueprint(doctor_search_bp)
    app.register_blueprint(referral_bp)
    csrf.exempt(doctor_search_bp)
    csrf.exempt(referral_bp)
    print('[MODULES] Doctor Search (public), Referral System registered')

    # Exempt JSON-API-heavy blueprints from CSRF.
    # These endpoints are called via fetch() with Content-Type: application/json.
    # Session-based auth (@login_required + role decorators) already protects them.
    csrf.exempt(doctor_bp)
    csrf.exempt(lab_bp)
    csrf.exempt(pharmacy_ops_bp)
    csrf.exempt(pharmacy_bp)
    csrf.exempt(reception_bp)
    csrf.exempt(walkin_bp)
    csrf.exempt(patients_api_bp)
    csrf.exempt(features_bp)
    csrf.exempt(ai_bp)
    csrf.exempt(ip_billing_bp)
    csrf.exempt(ot_bp)
    csrf.exempt(emergency_bp)
    csrf.exempt(insurance_bp)
    csrf.exempt(inventory_bp)
    csrf.exempt(telemedicine_bp)
    csrf.exempt(feedback_bp)
    csrf.exempt(notifications_bp)
    csrf.exempt(analytics_bp)

    # Warm Whisper model in background so first dictation is faster.
    if os.getenv('WHISPER_PRELOAD', 'true').lower() in ('1', 'true', 'yes', 'on'):
        try:
            from app.services.voice_service import warmup_whisper_model
            threading.Thread(target=warmup_whisper_model, daemon=True).start()
        except Exception as e:
            print(f"[VOICE] Whisper warmup skipped: {e}")
    
    # Create tables
    with app.app_context():
        db.create_all()

        # ── Ensure new module tables have all columns ──
        _ensure_new_modules_schema_compat(app)

        # ── Ensure patient_vitals has blood_sugar column ──
        try:
            db.session.execute(text("SELECT blood_sugar FROM patient_vitals LIMIT 1"))
        except Exception:
            db.session.rollback()
            try:
                db.session.execute(text("ALTER TABLE patient_vitals ADD COLUMN `blood_sugar` FLOAT NULL"))
                db.session.commit()
                app.logger.info("Added blood_sugar column to patient_vitals")
            except Exception:
                db.session.rollback()

        # ── Ensure system_settings has whatsapp_number column ──
        try:
            db.session.execute(text("SELECT whatsapp_number FROM system_settings LIMIT 1"))
        except Exception:
            db.session.rollback()
            try:
                db.session.execute(text("ALTER TABLE system_settings ADD COLUMN `whatsapp_number` VARCHAR(20) DEFAULT '919443966329'"))
                db.session.commit()
            except Exception:
                db.session.rollback()

        # ── Ensure a default Hospital record exists ──────────────────────────
        # Every registration route requires Hospital.query.first() to return a
        # valid row.  If the database was freshly created (or the old init_db.py
        # was never executed), seed a default hospital automatically.
        from app.models.models import Hospital
        if not Hospital.query.first():
            default_hospital = Hospital(
                name="CarePoint Hospital",
                domain_prefix="carepoint",
                contact_email="admin@carepoint.com",
                address="123 Healthcare Avenue, Medical City"
            )
            db.session.add(default_hospital)
            try:
                db.session.commit()
                app.logger.info("Seeded default hospital: %s", default_hospital.name)
            except Exception:
                db.session.rollback()
                app.logger.exception("Failed to seed default hospital")

        _ensure_ip_billing_schema_compat(app)      # Creates IP/billing tables + extends patients/visits/billings
        _ensure_consultation_schema_compat(app)     # Must run before patients compat: adds ORM-expected columns
        _ensure_patients_schema_compat(app)
        _ensure_health_data_schema_compat(app)
        _ensure_prescriptions_schema_compat(app)
        _ensure_users_role_schema_compat(app)
        _ensure_billing_doctor_nullable(app)
        _ensure_medicines_schema_compat(app)
        _ensure_patient_history_schema_compat(app)

        # Fix patients created with NULL name/uhid (e.g. via Google OAuth) — must run AFTER schema compat
        _repair_incomplete_patients(app)

    # ── Health check endpoint (used by load-balancer) ─────────────────
    @app.route('/health')
    def health_check():
        """Lightweight liveness probe. Returns 200 OK when the app is running."""
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'build_id': app.config.get('APP_BUILD_ID'),
            'server_time_utc': datetime.datetime.utcnow().isoformat() + 'Z'
        }), 200

    @app.route('/build-info')
    def build_info():
        from flask import jsonify
        return jsonify({
            'build_id': app.config.get('APP_BUILD_ID'),
            'config': config_name,
            'server_time_utc': datetime.datetime.utcnow().isoformat() + 'Z'
        }), 200

    @app.route('/api/debug/session', methods=['GET', 'POST'])
    def debug_session_endpoint():
        """Diagnostic endpoint to check session state - helps debug auth issues"""
        from flask import jsonify, session as flask_session, request
        return jsonify({
            'authenticated': current_user.is_authenticated,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'user_username': current_user.username if current_user.is_authenticated else None,
            'user_role': current_user.role.value if (current_user.is_authenticated and hasattr(current_user, 'role')) else None,
            'session_user_id': flask_session.get('_user_id'),
            'session_permanent': flask_session.get('permanent', '(not set)'),
            'request_cookies': dict(request.cookies),
            'request_headers_accept': request.headers.get('Accept', ''),
            'request_headers_xhr': request.headers.get('X-Requested-With', ''),
            'request_method': request.method,
            'session_key_count': len(flask_session.keys()),
        })

    @app.after_request
    def attach_build_headers(response):
        response.headers['X-App-Build'] = str(app.config.get('APP_BUILD_ID', 'unknown'))
        response.headers['X-App-Config'] = str(config_name)
        return response
    
    @app.errorhandler(500)
    def handle_500(e):
        import traceback
        from datetime import datetime
        from flask import request as flask_request
        try:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'global_500_error.txt')
            with open(log_path, 'a') as f:
                f.write(f"\n\n--- ERROR AT {datetime.now()} ---\n")
                f.write(f"URL: {flask_request.url}\n")
                f.write(str(e) + '\n' + traceback.format_exc())
        except Exception:
            pass

        # Return JSON for API/AJAX requests
        is_api = (
            flask_request.path.startswith('/doctor/api/') or
            flask_request.path.startswith('/api/') or
            'application/json' in (flask_request.content_type or '') or
            flask_request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            'application/json' in flask_request.headers.get('Accept', '')
        )
        if is_api:
            from flask import jsonify
            return jsonify({'success': False, 'error': f'Internal Server Error: {str(e)}'}), 500

        return "Internal Server Error", 500

    # Handle CSRF failures gracefully for API / AJAX endpoints
    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        from flask import request as flask_request
        is_api = (
            flask_request.path.startswith('/doctor/api/') or
            flask_request.path.startswith('/api/') or
            flask_request.path.startswith('/lab/') or
            flask_request.path.startswith('/reception/') or
            flask_request.path.startswith('/features/') or
            'application/json' in (flask_request.content_type or '') or
            'application/json' in flask_request.headers.get('Accept', '')
        )
        if is_api:
            from flask import jsonify
            return jsonify({'success': False, 'error': f'CSRF validation failed: {e.description}'}), 400
        flash('Session expired. Please refresh the page and try again.', 'warning')
        return redirect(flask_request.referrer or '/')

    return app
