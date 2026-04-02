"""
Walk-in Patient Management Module
- Register new walk-in patients
- Search and find existing patients
- Detect potential duplicates
- Manage patient selection flow
Accessible by: RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models.models import db, Patient, Doctor, UserRole, Hospital, LabOrder, Billing
from app.services.patient_service import PatientService
from datetime import datetime, date
from functools import wraps
import logging

logger = logging.getLogger(__name__)

walkin_bp = Blueprint('walkin', __name__, url_prefix='/walkin')


def lab_staff_access(f):
    """Allow RECEPTIONIST, LAB_STAFF, DOCTOR, ADMIN access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.staff_login'))
        if current_user.role not in (UserRole.RECEPTIONIST, UserRole.LAB_STAFF, UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# API Endpoints for Walk-in Patient Management
# ─────────────────────────────────────────────────────────────

@walkin_bp.route('/api/register', methods=['POST'])
@login_required
@lab_staff_access
def register_walkin_patient():
    """
    Register a new walk-in patient.
    
    Required fields: first_name, last_name, age, gender
    Optional fields: phone, address
    
    Response: {
        'success': bool,
        'patient': { id, uhid, name, ... },
        'error': str (if not successful)
    }
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        age_raw = data.get('age', '')
        gender = data.get('gender', '').strip()
        
        if not first_name:
            return jsonify({'success': False, 'error': 'First name is required'}), 400
        
        if age_raw is None or str(age_raw).strip() == '':
            return jsonify({'success': False, 'error': 'Age is required'}), 400
        
        if not gender:
            return jsonify({'success': False, 'error': 'Gender is required'}), 400
        
        # Parse age
        try:
            age = int(str(age_raw).strip())
            if age < 0 or age > 150:
                return jsonify({'success': False, 'error': 'Invalid age'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Age must be a number'}), 400
        
        # Get optional fields
        phone = data.get('phone', '').strip() or None
        address = data.get('address', '').strip() or None

        if phone and not PatientService.validate_phone(phone):
            return jsonify({'success': False, 'error': 'Invalid phone format'}), 400
        
        # Check for duplicates if phone provided
        if phone:
            similar = PatientService.find_similar_patients(phone=phone, threshold=0.8)
            if similar:
                return jsonify({
                    'success': False,
                    'error': 'Possible existing patient found',
                    'duplicates': [{
                        'id': s['patient'].id,
                        'uhid': s['patient'].uhid,
                        'name': s['patient'].full_name,
                        'phone': s['patient'].phone,
                        'similarity': s['similarity'],
                        'reason': s['reason']
                    } for s in similar],
                    'code': 'POSSIBLE_DUPLICATE',
                    'message': 'Possible existing patient found'
                }), 409
        
        # Get hospital ID
        hospital = Hospital.query.first()
        hospital_id = hospital.id if hospital else None
        
        # Create walk-in patient
        patient = PatientService.create_walk_in_patient(
            name=f"{first_name} {last_name}".strip(),
            age=age,
            gender=gender,
            phone=phone,
            address=address,
            hospital_id=hospital_id
        )
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Failed to create patient record'
            }), 500
        
        logger.info(f"Walk-in patient registered: {patient.uhid} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'patient': PatientService.get_patient_summary(patient),
            'message': f'Patient {patient.display_name} registered successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error registering walk-in patient: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


@walkin_bp.route('/api/search', methods=['GET'])
@login_required
@lab_staff_access
def search_patients():
    """
    Search for patients by UHID, name, or phone.
    
    Query parameters:
        q: search query (required)
        limit: max results (default: 10)
    
    Response: {
        'success': bool,
        'patients': [{ id, uhid, name, phone, ... }],
        'total': int
    }
    """
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 100)  # Max 100
        
        if not query or len(query) < 1:
            return jsonify({
                'success': False,
                'error': 'Search query required (min 1 character)'
            }), 400
        
        # Search patients
        patients = PatientService.search_patients(query, limit=limit)
        
        return jsonify({
            'success': True,
            'patients': [PatientService.get_patient_summary(p) for p in patients],
            'total': len(patients)
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching patients: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500


@walkin_bp.route('/api/find-similar', methods=['POST'])
@login_required
@lab_staff_access
def find_similar_patients():
    """
    Find patients with similar name, phone, or age.
    Used for duplicate detection.
    
    Request body:
        name (optional): patient name
        phone (optional): patient phone
        age (optional): patient age (will search ±2 years)
        threshold (optional): similarity threshold 0-1 (default: 0.7)
    
    Response: {
        'success': bool,
        'similar': [{ id, uhid, name, phone, similarity, reason }],
        'total': int
    }
    """
    try:
        data = request.get_json() or {}
        
        name = data.get('name', '').strip() or None
        phone = data.get('phone', '').strip() or None
        age = data.get('age')
        threshold = float(data.get('threshold', 0.7))
        
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
        
        return jsonify({
            'success': True,
            'similar': [{
                'id': s['patient'].id,
                'uhid': s['patient'].uhid,
                'name': s['patient'].full_name,
                'phone': s['patient'].phone,
                'age': s['patient'].age,
                'gender': s['patient'].gender,
                'similarity': s['similarity'],
                'reason': s['reason'],
                'is_walk_in': s['patient'].is_walk_in
            } for s in similar],
            'total': len(similar)
        }), 200
        
    except Exception as e:
        logger.error(f"Error finding similar patients: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500


@walkin_bp.route('/api/get/<int:patient_id>', methods=['GET'])
@login_required
@lab_staff_access
def get_patient(patient_id):
    """
    Get detailed patient information.
    
    Response: {
        'success': bool,
        'patient': { id, uhid, name, age, gender, phone, address, ... }
    }
    """
    try:
        patient = PatientService.get_patient_by_id(patient_id)
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
        
        # Get additional history
        from app.models.models import LabOrder, Prescription, Appointment
        
        lab_count = LabOrder.query.filter_by(patient_id=patient_id).count()
        prescription_count = Prescription.query.filter_by(patient_id=patient_id).count()
        appointment_count = Appointment.query.filter_by(patient_id=patient_id).count()
        
        summary = PatientService.get_patient_summary(patient)
        summary.update({
            'lab_orders_count': lab_count,
            'prescriptions_count': prescription_count,
            'appointments_count': appointment_count,
            'blood_type': patient.blood_type,
            'allergies': patient.allergies,
            'medical_history': patient.medical_history,
            'address': patient.address
        })
        
        return jsonify({
            'success': True,
            'patient': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting patient {patient_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve patient: {str(e)}'
        }), 500


@walkin_bp.route('/api/get-by-uhid/<uhid>', methods=['GET'])
@login_required
@lab_staff_access
def get_patient_by_uhid(uhid):
    """
    Get patient by UHID.
    
    Response: {
        'success': bool,
        'patient': { ... }
    }
    """
    try:
        patient = PatientService.get_patient_by_uhid(uhid.upper())
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
        
        return jsonify({
            'success': True,
            'patient': PatientService.get_patient_summary(patient)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting patient by UHID {uhid}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@walkin_bp.route('/api/update/<int:patient_id>', methods=['PUT'])
@login_required
@lab_staff_access
def update_patient(patient_id):
    """
    Update patient information.
    
    Allowed updates: age, phone, address, allergies, medical_history, emergency_contact
    
    Response: {
        'success': bool,
        'patient': { ... }
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
        
        # Only allow updating specific fields
        allowed_updates = {
            'age': int,
            'phone': str,
            'address': str,
            'allergies': str,
            'medical_history': str,
            'emergency_contact': str,
            'blood_type': str
        }
        
        updates = {}
        for field, converter in allowed_updates.items():
            if field in data:
                try:
                    value = data[field]
                    if value is None:
                        updates[field] = None
                    else:
                        updates[field] = converter(value)
                except (ValueError, TypeError) as e:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid value for {field}: {str(e)}'
                    }), 400
        
        # Apply updates
        updated = PatientService.update_patient(patient, **updates)
        
        if not updated:
            return jsonify({
                'success': False,
                'error': 'Failed to update patient'
            }), 500
        
        logger.info(f"Patient {patient.uhid} updated by {current_user.username}")
        
        return jsonify({
            'success': True,
            'patient': PatientService.get_patient_summary(updated),
            'message': 'Patient information updated'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Update failed: {str(e)}'
        }), 500


@walkin_bp.route('/api/list', methods=['GET'])
@login_required
@lab_staff_access
def list_patients():
    """
    Get list of all patients with pagination.
    
    Query parameters:
        is_walk_in (optional): filter by walk-in status (true/false)
        limit: max results per page (default: 20, max: 100)
        offset: pagination offset (default: 0)
    
    Response: {
        'success': bool,
        'patients': [{ ... }],
        'total': int,
        'limit': int,
        'offset': int
    }
    """
    try:
        # Get parameters
        is_walk_in_str = request.args.get('is_walk_in', '').lower()
        is_walk_in = None
        if is_walk_in_str == 'true':
            is_walk_in = True
        elif is_walk_in_str == 'false':
            is_walk_in = False
        
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Get hospital ID (for multi-tenant support)
        hospital_id = None
        
        # Get patients
        patients, total = PatientService.get_all_patients(
            hospital_id=hospital_id,
            is_walk_in=is_walk_in,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'patients': [PatientService.get_patient_summary(p) for p in patients],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing patients: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ─────────────────────────────────────────────────────────────
# UI Endpoints - Return HTML pages
# ─────────────────────────────────────────────────────────────

@walkin_bp.route('/register', methods=['GET'])
@login_required
@lab_staff_access
def register_page():
    """Display walk-in patient registration form"""
    return render_template('walkin/register.html')


@walkin_bp.route('/select', methods=['GET'])
@login_required
@lab_staff_access
def select_patient_page():
    """Display patient selection/search interface"""
    return render_template('walkin/select.html')
