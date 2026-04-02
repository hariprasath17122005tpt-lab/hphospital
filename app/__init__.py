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

    # ✅ FIXED: Use ONLY Flask default cookie-based sessions (no Flask-Session)
    # Flask-Session filesystem backend breaks with multiple Gunicorn workers
    # because different workers can't share /tmp session files.
    # Flask's built-in signed cookie session works perfectly across all workers.
    # Set session as permanent by default (session persists across browser close)
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
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
        # Prevent stale session by forcing permanent session refresh for logged-in users
        if current_user.is_authenticated:
            session.permanent = True
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

    # Nurse Portal
    from app.routes.nurse import nurse_bp
    app.register_blueprint(nurse_bp)

    # AI Voice Prescription System (Whisper)
    from app.routes.voice_api import voice_bp
    app.register_blueprint(voice_bp)
    csrf.exempt(voice_bp)  # Audio uploads can't carry CSRF tokens easily
    print('[VOICE] AI Voice Prescription System registered (Faster-Whisper)')

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

        _ensure_patients_schema_compat(app)
        _ensure_health_data_schema_compat(app)
        _ensure_prescriptions_schema_compat(app)
        _ensure_users_role_schema_compat(app)
        _ensure_billing_doctor_nullable(app)
        _ensure_medicines_schema_compat(app)
        _ensure_patient_history_schema_compat(app)

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
