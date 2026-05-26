"""
Bed Management Dashboard — Visual ward map with real-time bed status tracking.
Supports Available / Occupied / Reserved / Maintenance states per bed.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import db, Bed, Patient, IPAdmission, UserRole
from functools import wraps
from sqlalchemy import func

bed_management_bp = Blueprint('bed_management', __name__, url_prefix='/beds')

WARD_TYPES = ['ICU', 'General Ward', 'Emergency', 'Private Room', 'Semi-Private']


# ─── Access Decorator ───────────────────────────────────────────
def bed_access_required(f):
    """Allow DOCTOR, HOST, NURSE, RECEPTIONIST roles."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access Bed Management.', 'danger')
            return redirect(url_for('auth.staff_login'))
        allowed = (UserRole.DOCTOR, UserRole.HOST, UserRole.NURSE, UserRole.RECEPTIONIST)
        if current_user.role not in allowed:
            flash('Access denied. Bed management requires Doctor, Host, Nurse, or Receptionist credentials.', 'danger')
            return redirect(url_for('auth.choose_login'))
        return f(*args, **kwargs)
    return decorated


# ─── Helpers ────────────────────────────────────────────────────
def _bed_status(bed):
    """Return a semantic status string for a bed."""
    if getattr(bed, 'maintenance', False):
        return 'Maintenance'
    if getattr(bed, 'reserved', False):
        return 'Reserved'
    if bed.is_occupied:
        return 'Occupied'
    return 'Available'


def _bed_to_dict(bed):
    """Serialize a Bed row into a JSON-friendly dict."""
    patient = None
    if bed.patient_id:
        p = Patient.query.get(bed.patient_id)
        if p:
            patient = {'id': p.id, 'name': p.full_name, 'uhid': p.uhid}

    return {
        'id': bed.id,
        'ward_type': bed.ward_type,
        'bed_number': bed.bed_number,
        'status': _bed_status(bed),
        'is_occupied': bed.is_occupied,
        'patient': patient,
    }


# ─── Dashboard ──────────────────────────────────────────────────
@bed_management_bp.route('/dashboard')
@login_required
@bed_access_required
def dashboard():
    """Visual ward map with bed status cards."""
    beds = Bed.query.order_by(Bed.ward_type, Bed.bed_number).all()

    # Group beds by ward
    wards = {}
    for bed in beds:
        ward = bed.ward_type or 'Unassigned'
        if ward not in wards:
            wards[ward] = []
        wards[ward].append(_bed_to_dict(bed))

    # Compute aggregate stats
    total = len(beds)
    occupied = sum(1 for b in beds if b.is_occupied)
    available = total - occupied
    occupancy_rate = round((occupied / total * 100), 1) if total > 0 else 0

    # Patient list for assignment dropdowns
    patients = Patient.query.order_by(Patient.name).all()

    return render_template(
        'beds/dashboard.html',
        wards=wards,
        ward_types=WARD_TYPES,
        total=total,
        occupied=occupied,
        available=available,
        occupancy_rate=occupancy_rate,
        patients=patients,
    )


# ─── API: Update Bed Status ────────────────────────────────────
@bed_management_bp.route('/api/update', methods=['POST'])
@login_required
@bed_access_required
def api_update():
    """Update a bed's status (Available / Reserved / Maintenance)."""
    data = request.get_json(silent=True) or {}
    bed_id = data.get('bed_id')
    new_status = data.get('status')  # Available, Reserved, Maintenance

    if not bed_id or not new_status:
        return jsonify({'success': False, 'error': 'bed_id and status are required.'}), 400

    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'error': 'Bed not found.'}), 404

    valid_statuses = ('Available', 'Reserved', 'Maintenance', 'Occupied')
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': f'Invalid status. Choose from: {", ".join(valid_statuses)}'}), 400

    if new_status == 'Available':
        bed.is_occupied = False
        bed.patient_id = None
        # Clear extended flags if they exist
        if hasattr(bed, 'reserved'):
            bed.reserved = False
        if hasattr(bed, 'maintenance'):
            bed.maintenance = False
    elif new_status == 'Maintenance':
        bed.is_occupied = False
        bed.patient_id = None
        if hasattr(bed, 'maintenance'):
            bed.maintenance = True
        if hasattr(bed, 'reserved'):
            bed.reserved = False
    elif new_status == 'Reserved':
        bed.is_occupied = False
        if hasattr(bed, 'reserved'):
            bed.reserved = True
        if hasattr(bed, 'maintenance'):
            bed.maintenance = False
    elif new_status == 'Occupied':
        bed.is_occupied = True
        if hasattr(bed, 'reserved'):
            bed.reserved = False
        if hasattr(bed, 'maintenance'):
            bed.maintenance = False

    db.session.commit()
    return jsonify({'success': True, 'bed': _bed_to_dict(bed)})


# ─── API: Assign Patient to Bed ────────────────────────────────
@bed_management_bp.route('/api/assign', methods=['POST'])
@login_required
@bed_access_required
def api_assign():
    """Assign a patient to a specific bed."""
    data = request.get_json(silent=True) or {}
    bed_id = data.get('bed_id')
    patient_id = data.get('patient_id')

    if not bed_id or not patient_id:
        return jsonify({'success': False, 'error': 'bed_id and patient_id are required.'}), 400

    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'error': 'Bed not found.'}), 404

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found.'}), 404

    if bed.is_occupied and bed.patient_id != patient_id:
        return jsonify({'success': False, 'error': 'Bed is already occupied by another patient.'}), 409

    bed.is_occupied = True
    bed.patient_id = patient.id
    if hasattr(bed, 'reserved'):
        bed.reserved = False
    if hasattr(bed, 'maintenance'):
        bed.maintenance = False

    db.session.commit()
    return jsonify({'success': True, 'bed': _bed_to_dict(bed)})


# ─── API: Release Bed ──────────────────────────────────────────
@bed_management_bp.route('/api/release', methods=['POST'])
@login_required
@bed_access_required
def api_release():
    """Release a bed — mark it Available and clear the patient."""
    data = request.get_json(silent=True) or {}
    bed_id = data.get('bed_id')

    if not bed_id:
        return jsonify({'success': False, 'error': 'bed_id is required.'}), 400

    bed = Bed.query.get(bed_id)
    if not bed:
        return jsonify({'success': False, 'error': 'Bed not found.'}), 404

    bed.is_occupied = False
    bed.patient_id = None
    if hasattr(bed, 'reserved'):
        bed.reserved = False
    if hasattr(bed, 'maintenance'):
        bed.maintenance = False

    db.session.commit()
    return jsonify({'success': True, 'bed': _bed_to_dict(bed)})


# ─── API: Stats ────────────────────────────────────────────────
@bed_management_bp.route('/api/stats')
@login_required
@bed_access_required
def api_stats():
    """Return bed statistics as JSON."""
    beds = Bed.query.all()
    total = len(beds)
    occupied = sum(1 for b in beds if b.is_occupied)
    available = total - occupied

    # Per-ward breakdown
    ward_stats = {}
    for bed in beds:
        ward = bed.ward_type or 'Unassigned'
        if ward not in ward_stats:
            ward_stats[ward] = {'total': 0, 'occupied': 0, 'available': 0}
        ward_stats[ward]['total'] += 1
        if bed.is_occupied:
            ward_stats[ward]['occupied'] += 1
        else:
            ward_stats[ward]['available'] += 1

    return jsonify({
        'success': True,
        'total': total,
        'occupied': occupied,
        'available': available,
        'occupancy_rate': round((occupied / total * 100), 1) if total > 0 else 0,
        'ward_stats': ward_stats,
    })
