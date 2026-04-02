"""
Pharmacy Operations Module â€” Prescription-based dispensing workflow
Accessible by: PHARMACIST (full), DOCTOR (view status, create orders), ADMIN/HOST
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, PharmacyOrder, PharmacySale, Prescription, Patient, Doctor, UserRole, Medicine, Visit)
from app.services.patient_history_service import PatientHistoryService
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)

pharmacy_ops_bp = Blueprint('pharmacy_ops', __name__, url_prefix='/pharmacy-ops')


def pharmacy_access_required(f):
    """Allow PHARMACIST, DOCTOR, HOST, ADMIN"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access the pharmacy module.', 'danger')
            return redirect(url_for('auth.staff_login', role='PHARMACIST'))
        allowed = [UserRole.PHARMACIST, UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN]
        if current_user.role not in allowed:
            flash('Access denied. Pharmacist or Doctor login required.', 'danger')
            return redirect(url_for('auth.staff_login', role='PHARMACIST', switch='1'))
        return f(*args, **kwargs)
    return decorated


def pharmacist_only(f):
    """Only PHARMACIST and HOST/ADMIN"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.staff_login', role='PHARMACIST'))
        allowed = [UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN]
        if current_user.role not in allowed:
            flash('Access denied. Pharmacist login required.', 'danger')
            return redirect(url_for('auth.staff_login', role='PHARMACIST', switch='1'))
        return f(*args, **kwargs)
    return decorated


def _record_pharmacy_visit(patient_id, doctor_id=None, notes=None, visit_date=None):
    visit = Visit(
        patient_id=patient_id,
        visit_type='PHARMACY',
        doctor_id=doctor_id,
        notes=notes,
        visit_date=visit_date or datetime.utcnow(),
    )
    db.session.add(visit)
    return visit


# â”€â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/')
@pharmacy_ops_bp.route('/dashboard')
@pharmacy_access_required
@login_required
def dashboard():
    """Pharmacy dashboard â€” view prescriptions awaiting dispensing"""
    total = PharmacyOrder.query.count()
    pending = PharmacyOrder.query.filter_by(status='Pending').count()
    dispensed = PharmacyOrder.query.filter_by(status='Dispensed').count()

    status_filter = request.args.get('status', 'all')
    search_q = request.args.get('search', '').strip()

    query = PharmacyOrder.query

    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if search_q:
        query = query.join(Patient, PharmacyOrder.patient_id == Patient.id).filter(
            db.or_(
                Patient.first_name.ilike(f'%{search_q}%'),
                Patient.last_name.ilike(f'%{search_q}%'),
                PharmacyOrder.medicine_name.ilike(f'%{search_q}%')
            )
        )

    # If doctor, only show their own orders
    if current_user.role == UserRole.DOCTOR and hasattr(current_user, 'doctor') and current_user.doctor:
        query = query.filter_by(doctor_id=current_user.doctor.id)

    orders = query.order_by(PharmacyOrder.created_at.desc()).all()

    # Get recent prescriptions that don't have pharmacy orders yet (for pharmacist)
    unprocessed_prescriptions = []
    if current_user.role in (UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN):
        # Prescriptions without any pharmacy order
        existing_rx_ids = db.session.query(PharmacyOrder.prescription_id).filter(
            PharmacyOrder.prescription_id.isnot(None)
        ).distinct().all()
        existing_rx_ids = [x[0] for x in existing_rx_ids]

        unprocessed_prescriptions = Prescription.query.filter(
            ~Prescription.id.in_(existing_rx_ids) if existing_rx_ids else True
        ).order_by(Prescription.prescribed_at.desc()).limit(20).all()

    return render_template('pharmacy_ops/dashboard.html',
                           orders=orders,
                           total=total, pending=pending, dispensed=dispensed,
                           status_filter=status_filter, search_q=search_q,
                           unprocessed_prescriptions=unprocessed_prescriptions)


@pharmacy_ops_bp.route('/patient-history')
@pharmacy_access_required
@login_required
def patient_history_page():
    return render_template('pharmacy_ops/patient_history.html')

@pharmacy_ops_bp.route('/prescription/<int:id>/view')
@pharmacy_access_required
@login_required
def view_prescription(id):
    """View full hospital-grade prescription sheet"""
    prescription = Prescription.query.get_or_404(id)
    return render_template('patient/view_prescription.html', prescription=prescription)

# â”€â”€â”€ Dispense Medication â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/dispense', methods=['POST'])
@pharmacist_only
@login_required
def dispense():
    """Mark a pharmacy order as dispensed"""
    data = request.get_json()
    order_id = data.get('order_id')

    order = PharmacyOrder.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    if order.status == 'Dispensed':
        return jsonify({'success': False, 'error': 'Order is already dispensed'}), 400

    # Real-world logic fix: Decrease stock in inventory
    from app.models.models import Medicine
    
    # Try to find the exact medicine in the inventory (ignoring case)
    medicine = Medicine.query.filter(
        db.func.lower(Medicine.name) == db.func.lower(order.medicine_name.strip())
    ).first()
    
    quantity_to_dispense = int(order.quantity) if order.quantity else 1
    
    if medicine:
        if medicine.stock < quantity_to_dispense:
            return jsonify({
                'success': False, 
                'error': f'Insufficient stock. Only {medicine.stock} units of {medicine.name} available.'
            }), 400
        medicine.stock -= quantity_to_dispense
        logger.info(f"Inventory updated: {medicine.name} stock reduced by {quantity_to_dispense}. Remaining: {medicine.stock}")

    order.status = 'Dispensed'
    dispensed_at = datetime.utcnow()
    order.dispensed_at = dispensed_at
    order.notes = data.get('notes', order.notes)

    if not order.sale_records.first():
        sale = PharmacySale(
            patient_id=order.patient_id,
            pharmacy_order_id=order.id,
            medicine_name=order.medicine_name,
            quantity=quantity_to_dispense,
            price=float(medicine.price or 0) if medicine else 0.0,
            sold_at=dispensed_at,
            notes=order.notes,
        )
        db.session.add(sale)

    _record_pharmacy_visit(
        patient_id=order.patient_id,
        doctor_id=order.doctor_id,
        notes=f"Medicine dispensed: {order.medicine_name} x{quantity_to_dispense}",
        visit_date=dispensed_at,
    )
    
    try:
        db.session.commit()
        logger.info(f"Pharmacy order #{order_id} dispensed by user {current_user.id}")
        return jsonify({'success': True, 'message': 'Medication dispensed successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error dispensing order #{order_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Database transaction failed: ' + str(e)}), 500


# â”€â”€â”€ Create order from prescription â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/create-from-prescription', methods=['POST'])
@pharmacy_access_required
@login_required
def create_from_prescription():
    """Create pharmacy orders from a prescription â€” uses PrescriptionMedicine model"""
    data = request.get_json()
    prescription_id = data.get('prescription_id')

    rx = Prescription.query.get(prescription_id)
    if not rx:
        return jsonify({'success': False, 'error': 'Prescription not found'}), 404

    # Check if orders already exist for this prescription
    existing = PharmacyOrder.query.filter_by(prescription_id=rx.id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Pharmacy orders already created for this prescription'}), 400

    from app.models.models import PrescriptionMedicine
    # Use the PrescriptionMedicine relationship for structured medicines
    medicine_items = PrescriptionMedicine.query.filter_by(prescription_id=rx.id).all()

    created_count = 0

    if medicine_items:
        # Use structured PrescriptionMedicine entries
        for med in medicine_items:
            order = PharmacyOrder(
                patient_id=rx.patient_id,
                doctor_id=rx.doctor_id,
                prescription_id=rx.id,
                medicine_name=med.medicine_name,
                quantity=data.get('quantity', 1),
                dosage=f"{med.dosage or ''} | {med.frequency or ''} | {med.duration or ''}",
                status='Pending',
                notes=f"{med.instruction or ''} ({med.food_relation or ''})"
            )
            db.session.add(order)
            created_count += 1
    else:
        # Fallback: Parse legacy medicines text field
        medicines_raw = rx.medicines or ''
        import json as json_mod
        try:
            medicines_list = json_mod.loads(medicines_raw)
            if isinstance(medicines_list, str):
                medicines_list = [medicines_list]
        except (json_mod.JSONDecodeError, TypeError):
            medicines_list = [m.strip() for m in medicines_raw.split(',') if m.strip()]

        if not medicines_list:
            medicines_list = [medicines_raw] if medicines_raw.strip() else []

        for med_name in medicines_list:
            if not med_name:
                continue
            order = PharmacyOrder(
                patient_id=rx.patient_id,
                doctor_id=rx.doctor_id,
                prescription_id=rx.id,
                medicine_name=med_name,
                quantity=data.get('quantity', 1),
                dosage=rx.dosage if hasattr(rx, 'dosage') else '',
                status='Pending'
            )
            db.session.add(order)
            created_count += 1

    db.session.commit()
    logger.info(f"{created_count} pharmacy orders created from prescription #{prescription_id}")
    return jsonify({'success': True, 'created': created_count})


# â”€â”€â”€ Doctor create direct order â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/create-order', methods=['POST'])
@login_required
def create_order():
    """Doctor creates a direct pharmacy order (without prescription)"""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
        return jsonify({'success': False, 'error': 'Only doctors can create orders'}), 403

    data = request.get_json()
    patient_id = data.get('patient_id')
    medicine_name = data.get('medicine_name')
    quantity = data.get('quantity', 1)
    dosage = data.get('dosage', '')

    if not patient_id or not medicine_name:
        return jsonify({'success': False, 'error': 'Patient and medicine name required'}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    doctor_id = current_user.doctor.id if hasattr(current_user, 'doctor') and current_user.doctor else None

    order = PharmacyOrder(
        patient_id=patient.id,
        doctor_id=doctor_id,
        medicine_name=medicine_name,
        quantity=quantity,
        dosage=dosage,
        status='Pending'
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({'success': True, 'order_id': order.id})


# â”€â”€â”€ Patient Medicine History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/patient-history/<int:patient_id>')
@pharmacy_access_required
@login_required
def patient_history(patient_id):
    """Get centralized patient history payload for pharmacy usage."""
    page = request.args.get('page', '1')
    limit = request.args.get('limit', str(PatientHistoryService.DEFAULT_LIMIT))
    payload = PatientHistoryService.get_patient_history_payload(patient_id, page=page, limit=limit)
    if not payload:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    return jsonify(payload)


# â”€â”€â”€ Search patients (AJAX) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/search-patients')
@pharmacy_access_required
@login_required
def search_patients():
    """Search patients by UHID, name, or phone for pharmacy workflows."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    patients = Patient.query.filter(
        db.or_(
            Patient.uhid.ilike(f'%{q.upper()}%'),
            Patient.name.ilike(f'%{q}%'),
            Patient.first_name.ilike(f'%{q}%'),
            Patient.last_name.ilike(f'%{q}%'),
            Patient.phone.ilike(f'%{q}%')
        )
    ).limit(10).all()

    return jsonify([{
        'id': p.id,
        'name': p.full_name,
        'uhid': p.uhid,
        'age': p.age,
        'gender': p.gender,
        'phone': p.phone,
        'allergies': p.allergies,
    } for p in patients])


# â”€â”€â”€ Medicine Availability Check API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/check-medicines', methods=['POST'])
@pharmacy_access_required
@login_required
def check_medicines():
    """Check medicines against pharmacy inventory.
    
    Input JSON:  { "medicines": ["Paracetamol", "Amoxicillin"] }
    Output JSON: [
        {"name": "Paracetamol", "status": "available", "stock": 120},
        {"name": "Amoxicillin", "status": "available", "stock": 50},
        {"name": "RandomDrug", "status": "not_available", "stock": 0}
    ]
    """
    data = request.get_json()
    medicine_names = data.get('medicines', [])

    if not medicine_names or not isinstance(medicine_names, list):
        return jsonify({'success': False, 'error': 'Please provide a list of medicine names'}), 400

    # Normalize medicine names using RapidFuzz correction engine
    try:
        from app.services.voice_service import correct_medicine_name
        normalized_names = []
        for name in medicine_names:
            clean = name.strip()
            if not clean:
                continue
            result = correct_medicine_name(clean)
            normalized_names.append(result['name'])
    except Exception:
        normalized_names = [n.strip() for n in medicine_names if n.strip()]

    results = []
    seen = set()

    for clean_name in normalized_names:
        if not clean_name:
            continue
        # Prevent duplicates in results
        if clean_name.lower() in seen:
            continue
        seen.add(clean_name.lower())

        # Case-insensitive lookup in the medicines inventory table
        med = Medicine.query.filter(
            db.func.lower(Medicine.name) == clean_name.lower()
        ).first()

        if med and med.stock > 0:
            results.append({
                'name': med.name,
                'status': 'available',
                'stock': med.stock
            })
        elif med and med.stock == 0:
            results.append({
                'name': med.name,
                'status': 'not_available',
                'stock': 0
            })
        else:
            results.append({
                'name': clean_name,
                'status': 'not_available',
                'stock': 0
            })

    return jsonify(results)


# â”€â”€â”€ Single Medicine Check (POST /check_medicine) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@pharmacy_ops_bp.route('/api/check_medicine', methods=['POST'])
@pharmacy_access_required
@login_required
def check_single_medicine():
    """Check a single medicine in pharmacy inventory.
    
    Input JSON:  { "medicine": "Paracetamol" }
    Output JSON: { "name": "Paracetamol", "status": "available", "stock": 120 }
    """
    data = request.get_json()
    medicine_name = (data.get('medicine', '') or '').strip()

    if not medicine_name:
        return jsonify({'success': False, 'error': 'Medicine name required'}), 400

    # Normalize with RapidFuzz
    try:
        from app.services.voice_service import correct_medicine_name
        correction = correct_medicine_name(medicine_name)
        lookup_name = correction['name']
    except Exception:
        lookup_name = medicine_name

    med = Medicine.query.filter(
        db.func.lower(Medicine.name) == lookup_name.lower()
    ).first()

    if med and med.stock > 0:
        return jsonify({
            'name': med.name,
            'status': 'available',
            'stock': med.stock,
        })
    elif med and med.stock == 0:
        return jsonify({
            'name': med.name,
            'status': 'out_of_stock',
            'stock': 0,
        })
    else:
        return jsonify({
            'name': lookup_name,
            'status': 'not_available',
            'stock': 0,
        })

