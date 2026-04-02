"""
Patients API Module — Main Patient Identity System
Handles:
- Patient registration and identification
- UHID generation and management
- Patient search (UHID, name, phone)
- Duplicate detection
- Patient history and records
- Integration with doctor and lab modules

Accessible by: RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN, HOST
"""

from flask import Blueprint, request, jsonify, current_app, session
from flask_login import login_required, current_user, login_user
from app.models.models import (
    db, User, Patient, Doctor, UserRole, Hospital, 
    LabOrder, Prescription, Appointment, HealthData
)
from app.services.patient_history_service import PatientHistoryService
from app.services.patient_service import PatientService
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)

patients_api_bp = Blueprint('patients_api', __name__, url_prefix='/api/patients')
# Compatibility alias for clients/pages calling non-/api patient URLs.
patients_bp = Blueprint('patients', __name__, url_prefix='/patients')


def _try_recover_session_user():
    """Recover current_user from the signed session cookie during API calls."""
    if current_user.is_authenticated:
        logger.debug(f"User already authenticated: {current_user.id}")
        return current_user

    raw_user_id = session.get('_user_id')
    logger.debug(f"_try_recover_session_user: raw_user_id={raw_user_id}, path={request.path}")
    
    if not raw_user_id:
        logger.warning(f"No _user_id in session for {request.path}")
        return None
    
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        logger.error(f"Could not parse user_id: {raw_user_id}")
        return None

    try:
        user = db.session.get(User, user_id)
        logger.debug(f"User lookup: user_id={user_id}, found={user is not None}, active={user.is_active if user else 'N/A'}")
        
        if not user or not user.is_active:
            logger.warning(f"User not found or inactive: user_id={user_id}")
            return None

        login_user(user, remember=False, force=True)
        logger.warning(f"Recovered API session for user_id={user_id} on {request.path}")
        return user
    except Exception as e:
        logger.error(f"Session recovery error: {e}", exc_info=True)
        return None


def patient_access_required(f):
    """Allow RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN, HOST access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        _try_recover_session_user()
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        allowed_roles = (
            UserRole.RECEPTIONIST, UserRole.LAB_STAFF, 
            UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN
        )
        
        if current_user.role not in allowed_roles:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        return f(*args, **kwargs)
    return decorated


def patient_history_access_required(f):
    """Restrict centralized patient history to reception, pharmacy, admin, and host."""
    @wraps(f)
    def decorated(*args, **kwargs):
        _try_recover_session_user()
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        allowed_roles = (
            UserRole.RECEPTIONIST,
            UserRole.PHARMACIST,
            UserRole.ADMIN,
            UserRole.HOST,
        )
        if current_user.role not in allowed_roles:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# PATIENT CREATION & REGISTRATION
# ─────────────────────────────────────────────────────────────

@patients_api_bp.route('/register', methods=['POST'])
@patient_access_required
def register_patient():
    """
    Register a new patient (walk-in or returning).
    Performs duplicate detection before creation.
    
    Request body:
    {
        "name": "Ravi Kumar",
        "age": 35,
        "gender": "Male",
        "phone": "9876543210",
        "address": "123 Main St",
        "force_create": false  # Skip duplicate check if true
    }
    
    Response:
    {
        "success": true,
        "patient": { id, uhid, name, ... },
        "duplicates": [],  # If found
        "message": "Patient registered"
    }
    """
    try:
        print("USER AUTH:", current_user.is_authenticated)
        data = request.get_json() or {}
        
        # Validate required fields (canonical `name` with backward compatibility)
        full_name = ' '.join((data.get('name') or '').strip().split())
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        if not full_name:
            full_name = f"{first_name} {last_name}".strip()
        age_str = data.get('age', '')
        gender = data.get('gender', '').strip()
        
        if not full_name:
            return jsonify({'success': False, 'error': 'Name required'}), 400
        
        if not age_str:
            return jsonify({'success': False, 'error': 'Age required'}), 400
        
        if not gender:
            return jsonify({'success': False, 'error': 'Gender required'}), 400
        
        # Parse age
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                raise ValueError("Invalid age range")
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Age must be a valid number'}), 400
        
        # Optional fields
        phone = data.get('phone', '').strip() or None
        address = data.get('address', '').strip() or None
        dob_raw = (data.get('date_of_birth') or '').strip()
        force_create = data.get('force_create', False)
        date_of_birth = None
        if dob_raw:
            try:
                date_of_birth = datetime.strptime(dob_raw, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'date_of_birth must be YYYY-MM-DD'}), 400

        if phone and not PatientService.validate_phone(phone):
            return jsonify({'success': False, 'error': 'Invalid phone format'}), 400
        
        # Get hospital
        hospital = Hospital.query.first()
        hospital_id = hospital.id if hospital else None
        
        # Check for duplicates unless force_create is True
        duplicates = []
        if not force_create and (phone or full_name):
            similar = PatientService.find_similar_patients(
                name=full_name if full_name else None,
                phone=phone,
                age=age,
                threshold=0.7
            )
            
            if similar and len(similar) > 0:
                duplicates = [{
                    'id': s['patient'].id,
                    'uhid': s['patient'].uhid,
                    'name': s['patient'].full_name,
                    'phone': s['patient'].phone,
                    'age': s['patient'].age,
                    'gender': s['patient'].gender,
                    'similarity': s['similarity'],
                    'reason': s['reason']
                } for s in similar]
                
                # Return duplicates without creating patient
                return jsonify({
                    'success': False,
                    'error': 'Possible existing patient found',
                    'code': 'DUPLICATE_WARNING',
                    'duplicates': duplicates,
                    'message': 'Possible existing patient found'
                }), 409
        
        # Create patient
        patient = PatientService.create_walk_in_patient(
            name=full_name,
            age=age,
            gender=gender,
            phone=phone,
            address=address,
            date_of_birth=date_of_birth,
            hospital_id=hospital_id
        )
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Failed to create patient record'
            }), 500
        
        logger.info(f"Patient registered by {current_user.username}: {patient.uhid}")
        
        return jsonify({
            'success': True,
            'patient': PatientService.get_patient_summary(patient),
            'duplicates': duplicates,
            'message': f'Patient {patient.display_name} registered successfully'
        }), 201
        
    except Exception as e:
        logger.exception("Error registering patient")
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


# ─────────────────────────────────────────────────────────────
# PATIENT SEARCH & LOOKUP
# ─────────────────────────────────────────────────────────────

@patients_api_bp.route('/search', methods=['GET'])
@patient_access_required
def search_patients():
    """
    Search patients by UHID, name, or phone.
    Returns multiple results sorted by relevance.
    
    Query parameters:
        q: Search query (UHID, name, or phone) — required
        limit: Max results (1-100, default: 20)
    
    Response:
    {
        "success": true,
        "patients": [{ id, uhid, name, phone, age, ... }],
        "total": 5
    }
    """
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', '20')), 100)
        
        if not query or len(query) < 1:
            return jsonify({
                'success': False,
                'error': 'Search query required (minimum 1 character)'
            }), 400
        
        # Search patients
        patients = PatientService.search_patients(query, limit=limit)
        
        results = [PatientService.get_patient_summary(p) for p in patients]
        
        logger.debug(f"Patient search by {current_user.username}: '{query}' → {len(results)} results")
        
        return jsonify({
            'success': True,
            'patients': results,
            'total': len(results)
        }), 200
        
    except Exception as e:
        logger.exception("Error searching patients")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500


@patients_api_bp.route('/by-uhid/<uhid>', methods=['GET'])
@patient_access_required
def get_by_uhid(uhid):
    """
    Get patient by UHID (preferred for returning patients).
    
    Response:
    {
        "success": true,
        "patient": { id, uhid, name, ... },
        "history": {
            "lab_orders": [...],
            "prescriptions": [...],
            "appointments": [...]
        }
    }
    """
    try:
        patient = PatientService.get_patient_by_uhid(uhid)
        
        if not patient:
            return jsonify({
                'success': False,
                'error': f'Patient with UHID {uhid} not found'
            }), 404
        
        return _get_patient_with_history(patient)
        
    except Exception as e:
        logger.exception(f"Error fetching patient by UHID: {uhid}")
        return jsonify({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }), 500


@patients_api_bp.route('/<int:patient_id>', methods=['GET'])
@patient_access_required
def get_patient(patient_id):
    """
    Get patient details by ID with full history.
    
    Response:
    {
        "success": true,
        "patient": {...},
        "history": {...}
    }
    """
    try:
        patient = PatientService.get_patient_by_id(patient_id)
        
        if not patient:
            return jsonify({
                'success': False,
                'error': f'Patient not found'
            }), 404
        
        return _get_patient_with_history(patient)
        
    except Exception as e:
        logger.exception(f"Error fetching patient {patient_id}")
        return jsonify({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }), 500


@patients_api_bp.route('/<int:patient_id>/history', methods=['GET'])
@patients_bp.route('/<int:patient_id>/history', methods=['GET'])
@patient_history_access_required
def get_patient_history(patient_id):
    """Centralized patient history for reception and pharmacy workflows."""
    try:
        page = request.args.get('page', '1')
        limit = request.args.get('limit', str(PatientHistoryService.DEFAULT_LIMIT))
        payload = PatientHistoryService.get_patient_history_payload(
            patient_id=patient_id,
            page=page,
            limit=limit,
        )

        if not payload:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404

        return jsonify(payload), 200

    except Exception as e:
        logger.exception(f"Error loading centralized history for patient {patient_id}")
        return jsonify({
            'success': False,
            'error': f'History lookup failed: {str(e)}'
        }), 500


def _get_patient_with_history(patient):
    """
    Get patient data with complete history.
    Helper function for get endpoints.
    """
    summary = PatientService.get_patient_summary(patient)
    
    # Load patient history
    lab_orders = LabOrder.query.filter_by(patient_id=patient.id)\
        .order_by(LabOrder.created_at.desc()).limit(10).all()
    
    prescriptions = Prescription.query.filter_by(patient_id=patient.id)\
        .order_by(Prescription.prescribed_at.desc()).limit(10).all()
    
    appointments = Appointment.query.filter_by(patient_id=patient.id)\
        .order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    health_records = HealthData.query.filter_by(patient_id=patient.id)\
        .order_by(HealthData.recorded_at.desc()).limit(5).all()
    
    # Add extended info
    summary.update({
        'medical_history': patient.medical_history,
        'allergies': patient.allergies,
        'blood_type': patient.blood_type,
        'weight': patient.weight,
        'height': patient.height,
        'emergency_contact': patient.emergency_contact,
        'address': patient.address
    })
    
    return jsonify({
        'success': True,
        'patient': summary,
        'history': {
            'lab_orders_count': len(lab_orders),
            'lab_orders': _serialize_lab_orders(lab_orders),
            'prescriptions_count': len(prescriptions),
            'prescriptions': _serialize_prescriptions(prescriptions),
            'appointments_count': len(appointments),
            'appointments': _serialize_appointments(appointments),
            'health_records_count': len(health_records),
            'health_records': _serialize_health_data(health_records)
        }
    }), 200


def _serialize_lab_orders(orders):
    """Serialize lab orders for API response"""
    return [{
        'id': o.id,
        'test_name': o.test_name,
        'test_category': o.test_category,
        'status': o.status,
        'source_type': o.source_type,
        'created_at': o.created_at.isoformat() if o.created_at else None,
        'doctor_name': o.doctor.user.username if o.doctor else 'Walk-in'
    } for o in orders]


def _serialize_prescriptions(prescriptions):
    """Serialize prescriptions for API response"""
    return [{
        'id': p.id,
        'diagnosis': p.diagnosis,
        'medicines': p.medicines,
        'prescribed_at': p.prescribed_at.isoformat() if p.prescribed_at else None,
        'doctor': p.doctor.user.username if p.doctor else 'Unknown'
    } for p in prescriptions]


def _serialize_appointments(appointments):
    """Serialize appointments for API response"""
    return [{
        'id': a.id,
        'appointment_date': a.appointment_date.isoformat() if a.appointment_date else None,
        'reason': a.reason,
        'status': a.status,
        'doctor': a.doctor.user.username if a.doctor else 'Unknown'
    } for a in appointments]


def _serialize_health_data(records):
    """Serialize health data for API response"""
    return [{
        'id': h.id,
        'recorded_at': h.recorded_at.isoformat() if h.recorded_at else None,
        'bmi': h.bmi,
        'heart_rate': h.heart_rate,
        'systolic_bp': h.systolic_bp,
        'diastolic_bp': h.diastolic_bp,
        'fasting_sugar': h.fasting_sugar
    } for h in records]


# ─────────────────────────────────────────────────────────────
# DUPLICATE DETECTION
# ─────────────────────────────────────────────────────────────

@patients_api_bp.route('/find-similar', methods=['POST'])
@patient_access_required
def find_similar():
    """
    Find potentially duplicate patients using name, phone, age.
    Used during patient registration for duplicate warnings.
    
    Request body:
    {
        "name": "Ravi Kumar",
        "phone": "9876543210",
        "age": 35,
        "threshold": 0.7
    }
    
    Response:
    {
        "success": true,
        "similar": [{ id, uhid, name, phone, age, similarity, reason }],
        "total": 2
    }
    """
    try:
        data = request.get_json() or {}
        
        name = data.get('name', '').strip() or None
        phone = data.get('phone', '').strip() or None
        age = data.get('age')
        threshold = float(data.get('threshold', 0.7))
        
        # Validate at least one search criterion
        if not name and not phone and not age:
            return jsonify({
                'success': False,
                'error': 'Provide at least one of: name, phone, or age'
            }), 400
        
        # Convert age to int if provided
        if age:
            try:
                age = int(age)
            except (ValueError, TypeError):
                age = None
        
        # Find similar patients
        similar = PatientService.find_similar_patients(
            name=name,
            phone=phone,
            age=age,
            threshold=threshold
        )
        
        results = [{
            'id': s['patient'].id,
            'uhid': s['patient'].uhid,
            'name': s['patient'].full_name,
            'phone': s['patient'].phone,
            'age': s['patient'].age,
            'gender': s['patient'].gender,
            'is_walk_in': s['patient'].is_walk_in,
            'similarity': s['similarity'],
            'reason': s['reason'],
            'created_at': s['patient'].created_at.isoformat() if s['patient'].created_at else None
        } for s in similar]
        
        logger.debug(f"Similar patient search: {len(results)} results")
        
        return jsonify({
            'success': True,
            'similar': results,
            'total': len(results)
        }), 200
        
    except Exception as e:
        logger.exception("Error finding similar patients")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500


# ─────────────────────────────────────────────────────────────
# PATIENT UPDATES
# ─────────────────────────────────────────────────────────────

@patients_api_bp.route('/<int:patient_id>', methods=['PUT'])
@patient_access_required
def update_patient(patient_id):
    """
    Update patient information.
    
    Request body:
    {
        "phone": "9876543210",
        "address": "New Address",
        "medical_history": "...",
        "allergies": "...",
        "blood_type": "O+"
    }
    
    Response:
    {
        "success": true,
        "patient": {...}
    }
    """
    try:
        patient = PatientService.get_patient_by_id(patient_id)
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
        
        data = request.get_json() or {}
        
        # Update fields (exclude protected fields)
        protected_fields = {'id', 'uhid', 'user_id', 'created_at', 'is_walk_in'}
        
        for key, value in data.items():
            if key not in protected_fields and hasattr(patient, key):
                setattr(patient, key, value)
        
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Patient {patient.uhid} updated by {current_user.username}")
        
        return jsonify({
            'success': True,
            'patient': PatientService.get_patient_summary(patient),
            'message': 'Patient information updated'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error updating patient {patient_id}")
        return jsonify({
            'success': False,
            'error': f'Update failed: {str(e)}'
        }), 500


# ─────────────────────────────────────────────────────────────
# STATISTICS & REPORTING
# ─────────────────────────────────────────────────────────────

@patients_api_bp.route('/list', methods=['GET'])
@patient_access_required
def list_patients():
    """
    List all patients with pagination.
    
    Query parameters:
        page: Page number (default: 1)
        limit: Results per page (default: 20, max: 100)
        walk_in_only: Filter walk-in only (default: false)
    
    Response:
    {
        "success": true,
        "patients": [...],
        "total": 150,
        "page": 1,
        "pages": 8
    }
    """
    try:
        page = max(1, int(request.args.get('page', '1')))
        limit = min(int(request.args.get('limit', '20')), 100)
        walk_in_only = request.args.get('walk_in_only', 'false').lower() == 'true'
        
        query = Patient.query
        
        if walk_in_only:
            query = query.filter_by(is_walk_in=True)
        
        total = query.count()
        pages = (total + limit - 1) // limit
        
        patients = query.order_by(Patient.created_at.desc())\
            .limit(limit)\
            .offset((page - 1) * limit)\
            .all()
        
        return jsonify({
            'success': True,
            'patients': [PatientService.get_patient_summary(p) for p in patients],
            'total': total,
            'page': page,
            'limit': limit,
            'pages': pages
        }), 200
        
    except Exception as e:
        logger.exception("Error listing patients")
        return jsonify({
            'success': False,
            'error': f'Failed to list patients: {str(e)}'
        }), 500


@patients_api_bp.route('/stats', methods=['GET'])
@patient_access_required
def get_stats():
    """
    Get patient statistics.
    
    Response:
    {
        "success": true,
        "stats": {
            "total_patients": 1500,
            "walk_in_count": 800,
            "registered_count": 700,
            "today_registrations": 15
        }
    }
    """
    try:
        from sqlalchemy import func
        from datetime import date
        
        total = Patient.query.count()
        walk_in_count = Patient.query.filter_by(is_walk_in=True).count()
        registered_count = Patient.query.filter_by(is_walk_in=False).count()
        
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_registrations = Patient.query.filter(
            Patient.created_at >= today_start
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_patients': total,
                'walk_in_count': walk_in_count,
                'registered_count': registered_count,
                'today_registrations': today_registrations
            }
        }), 200
        
    except Exception as e:
        logger.exception("Error getting patient stats")
        return jsonify({
            'success': False,
            'error': f'Failed to get stats: {str(e)}'
        }), 500


# ------------------------------------------------------------------
# /patients/* compatibility routes (same behavior as /api/patients/*)
# ------------------------------------------------------------------

@patients_bp.route('/register', methods=['POST'])
def register_patient_alias():
    return register_patient()

@patients_api_bp.route('/create', methods=['POST'])
@patients_bp.route('/create', methods=['POST'])
def create_patient_alias():
    return register_patient()


@patients_bp.route('/search', methods=['GET'])
def search_patients_alias():
    return search_patients()


@patients_bp.route('/find-similar', methods=['POST'])
def find_similar_alias():
    return find_similar()


@patients_bp.route('/by-uhid/<uhid>', methods=['GET'])
def get_by_uhid_alias(uhid):
    return get_by_uhid(uhid)


@patients_bp.route('/<int:patient_id>', methods=['GET'])
def get_patient_alias(patient_id):
    return get_patient(patient_id)
