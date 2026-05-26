"""
IP Admission, OP/IP Billing, and Discharge Summary Module.
Accessible by: RECEPTIONIST, DOCTOR, HOST, ADMIN
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.models import (
    db, Patient, Doctor, Visit, Billing, BillItem, IPAdmission,
    DischargeSummary, ConsultationFee, HospitalCharge, Bed, UserRole,
    Prescription, PrescriptionMedicine, ReceptionQueue
)
from datetime import datetime, date as date_cls
from functools import wraps
from sqlalchemy import text, inspect

ip_billing_bp = Blueprint('ip_billing', __name__, url_prefix='/ip-billing')


# ── Access control ───────────────────────────────────────────────────────────

def _staff_required(f):
    """Allow RECEPTIONIST, DOCTOR, HOST, ADMIN."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.choose_login'))
        allowed = {'RECEPTIONIST', 'DOCTOR', 'HOST', 'ADMIN'}
        if current_user.role.value not in allowed:
            flash('Access denied.', 'danger')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generate_bill_number():
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


def _generate_ip_number():
    """Generate sequential IP number: IP-YYYY-XXXX"""
    year = datetime.utcnow().strftime('%Y')
    last = IPAdmission.query.filter(IPAdmission.ip_number.like(f'IP-{year}-%'))\
        .order_by(IPAdmission.id.desc()).first()
    if last and last.ip_number:
        try:
            seq = int(last.ip_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f'IP-{year}-{seq:04d}'


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

@ip_billing_bp.route('/')
@ip_billing_bp.route('/dashboard')
@login_required
@_staff_required
def dashboard():
    """Billing & IP dashboard — shows active admissions, recent bills."""
    active_admissions = IPAdmission.query.filter_by(admission_status='Admitted')\
        .order_by(IPAdmission.admission_date.desc()).all()
    recent_bills = Billing.query.order_by(Billing.created_at.desc()).limit(20).all()
    pending_bills = Billing.query.filter(Billing.status.in_(['Unpaid', 'Draft']))\
        .order_by(Billing.created_at.desc()).all()

    return render_template('ip_billing/dashboard.html',
                           active_admissions=active_admissions,
                           recent_bills=recent_bills,
                           pending_bills=pending_bills)


# ═════════════════════════════════════════════════════════════════════════════
# IP ADMISSION
# ═════════════════════════════════════════════════════════════════════════════

@ip_billing_bp.route('/admit', methods=['GET', 'POST'])
@login_required
@_staff_required
def admit_patient():
    """Admit a patient as IP."""
    if request.method == 'GET':
        doctors = Doctor.query.filter_by(is_deleted=False, verified=True).all()
        beds = Bed.query.filter_by(is_occupied=False).all()
        # Pre-load all patients for client-side search (avoids AJAX/CSRF issues)
        all_patients = Patient.query.order_by(Patient.name).all()
        patients_json = []
        for p in all_patients:
            try:
                patients_json.append({
                    'id': p.id,
                    'uhid': p.uhid or '',
                    'name': p.full_name or p.name or '',
                    'age': p.age,
                    'gender': p.gender or '',
                    'phone': p.phone or '',
                    'aadhaar': getattr(p, 'aadhaar', '') or '',
                    'address': p.address or '',
                    'blood_type': p.blood_type or '',
                })
            except Exception:
                pass
        return render_template('ip_billing/admit.html', doctors=doctors, beds=beds,
                               patients_json=patients_json)

    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    # Check if already admitted
    active = IPAdmission.query.filter_by(patient_id=patient.id, admission_status='Admitted').first()
    if active:
        return jsonify({'success': False, 'error': f'Patient already admitted (IP: {active.ip_number})'}), 400

    try:
        # Create visit record
        visit = Visit(
            patient_id=patient.id,
            doctor_id=doctor_id,
            visit_type='IP',
            visit_reason=data.get('admission_reason', 'IP Admission'),
            visit_status='Active',
        )
        db.session.add(visit)
        db.session.flush()

        # Assign bed if selected
        bed_id = data.get('bed_id')
        if bed_id:
            bed = Bed.query.get(bed_id)
            if bed and not bed.is_occupied:
                bed.is_occupied = True
                bed.patient_id = patient.id

        admission = IPAdmission(
            patient_id=patient.id,
            doctor_id=doctor_id,
            visit_id=visit.id,
            ip_number=_generate_ip_number(),
            admission_reason=(data.get('admission_reason') or '').strip() or None,
            ward_type=data.get('ward_type') or None,
            bed_id=bed_id or None,
            room_number=data.get('room_number') or None,
            provisional_diagnosis=data.get('provisional_diagnosis') or None,
            notes=data.get('notes') or None,
        )
        db.session.add(admission)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Patient admitted successfully. IP Number: {admission.ip_number}',
            'ip_number': admission.ip_number,
            'admission_id': admission.id,
        })

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("IP admission failed")
        return jsonify({'success': False, 'error': str(exc)}), 500


@ip_billing_bp.route('/admission/<int:admission_id>')
@login_required
@_staff_required
def view_admission(admission_id):
    """View IP admission details."""
    admission = IPAdmission.query.get_or_404(admission_id)
    bills = Billing.query.filter_by(admission_id=admission.id).order_by(Billing.created_at.desc()).all()
    return render_template('ip_billing/view_admission.html', admission=admission, bills=bills)


@ip_billing_bp.route('/api/admissions/active')
@login_required
@_staff_required
def api_active_admissions():
    """Get all active IP admissions."""
    admissions = IPAdmission.query.filter_by(admission_status='Admitted')\
        .order_by(IPAdmission.admission_date.desc()).all()
    return jsonify({
        'success': True,
        'admissions': [{
            'id': a.id, 'ip_number': a.ip_number,
            'patient_name': a.patient.full_name, 'uhid': a.patient.uhid,
            'doctor': f"Dr. {a.doctor.first_name} {a.doctor.last_name}",
            'ward': a.ward_type or 'N/A', 'days': a.length_of_stay,
            'admission_date': a.admission_date.strftime('%Y-%m-%d') if a.admission_date else 'N/A',
        } for a in admissions],
    })


# ═════════════════════════════════════════════════════════════════════════════
# BILLING (OP + IP)
# ═════════════════════════════════════════════════════════════════════════════

@ip_billing_bp.route('/bill/create/<string:billing_type>/<int:patient_id>', methods=['GET'])
@login_required
@_staff_required
def create_bill_page(billing_type, patient_id):
    """Render OP or IP bill creation page."""
    patient = Patient.query.get_or_404(patient_id)
    billing_type = billing_type.upper()
    if billing_type not in ('OP', 'IP'):
        billing_type = 'OP'

    doctors = Doctor.query.filter_by(is_deleted=False, verified=True).all()
    charges = HospitalCharge.query.filter(
        db.or_(HospitalCharge.is_active == True, HospitalCharge.is_active.is_(None))
    ).order_by(HospitalCharge.charge_category, HospitalCharge.charge_name).all()
    fees = ConsultationFee.query.filter(
        db.or_(ConsultationFee.is_active == True, ConsultationFee.is_active.is_(None))
    ).all()

    # Group charges by category for organized display
    charge_categories = {}
    for c in charges:
        cat = c.charge_category or 'Other'
        if cat not in charge_categories:
            charge_categories[cat] = []
        charge_categories[cat].append(c)

    # Define category display order and icons
    cat_meta = {
        'Admin': ('fas fa-clipboard', '#64748b'),
        'Room': ('fas fa-bed', '#2563eb'),
        'Professional': ('fas fa-user-md', '#7c3aed'),
        'Nursing': ('fas fa-user-nurse', '#ec4899'),
        'Lab': ('fas fa-flask', '#0891b2'),
        'Lab-Haematology': ('fas fa-tint', '#dc2626'),
        'Lab-Biochemistry': ('fas fa-vials', '#0891b2'),
        'Lab-Serology': ('fas fa-shield-virus', '#7c3aed'),
        'Lab-Microbiology': ('fas fa-bacterium', '#059669'),
        'Lab-Screening': ('fas fa-search-plus', '#d97706'),
        'Lab-Urine': ('fas fa-flask', '#06b6d4'),
        'Lab-Hormones': ('fas fa-dna', '#be185d'),
        'Lab-Special': ('fas fa-microscope', '#6366f1'),
        'Lab-Histopath': ('fas fa-cut', '#b91c1c'),
        'Radiology': ('fas fa-x-ray', '#6366f1'),
        'Ultrasound': ('fas fa-broadcast-tower', '#0d9488'),
        'CT-Scan': ('fas fa-radiation', '#7c3aed'),
        'MRI': ('fas fa-magnet', '#2563eb'),
        'Imaging': ('fas fa-camera-retro', '#64748b'),
        'Cardiac': ('fas fa-heartbeat', '#dc2626'),
        'Neuro': ('fas fa-brain', '#8b5cf6'),
        'Endoscopy': ('fas fa-search', '#0d9488'),
        'Pulmonology': ('fas fa-lungs', '#06b6d4'),
        'Procedure': ('fas fa-syringe', '#d97706'),
        'Dialysis': ('fas fa-tint', '#dc2626'),
        'Oncology': ('fas fa-ribbon', '#be185d'),
        'OT': ('fas fa-procedures', '#b91c1c'),
        'Oxygen': ('fas fa-wind', '#0284c7'),
        'Ventilator': ('fas fa-fan', '#1d4ed8'),
        'Physio': ('fas fa-walking', '#059669'),
        'Emergency': ('fas fa-ambulance', '#dc2626'),
        'Ambulance': ('fas fa-truck-medical', '#b45309'),
        'OB-GYN': ('fas fa-baby', '#ec4899'),
        'Ortho': ('fas fa-bone', '#d97706'),
        'Urology': ('fas fa-procedures', '#0891b2'),
        'Eye': ('fas fa-eye', '#2563eb'),
        'ENT': ('fas fa-head-side-cough', '#7c3aed'),
        'Dental': ('fas fa-tooth', '#06b6d4'),
        'Dermatology': ('fas fa-allergies', '#d97706'),
        'Surgery': ('fas fa-cut', '#b91c1c'),
        'Health-Package': ('fas fa-box-open', '#059669'),
        'Pharmacy': ('fas fa-pills', '#059669'),
        'Consumables': ('fas fa-box', '#64748b'),
        'Misc': ('fas fa-ellipsis-h', '#94a3b8'),
    }

    # For IP billing, get admission
    admission = None
    if billing_type == 'IP':
        admission = IPAdmission.query.filter_by(
            patient_id=patient.id, admission_status='Admitted'
        ).first()

    return render_template('ip_billing/create_bill.html',
                           patient=patient, billing_type=billing_type,
                           doctors=doctors, charges=charges, fees=fees,
                           charge_categories=charge_categories,
                           cat_meta=cat_meta,
                           admission=admission)


@ip_billing_bp.route('/api/bill/save', methods=['POST'])
@login_required
@_staff_required
def api_save_bill():
    """Save a bill with line items."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    billing_type = (data.get('billing_type') or 'OP').upper()

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    try:
        items_data = data.get('items') or []
        subtotal = sum(float(i.get('total_price', 0)) for i in items_data)
        discount = float(data.get('discount', 0))
        tax = float(data.get('tax', 0))
        grand_total = subtotal - discount + tax

        bill = Billing(
            patient_id=patient.id,
            doctor_id=data.get('doctor_id') or None,
            billing_type=billing_type,
            bill_number=_generate_bill_number(),
            admission_id=data.get('admission_id') or None,
            amount=grand_total,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            grand_total=grand_total,
            description=data.get('description') or f'{billing_type} Bill',
            status=data.get('status', 'Unpaid'),
            payment_method=data.get('payment_method') or None,
            notes=data.get('notes') or None,
        )

        if bill.status == 'Paid':
            bill.paid_at = datetime.utcnow()

        db.session.add(bill)
        db.session.flush()

        for item in items_data:
            bi = BillItem(
                bill_id=bill.id,
                item_name=item.get('item_name', ''),
                item_category=item.get('item_category', ''),
                quantity=int(item.get('quantity', 1)),
                unit_price=float(item.get('unit_price', 0)),
                total_price=float(item.get('total_price', 0)),
                remarks=item.get('remarks') or None,
            )
            db.session.add(bi)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Bill {bill.bill_number} saved successfully',
            'bill_id': bill.id,
            'bill_number': bill.bill_number,
        })

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Bill save failed")
        return jsonify({'success': False, 'error': str(exc)}), 500


@ip_billing_bp.route('/bill/<int:bill_id>')
@login_required
@_staff_required
def view_bill(bill_id):
    """View/print a bill."""
    bill = Billing.query.get_or_404(bill_id)
    items = BillItem.query.filter_by(bill_id=bill.id).all()
    return render_template('ip_billing/view_bill.html', bill=bill, items=items)


@ip_billing_bp.route('/bill/<int:bill_id>/edit')
@login_required
@_staff_required
def edit_bill(bill_id):
    """Edit an existing bill — loads all items back into the billing form."""
    bill = Billing.query.get_or_404(bill_id)
    patient = bill.patient
    billing_type = bill.billing_type or 'OP'

    existing_items = BillItem.query.filter_by(bill_id=bill.id).all()

    doctors = Doctor.query.filter_by(is_deleted=False, verified=True).all()
    charges = HospitalCharge.query.filter(
        db.or_(HospitalCharge.is_active == True, HospitalCharge.is_active.is_(None))
    ).order_by(HospitalCharge.charge_category, HospitalCharge.charge_name).all()
    fees = ConsultationFee.query.filter(
        db.or_(ConsultationFee.is_active == True, ConsultationFee.is_active.is_(None))
    ).all()

    charge_categories = {}
    for c in charges:
        cat = c.charge_category or 'Other'
        if cat not in charge_categories:
            charge_categories[cat] = []
        charge_categories[cat].append(c)

    cat_meta = {
        'Admin': ('fas fa-clipboard', '#64748b'), 'Room': ('fas fa-bed', '#2563eb'),
        'Professional': ('fas fa-user-md', '#7c3aed'), 'Nursing': ('fas fa-user-nurse', '#ec4899'),
        'Lab': ('fas fa-flask', '#0891b2'),
        'Lab-Haematology': ('fas fa-tint', '#dc2626'), 'Lab-Biochemistry': ('fas fa-vials', '#0891b2'),
        'Lab-Serology': ('fas fa-shield-virus', '#7c3aed'), 'Lab-Microbiology': ('fas fa-bacterium', '#059669'),
        'Lab-Screening': ('fas fa-search-plus', '#d97706'), 'Lab-Urine': ('fas fa-flask', '#06b6d4'),
        'Lab-Hormones': ('fas fa-dna', '#be185d'), 'Lab-Special': ('fas fa-microscope', '#6366f1'),
        'Lab-Histopath': ('fas fa-cut', '#b91c1c'),
        'Radiology': ('fas fa-x-ray', '#6366f1'), 'Ultrasound': ('fas fa-broadcast-tower', '#0d9488'),
        'CT-Scan': ('fas fa-radiation', '#7c3aed'), 'MRI': ('fas fa-magnet', '#2563eb'),
        'Imaging': ('fas fa-camera-retro', '#64748b'),
        'Cardiac': ('fas fa-heartbeat', '#dc2626'), 'Neuro': ('fas fa-brain', '#8b5cf6'),
        'Endoscopy': ('fas fa-search', '#0d9488'), 'Pulmonology': ('fas fa-lungs', '#06b6d4'),
        'Procedure': ('fas fa-syringe', '#d97706'), 'Dialysis': ('fas fa-tint', '#dc2626'),
        'Oncology': ('fas fa-ribbon', '#be185d'),
        'OT': ('fas fa-procedures', '#b91c1c'), 'Oxygen': ('fas fa-wind', '#0284c7'),
        'Ventilator': ('fas fa-fan', '#1d4ed8'), 'Physio': ('fas fa-walking', '#059669'),
        'Emergency': ('fas fa-ambulance', '#dc2626'), 'Ambulance': ('fas fa-truck-medical', '#b45309'),
        'OB-GYN': ('fas fa-baby', '#ec4899'), 'Ortho': ('fas fa-bone', '#d97706'),
        'Urology': ('fas fa-procedures', '#0891b2'), 'Eye': ('fas fa-eye', '#2563eb'),
        'ENT': ('fas fa-head-side-cough', '#7c3aed'), 'Dental': ('fas fa-tooth', '#06b6d4'),
        'Dermatology': ('fas fa-allergies', '#d97706'), 'Surgery': ('fas fa-cut', '#b91c1c'),
        'Health-Package': ('fas fa-box-open', '#059669'),
        'Pharmacy': ('fas fa-pills', '#059669'), 'Consumables': ('fas fa-box', '#64748b'),
        'Misc': ('fas fa-ellipsis-h', '#94a3b8'),
    }

    admission = None
    if billing_type == 'IP' and bill.admission_id:
        admission = IPAdmission.query.get(bill.admission_id)

    return render_template('ip_billing/create_bill.html',
                           patient=patient, billing_type=billing_type,
                           doctors=doctors, charges=charges, fees=fees,
                           charge_categories=charge_categories, cat_meta=cat_meta,
                           admission=admission,
                           edit_bill=bill, edit_items=existing_items)


@ip_billing_bp.route('/api/bill/<int:bill_id>/update', methods=['POST'])
@login_required
@_staff_required
def api_update_bill(bill_id):
    """Update an existing bill — replaces all items."""
    bill = Billing.query.get_or_404(bill_id)
    data = request.get_json(silent=True) or {}

    try:
        # Delete old items
        BillItem.query.filter_by(bill_id=bill.id).delete()

        items_data = data.get('items') or []
        subtotal = sum(float(i.get('total_price', 0)) for i in items_data)
        discount = float(data.get('discount', 0))
        tax = float(data.get('tax', 0))
        grand_total = subtotal - discount + tax

        bill.doctor_id = data.get('doctor_id') or bill.doctor_id
        bill.description = data.get('description') or bill.description
        bill.payment_method = data.get('payment_method') or bill.payment_method
        bill.subtotal = subtotal
        bill.discount = discount
        bill.tax = tax
        bill.grand_total = grand_total
        bill.amount = grand_total
        bill.notes = data.get('notes') or bill.notes
        bill.status = data.get('status') or bill.status

        if bill.status == 'Paid' and not bill.paid_at:
            bill.paid_at = datetime.utcnow()

        for item in items_data:
            bi = BillItem(
                bill_id=bill.id,
                item_name=item.get('item_name', ''),
                item_category=item.get('item_category', ''),
                quantity=int(item.get('quantity', 1)),
                unit_price=float(item.get('unit_price', 0)),
                total_price=float(item.get('total_price', 0)),
                remarks=item.get('remarks') or None,
            )
            db.session.add(bi)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Bill {bill.bill_number or bill.id} updated successfully',
            'bill_id': bill.id,
            'bill_number': bill.bill_number,
        })

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Bill update failed")
        return jsonify({'success': False, 'error': str(exc)}), 500


@ip_billing_bp.route('/api/bill/<int:bill_id>/pay', methods=['POST'])
@login_required
@_staff_required
def api_pay_bill(bill_id):
    """Mark a bill as paid."""
    bill = Billing.query.get_or_404(bill_id)
    data = request.get_json(silent=True) or {}
    try:
        bill.status = 'Paid'
        bill.payment_method = data.get('payment_method', 'Cash')
        bill.paid_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bill marked as paid'})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@ip_billing_bp.route('/api/charges')
@login_required
@_staff_required
def api_get_charges():
    """Get all hospital charges for billing dropdown."""
    charges = HospitalCharge.query.filter(
        db.or_(HospitalCharge.is_active == True, HospitalCharge.is_active.is_(None))
    ).order_by(HospitalCharge.charge_category).all()
    return jsonify({
        'success': True,
        'charges': [{
            'id': c.id, 'name': c.charge_name,
            'category': c.charge_category, 'price': c.default_price,
        } for c in charges],
    })


@ip_billing_bp.route('/api/consultation-fees')
@login_required
@_staff_required
def api_get_consultation_fees():
    """Get consultation fees."""
    fees = ConsultationFee.query.filter(
        db.or_(ConsultationFee.is_active == True, ConsultationFee.is_active.is_(None))
    ).all()
    return jsonify({
        'success': True,
        'fees': [{
            'id': f.id, 'type': f.consultation_type,
            'amount': f.fee_amount, 'doctor_id': f.doctor_id,
        } for f in fees],
    })


# ═════════════════════════════════════════════════════════════════════════════
# DISCHARGE
# ═════════════════════════════════════════════════════════════════════════════

@ip_billing_bp.route('/discharge/<int:admission_id>', methods=['GET'])
@login_required
@_staff_required
def discharge_page(admission_id):
    """Render discharge summary form."""
    admission = IPAdmission.query.get_or_404(admission_id)
    existing = DischargeSummary.query.filter_by(admission_id=admission.id).first()
    return render_template('ip_billing/discharge.html', admission=admission, summary=existing)


@ip_billing_bp.route('/api/discharge/save', methods=['POST'])
@login_required
@_staff_required
def api_save_discharge():
    """Save discharge summary and mark admission as discharged."""
    data = request.get_json(silent=True) or {}
    admission_id = data.get('admission_id')
    admission = IPAdmission.query.get(admission_id)
    if not admission:
        return jsonify({'success': False, 'error': 'Admission not found'}), 404

    try:
        # Create or update discharge summary
        summary = DischargeSummary.query.filter_by(admission_id=admission.id).first()
        if not summary:
            summary = DischargeSummary(
                admission_id=admission.id,
                patient_id=admission.patient_id,
                doctor_id=admission.doctor_id,
            )
            db.session.add(summary)

        for field in ['presenting_complaints', 'history_of_illness', 'past_history',
                      'examination_findings', 'diagnosis', 'investigations',
                      'course_in_hospital', 'treatment_given', 'procedures_done',
                      'condition_at_discharge', 'medicines_at_discharge',
                      'discharge_advice', 'diet_advice', 'follow_up_instructions']:
            val = (data.get(field) or '').strip() or None
            setattr(summary, field, val)

        fup_raw = (data.get('follow_up_date') or '').strip()
        if fup_raw:
            try:
                summary.follow_up_date = datetime.strptime(fup_raw, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Mark admission as discharged
        if data.get('mark_discharged', False):
            admission.admission_status = 'Discharged'
            admission.discharge_date = datetime.utcnow()

            # Free bed
            if admission.bed_id:
                bed = Bed.query.get(admission.bed_id)
                if bed:
                    bed.is_occupied = False
                    bed.patient_id = None

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Discharge summary saved',
            'summary_id': summary.id,
        })

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Discharge save failed")
        return jsonify({'success': False, 'error': str(exc)}), 500


@ip_billing_bp.route('/discharge/<int:admission_id>/print')
@login_required
@_staff_required
def discharge_print(admission_id):
    """Printable discharge summary."""
    admission = IPAdmission.query.get_or_404(admission_id)
    summary = DischargeSummary.query.filter_by(admission_id=admission.id).first_or_404()
    return render_template('ip_billing/discharge_print.html', admission=admission, summary=summary)


# ═════════════════════════════════════════════════════════════════════════════
# PATIENT SEARCH (for reception/billing use)
# ═════════════════════════════════════════════════════════════════════════════

@ip_billing_bp.route('/api/patient/search')
@login_required
@_staff_required
def api_search_patient():
    """Search patients by UHID, name, phone, aadhaar. Works with partial matches."""
    q = (request.args.get('q') or '').strip()
    if not q or len(q) < 1:
        return jsonify({'success': True, 'patients': []})

    try:
        like_q = f'%{q}%'
        # Use coalesce to handle NULL columns safely
        filters = [
            db.func.coalesce(Patient.uhid, '').ilike(like_q),
            db.func.coalesce(Patient.name, '').ilike(like_q),
            db.func.coalesce(Patient.first_name, '').ilike(like_q),
            db.func.coalesce(Patient.last_name, '').ilike(like_q),
            db.func.coalesce(Patient.phone, '').ilike(like_q),
        ]
        try:
            filters.append(db.func.coalesce(Patient.aadhaar, '').ilike(like_q))
        except Exception:
            pass

        patients = Patient.query.filter(db.or_(*filters)).limit(20).all()

        results = []
        for p in patients:
            try:
                results.append({
                    'id': p.id, 'uhid': p.uhid or '', 'name': p.full_name or p.name or '',
                    'age': p.age, 'gender': p.gender or '', 'phone': p.phone or '',
                    'aadhaar': getattr(p, 'aadhaar', '') or '',
                    'address': p.address or '',
                    'blood_type': p.blood_type or '',
                })
            except Exception as row_err:
                current_app.logger.warning("Skipping patient %s: %s", p.id, row_err)

        return jsonify({'success': True, 'patients': results})
    except Exception as exc:
        current_app.logger.exception("Patient search failed for q=%s", q)
        return jsonify({'success': False, 'patients': [], 'error': str(exc)})


@ip_billing_bp.route('/api/patient/register', methods=['POST'])
@login_required
@_staff_required
def api_register_patient():
    """Register a new patient directly (for IP admission, elderly patients without accounts)."""
    data = request.get_json(silent=True) or {}

    first_name = (data.get('first_name') or '').strip()
    if not first_name:
        return jsonify({'success': False, 'error': 'First name is required'}), 400

    last_name = (data.get('last_name') or '').strip()
    gender = data.get('gender') or 'Male'

    try:
        from app.services.patient_service import PatientService
        uhid = PatientService.generate_uhid()
    except Exception:
        # Fallback UHID generation
        import random
        year = datetime.utcnow().strftime('%Y')
        uhid = f'PAT-{year}-{random.randint(1000,9999)}'

    full_name = f"{first_name} {last_name}".strip()

    try:
        patient = Patient(
            uhid=uhid,
            name=full_name,
            first_name=first_name,
            last_name=last_name or '',
            age=int(data['age']) if data.get('age') else None,
            gender=gender,
            phone=(data.get('phone') or '').strip() or None,
            address=(data.get('address') or '').strip() or None,
            blood_type=(data.get('blood_type') or '').strip() or None,
            emergency_contact=(data.get('emergency_contact') or '').strip() or None,
            is_walk_in=True,
        )

        # Set aadhaar if available
        aadhaar = (data.get('aadhaar') or '').strip()
        if aadhaar and hasattr(patient, 'aadhaar'):
            patient.aadhaar = aadhaar

        db.session.add(patient)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Patient registered. UHID: {uhid}',
            'patient': {
                'id': patient.id, 'uhid': patient.uhid, 'name': patient.full_name,
                'age': patient.age, 'gender': patient.gender, 'phone': patient.phone or '',
            },
        })
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Patient registration failed")
        return jsonify({'success': False, 'error': str(exc)}), 500
