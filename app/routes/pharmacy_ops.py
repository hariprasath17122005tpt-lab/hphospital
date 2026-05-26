"""
Pharmacy Operations Module â€" Prescription-based dispensing workflow
Accessible by: PHARMACIST (full), DOCTOR (view status, create orders), ADMIN/HOST
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, PharmacyOrder, PharmacySale, Prescription, Patient, Doctor, UserRole, Medicine, Visit, Consultation,
                               MedicationDispensing, IPAdmission, IPMedication, Billing, BillItem)
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


# â"€â"€â"€ Dashboard â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
@pharmacy_ops_bp.route('/')
@pharmacy_ops_bp.route('/dashboard')
@pharmacy_access_required
@login_required
def dashboard():
    """Pharmacy dashboard -- view prescriptions awaiting dispensing (grouped by prescription)"""
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

    # ── Group orders by prescription_id ──
    from collections import OrderedDict
    grouped_orders = OrderedDict()  # {prescription_id: {patient, doctor, orders[], status, date}}
    orphan_orders = []  # orders without prescription_id

    for order in orders:
        if order.prescription_id:
            key = order.prescription_id
            if key not in grouped_orders:
                grouped_orders[key] = {
                    'prescription_id': key,
                    'patient': order.patient,
                    'doctor': order.doctor,
                    'orders': [],
                    'created_at': order.created_at,
                }
            grouped_orders[key]['orders'].append(order)
        else:
            orphan_orders.append(order)

    # Compute group-level status: all dispensed → Dispensed, any pending → Pending
    for grp in grouped_orders.values():
        all_dispensed = all(o.status == 'Dispensed' for o in grp['orders'])
        grp['status'] = 'Dispensed' if all_dispensed else 'Pending'
        grp['pending_count'] = sum(1 for o in grp['orders'] if o.status == 'Pending')
        grp['total_count'] = len(grp['orders'])

    # Get recent prescriptions that don't have pharmacy orders yet (for pharmacist)
    unprocessed_prescriptions = []
    if current_user.role in (UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN):
        existing_rx_ids = db.session.query(PharmacyOrder.prescription_id).filter(
            PharmacyOrder.prescription_id.isnot(None)
        ).distinct().all()
        existing_rx_ids = [x[0] for x in existing_rx_ids]

        unprocessed_prescriptions = Prescription.query.filter(
            ~Prescription.id.in_(existing_rx_ids) if existing_rx_ids else True
        ).order_by(Prescription.prescribed_at.desc()).limit(20).all()

    return render_template('pharmacy_ops/dashboard.html',
                           orders=orders,
                           grouped_orders=list(grouped_orders.values()),
                           orphan_orders=orphan_orders,
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
    """View full hospital-grade prescription sheet — uses professional template."""
    prescription = Prescription.query.get_or_404(id)

    # Use the professional Paras-style template if consultation exists
    consultation_id = getattr(prescription, 'consultation_id', None)
    if consultation_id:
        consultation = Consultation.query.get(consultation_id)
        if consultation:
            patient = consultation.patient
            doc = consultation.doctor
            medicines = []
            try:
                for m in prescription.medicine_items:
                    medicines.append({
                        'name': m.medicine_name, 'dosage': m.dosage or '', 'route': m.route or '',
                        'frequency': m.frequency or '', 'duration': m.duration or '',
                        'food_relation': m.food_relation or '', 'instruction': m.instruction or '',
                        'special_instruction': m.special_instruction or '',
                    })
            except Exception:
                pass

            allergy_warning = None
            if patient.allergy_history or patient.allergies:
                allergy_warning = patient.allergy_history or patient.allergies

            return render_template('doctor/consultation_prescription.html',
                                   consultation=consultation, patient=patient,
                                   doctor_record=doc, medicines=medicines,
                                   prescription=prescription, allergy_warning=allergy_warning)

    # Fallback for old prescriptions
    return render_template('patient/view_prescription.html', prescription=prescription)

# â"€â"€â"€ Dispense Medication â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# --- Fetch prescription details for the dispense modal ---
@pharmacy_ops_bp.route('/api/prescription-details/<int:prescription_id>')
@pharmacy_access_required
@login_required
def prescription_details(prescription_id):
    """Return pending order details so the pharmacist modal can pre-fill them."""
    orders = PharmacyOrder.query.filter_by(
        prescription_id=prescription_id, status='Pending'
    ).all()
    if not orders:
        return jsonify({'success': False, 'error': 'No pending orders'}), 404

    patient = Patient.query.get(orders[0].patient_id)
    doctor = Doctor.query.get(orders[0].doctor_id) if orders[0].doctor_id else None

    items = []
    for o in orders:
        # Try to get default price from inventory
        med = Medicine.query.filter(
            db.func.lower(Medicine.name) == db.func.lower(o.medicine_name.strip())
        ).first()
        items.append({
            'order_id': o.id,
            'medicine_name': o.medicine_name,
            'dosage': o.dosage or '',
            'quantity': int(o.quantity) if o.quantity else 1,
            'unit_price': float(med.price or 0) if med else 0.0,
            'stock': int(med.stock) if med else 0,
        })

    # Auto-fetch lab and consultation charges for today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from app.models.models import LabOrder as _LabOrder, HospitalCharge, ConsultationFee
    extra_items = []

    lab_orders_today = _LabOrder.query.filter(
        _LabOrder.patient_id == patient.id,
        _LabOrder.created_at >= today_start,
    ).all()
    for lo in lab_orders_today:
        charge = HospitalCharge.query.filter(
            HospitalCharge.charge_name.ilike(f'%{lo.test_name}%'),
            db.or_(HospitalCharge.is_active == True, HospitalCharge.is_active.is_(None)),
        ).first()
        lab_price = float(charge.default_price) if charge else 0.0
        extra_items.append({
            'item_name': f'Lab: {lo.test_name}',
            'category': 'Laboratory',
            'quantity': 1,
            'unit_price': lab_price,
        })

    if orders[0].doctor_id:
        fee = ConsultationFee.query.filter_by(
            doctor_id=orders[0].doctor_id, consultation_type='New'
        ).filter(
            db.or_(ConsultationFee.is_active == True, ConsultationFee.is_active.is_(None))
        ).first()
        if not fee:
            fee = ConsultationFee.query.filter_by(
                doctor_id=None, consultation_type='New'
            ).filter(
                db.or_(ConsultationFee.is_active == True, ConsultationFee.is_active.is_(None))
            ).first()
        if fee and fee.fee_amount > 0:
            extra_items.append({
                'item_name': 'Consultation Fee',
                'category': 'Consultation',
                'quantity': 1,
                'unit_price': float(fee.fee_amount),
            })

    return jsonify({
        'success': True,
        'patient_name': patient.name if patient else '',
        'uhid': patient.uhid if patient else '',
        'doctor_name': f'Dr. {doctor.first_name} {doctor.last_name}' if doctor else '',
        'medicines': items,
        'extra_charges': extra_items,
    })


# --- Dispense ALL with pharmacist-entered prices + create OP bill ---
@pharmacy_ops_bp.route('/api/dispense-prescription', methods=['POST'])
@pharmacist_only
@login_required
def dispense_prescription():
    """Dispense orders using pharmacist-entered qty/price and create OP bill."""
    data = request.get_json()
    prescription_id = data.get('prescription_id')
    medicines_input = data.get('medicines', [])     # [{order_id, quantity, unit_price}]
    extra_charges = data.get('extra_charges', [])    # [{item_name, category, quantity, unit_price}]
    discount = float(data.get('discount', 0) or 0)

    if not prescription_id or not medicines_input:
        return jsonify({'success': False, 'error': 'prescription_id and medicines required'}), 400

    dispensed_at = datetime.utcnow()
    bill_items_data = []
    dispensed_names = []
    patient_id = None
    doctor_id = None

    for med_in in medicines_input:
        order = PharmacyOrder.query.get(med_in.get('order_id'))
        if not order or order.prescription_id != int(prescription_id):
            continue
        if order.status == 'Dispensed':
            continue

        patient_id = order.patient_id
        doctor_id = order.doctor_id

        qty = int(med_in.get('quantity', 1) or 1)
        unit_price = float(med_in.get('unit_price', 0) or 0)

        # Check + deduct inventory
        medicine = Medicine.query.filter(
            db.func.lower(Medicine.name) == db.func.lower(order.medicine_name.strip())
        ).first()
        if medicine:
            if medicine.stock < qty:
                return jsonify({
                    'success': False,
                    'error': f'Insufficient stock for {medicine.name}. Only {medicine.stock} available.'
                }), 400
            medicine.stock -= qty

        order.status = 'Dispensed'
        order.dispensed_at = dispensed_at
        order.quantity = qty

        if not order.sale_records.first():
            sale = PharmacySale(
                patient_id=order.patient_id,
                pharmacy_order_id=order.id,
                medicine_name=order.medicine_name,
                quantity=qty,
                price=unit_price,
                sold_at=dispensed_at,
                notes=order.notes,
            )
            db.session.add(sale)

        line_total = round(qty * unit_price, 2)
        bill_items_data.append({
            'item_name': order.medicine_name,
            'item_category': 'Pharmacy',
            'quantity': qty,
            'unit_price': unit_price,
            'total_price': line_total,
        })
        dispensed_names.append(order.medicine_name)

    if not patient_id:
        return jsonify({'success': False, 'error': 'No valid orders to dispense'}), 400

    # Add extra charges (lab, consultation) from pharmacist input
    for ec in extra_charges:
        ec_qty = int(ec.get('quantity', 1) or 1)
        ec_price = float(ec.get('unit_price', 0) or 0)
        if ec_price > 0:
            bill_items_data.append({
                'item_name': ec.get('item_name', ''),
                'item_category': ec.get('category', 'Other'),
                'quantity': ec_qty,
                'unit_price': ec_price,
                'total_price': round(ec_qty * ec_price, 2),
            })

    subtotal = sum(item['total_price'] for item in bill_items_data)
    grand_total = max(subtotal - discount, 0)

    bill = None
    if grand_total > 0 or subtotal > 0:
        bill = Billing(
            patient_id=patient_id,
            doctor_id=doctor_id,
            billing_type='OP',
            bill_number=_generate_pharm_bill_number(),
            amount=grand_total,
            subtotal=subtotal,
            discount=discount,
            tax=0,
            grand_total=grand_total,
            description=f'OP Bill - Rx #{prescription_id}',
            status='Unpaid',
        )
        db.session.add(bill)
        db.session.flush()

        for bi_data in bill_items_data:
            db.session.add(BillItem(
                bill_id=bill.id,
                item_name=bi_data['item_name'],
                item_category=bi_data['item_category'],
                quantity=bi_data['quantity'],
                unit_price=bi_data['unit_price'],
                total_price=bi_data['total_price'],
            ))

    _record_pharmacy_visit(
        patient_id=patient_id,
        doctor_id=doctor_id,
        notes=f"Prescription #{prescription_id} dispensed: {', '.join(dispensed_names)}",
        visit_date=dispensed_at,
    )

    try:
        db.session.commit()
        msg = f'{len(dispensed_names)} medicine(s) dispensed'
        if bill:
            msg += f' | Bill {bill.bill_number} created (Rs.{grand_total:.2f})'
        return jsonify({
            'success': True,
            'message': msg,
            'bill_number': bill.bill_number if bill else None,
            'grand_total': grand_total,
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Batch dispense error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# â"€â"€â"€ Create order from prescription â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
@pharmacy_ops_bp.route('/api/create-from-prescription', methods=['POST'])
@pharmacy_access_required
@login_required
def create_from_prescription():
    """Create pharmacy orders from a prescription â€" uses PrescriptionMedicine model"""
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


# â"€â"€â"€ Doctor create direct order â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# â"€â"€â"€ Patient Medicine History â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# â"€â"€â"€ Search patients (AJAX) â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# â"€â"€â"€ Medicine Availability Check API â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# â"€â"€â"€ Single Medicine Check (POST /check_medicine) â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


# ═══════════════════════════════════════════════════════════════════
#  IP MEDICATION DISPENSING WORKFLOW
# ═══════════════════════════════════════════════════════════════════

@pharmacy_ops_bp.route('/ip-medication-requests')
@login_required
@pharmacist_only
def ip_medication_requests():
    """Patient-centric view of IP medication dispensing requests."""
    # Group pending dispensing records by admission
    active_admissions = IPAdmission.query.filter_by(admission_status='Admitted').all()
    logger.info(f'[IP-MED-REQ] Found {len(active_admissions)} active admissions')

    patients_data = []
    for adm in active_admissions:
        pending = MedicationDispensing.query.filter_by(
            admission_id=adm.id, dispensing_status='Pending'
        ).count()
        dispensed = MedicationDispensing.query.filter_by(
            admission_id=adm.id, dispensing_status='Dispensed'
        ).count()
        total = MedicationDispensing.query.filter_by(admission_id=adm.id).count()
        if total == 0:
            continue
        patient = Patient.query.get(adm.patient_id)
        doctor = Doctor.query.get(adm.doctor_id)
        patients_data.append({
            'admission': adm,
            'patient': patient,
            'doctor': doctor,
            'pending': pending,
            'dispensed': dispensed,
            'total': total,
        })

    # Sort: patients with pending items first
    patients_data.sort(key=lambda x: (-x['pending'], x['patient'].first_name if x['patient'] else ''))

    logger.info(f'[IP-MED-REQ] Returning {len(patients_data)} patients to template')

    return render_template(
        'pharmacy/ip_medication_requests.html',
        patients_data=patients_data,
    )


@pharmacy_ops_bp.route('/ip-medication-requests/<int:admission_id>')
@login_required
@pharmacist_only
def ip_medication_patient_detail(admission_id):
    """Show all medication requests for a specific IP patient."""
    adm = IPAdmission.query.get_or_404(admission_id)
    patient = Patient.query.get(adm.patient_id)
    doctor = Doctor.query.get(adm.doctor_id)

    records = MedicationDispensing.query.filter_by(admission_id=adm.id).order_by(
        db.case(
            (MedicationDispensing.dispensing_status == 'Pending', 0),
            (MedicationDispensing.dispensing_status == 'Partially Dispensed', 1),
            else_=2
        ),
        MedicationDispensing.created_at.desc()
    ).all()

    items = []
    for rec in records:
        ip_med = IPMedication.query.get(rec.ip_medication_id)
        med_master = Medicine.query.filter(Medicine.name.ilike(rec.medicine_name)).first()
        items.append({
            'record': rec,
            'ip_med': ip_med,
            'stock': med_master.stock if med_master else 0,
            'price': med_master.price if med_master and med_master.price else 0,
        })

    return render_template(
        'pharmacy/ip_medication_patient.html',
        admission=adm,
        patient=patient,
        doctor=doctor,
        items=items,
    )


def _generate_pharm_bill_number():
    """Generate sequential bill number: BILL-YYYY-XXXX"""
    year = datetime.utcnow().strftime('%Y')
    last = Billing.query.filter(Billing.bill_number.like(f'BILL-{year}-%'))\
        .order_by(Billing.id.desc()).first()
    if last and last.bill_number:
        try:
            seq = int(last.bill_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f'BILL-{year}-{seq:04d}'


@pharmacy_ops_bp.route('/ip-medication/dispense/<int:admission_id>', methods=['POST'])
@login_required
@pharmacist_only
def ip_medication_dispense(admission_id):
    """Pharmacist dispenses medicines for an IP patient and creates a bill."""
    adm = IPAdmission.query.get_or_404(admission_id)
    data = request.get_json(silent=True) or {}
    medicines = data.get('medicines', [])

    if not medicines:
        return jsonify({'success': False, 'error': 'No medicines provided'}), 400

    bill_items = []
    total_amount = 0

    for med_data in medicines:
        disp_id = med_data.get('dispensing_id')
        if not disp_id:
            continue
        rec = MedicationDispensing.query.get(disp_id)
        if not rec or rec.admission_id != adm.id:
            continue

        qty = int(med_data.get('quantity', 0) or 0)
        price = float(med_data.get('unit_price', 0) or 0)
        line_total = qty * price

        # Update dispensing record
        rec.dispensed_quantity = str(qty)
        rec.unit_price = price
        rec.total_price = line_total
        rec.dispensing_status = 'Dispensed' if qty > 0 else 'Not Available'
        rec.stock_status = 'Available' if qty > 0 else 'Out of Stock'
        rec.pharmacist_id = current_user.id
        rec.dispensed_at = datetime.utcnow() if qty > 0 else None
        rec.remarks = med_data.get('remarks', '')

        # Deduct stock
        if qty > 0:
            med_master = Medicine.query.filter(Medicine.name.ilike(rec.medicine_name)).first()
            if med_master and med_master.stock >= qty:
                med_master.stock -= qty

            bill_items.append({
                'item_name': rec.medicine_name,
                'item_category': 'Medicine',
                'quantity': qty,
                'unit_price': price,
                'total_price': line_total,
                'remarks': rec.remarks or '',
            })
            total_amount += line_total

    # Create a pharmacy bill linked to this admission
    bill = None
    if bill_items and total_amount > 0:
        bill = Billing(
            patient_id=adm.patient_id,
            doctor_id=adm.doctor_id,
            billing_type='IP',
            bill_number=_generate_pharm_bill_number(),
            admission_id=adm.id,
            amount=total_amount,
            subtotal=total_amount,
            discount=0,
            tax=0,
            grand_total=total_amount,
            description=f'IP Pharmacy — {adm.ip_number}',
            status='Unpaid',
        )
        db.session.add(bill)
        db.session.flush()

        for bi_data in bill_items:
            bi = BillItem(
                bill_id=bill.id,
                item_name=bi_data['item_name'],
                item_category='Medicine',
                quantity=bi_data['quantity'],
                unit_price=bi_data['unit_price'],
                total_price=bi_data['total_price'],
                remarks=bi_data.get('remarks', ''),
            )
            db.session.add(bi)

    db.session.commit()

    msg = f'Dispensed {len(bill_items)} medicine(s)'
    if bill:
        msg += f' — Bill {bill.bill_number} (₹{total_amount:.2f}) created for reception'

    return jsonify({'success': True, 'message': msg})

