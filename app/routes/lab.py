"""
Laboratory Module — unified workflow (doctor-referred + walk-in).
Canonical model: LabOrder (table lab_orders).
Legacy: LabReport retained for historical rows and doctor-entered panels.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, Response, session
from flask_login import login_required, current_user
from app.models.models import (
    db, LabReport, LabOrder, Patient, Doctor, UserRole, Prescription, Billing, LabTestTemplate
)
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import json
import logging

logger = logging.getLogger(__name__)

lab_bp = Blueprint('lab', __name__, url_prefix='/lab')

# Bumped when lab HTML/API changes — visible in X-CarePoint-Lab-UI response header
LAB_UI_BUILD_ID = 'laborder-v2.1'


@lab_bp.after_request
def _lab_cache_headers(response):
    """Prevent stale lab HTML in browsers; expose build id for debugging (DevTools → Network)."""
    response.headers['X-CarePoint-Lab-UI'] = LAB_UI_BUILD_ID
    if request.endpoint == 'lab.dashboard':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response


LAB_ORDER_STATUSES = ('CREATED', 'SAMPLE_COLLECTED', 'PROCESSING', 'COMPLETED')
SOURCE_DOCTOR = 'DOCTOR'
SOURCE_WALK_IN = 'WALK_IN'

# Default fee when not in catalog (institution configures real fee schedule separately)
DEFAULT_LAB_PRICE = 499.0

# test_name -> { 'category': str, 'price': float }
LAB_TEST_CATALOG = {
    'Complete Blood Count (CBC)': {'category': 'Hematology', 'price': 350},
    'Blood Sugar (Fasting)': {'category': 'Biochemistry', 'price': 180},
    'Blood Sugar (Random)': {'category': 'Biochemistry', 'price': 150},
    'HbA1c': {'category': 'Biochemistry', 'price': 450},
    'Lipid Profile': {'category': 'Biochemistry', 'price': 550},
    'Liver Function Test (LFT)': {'category': 'Biochemistry', 'price': 720},
    'Kidney Function Test (KFT)': {'category': 'Biochemistry', 'price': 650},
    'Thyroid Profile (T3, T4, TSH)': {'category': 'Endocrinology', 'price': 900},
    'Urine Analysis': {'category': 'Clinical Pathology', 'price': 200},
    'ECG': {'category': 'Cardiology', 'price': 300},
    'Chest X-Ray': {'category': 'Radiology', 'price': 400},
    'MRI Scan': {'category': 'Radiology', 'price': 8500},
    'CT Scan': {'category': 'Radiology', 'price': 4500},
    'Vitamin D': {'category': 'Biochemistry', 'price': 1200},
    'Vitamin B12': {'category': 'Biochemistry', 'price': 900},
    'Iron Studies': {'category': 'Hematology', 'price': 800},
    'COVID-19 RT-PCR': {'category': 'Microbiology', 'price': 600},
}


def _catalog_entry(test_name):
    if not test_name:
        return {'category': 'General', 'price': DEFAULT_LAB_PRICE}
    return LAB_TEST_CATALOG.get(
        test_name.strip(),
        {'category': 'General', 'price': DEFAULT_LAB_PRICE},
    )


def _validate_lab_order_source(source_type, doctor_id):
    if source_type == SOURCE_DOCTOR:
        return doctor_id is not None
    if source_type == SOURCE_WALK_IN:
        return doctor_id is None
    return False


def lab_access_required(f):
    """Allow LAB_STAFF, DOCTOR, HOST, ADMIN"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access the laboratory module.', 'danger')
            return redirect(url_for('auth.choose_login'))
        allowed = [UserRole.LAB_STAFF, UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN]
        if current_user.role not in allowed:
            flash('Access denied. Lab staff or Doctor login required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def lab_staff_only(f):
    """Only LAB_STAFF and HOST/ADMIN"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.choose_login'))
        allowed = [UserRole.LAB_STAFF, UserRole.HOST, UserRole.ADMIN]
        if current_user.role not in allowed:
            flash('Access denied. Lab staff login required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def _lab_orders_base_query():
    q = LabOrder.query
    if current_user.role == UserRole.DOCTOR and hasattr(current_user, 'doctor') and current_user.doctor:
        q = q.filter(LabOrder.doctor_id == current_user.doctor.id)
    return q


def _order_to_dict(o):
    patient = o.patient
    generated = []
    if getattr(o, 'generated_reports', None):
        generated = sorted(
            [{'id': r.id} for r in o.generated_reports if getattr(r, 'id', None)],
            key=lambda x: x['id'],
            reverse=True
        )
    return {
        'id': o.id,
        'patient_id': o.patient_id,
        'patient_uhid': patient.uhid if patient else '',
        'patient_name': f'{patient.first_name} {patient.last_name}' if patient else '',
        'doctor_id': o.doctor_id,
        'referring_doctor': (
            f"Dr. {o.doctor.first_name} {o.doctor.last_name}" if o.doctor else None
        ),
        'source_type': o.source_type,
        'test_name': o.test_name,
        'test_category': o.test_category,
        'status': o.status,
        'result_data': o.result_data,
        'billing_id': o.billing_id,
        'created_at': o.created_at.isoformat() if o.created_at else None,
        'updated_at': o.updated_at.isoformat() if o.updated_at else None,
        'generated_reports': generated
    }


def _create_lab_order_row(patient_id, test_name, source_type, doctor_id, test_category=None, notes=None):
    if not _validate_lab_order_source(source_type, doctor_id):
        raise ValueError('Invalid source_type and doctor_id combination')

    cat_entry = _catalog_entry(test_name)
    category = test_category or cat_entry['category']
    price = cat_entry['price']

    desc = f'Lab: {test_name[:200]}'
    bill = Billing(
        patient_id=patient_id,
        doctor_id=doctor_id,
        amount=float(price),
        description=desc,
        status='Unpaid',
    )
    db.session.add(bill)
    db.session.flush()

    payload = {}
    if notes:
        payload['order_notes'] = notes

    order = LabOrder(
        patient_id=patient_id,
        doctor_id=doctor_id,
        source_type=source_type,
        test_name=test_name[:200],
        test_category=category[:100] if category else 'General',
        status='CREATED',
        result_data=json.dumps(payload) if payload else None,
        billing_id=bill.id,
    )
    db.session.add(order)
    db.session.flush()
    return order


# ─── Dashboard (HTML) ───────────────────────────────────────────────────
@lab_bp.route('/')
@lab_bp.route('/dashboard')
@login_required
@lab_access_required
def dashboard():
    """Unified lab dashboard — LabOrder workflow."""
    # ✅ DEBUG: Verify session persistence
    print(f"[LAB_DASHBOARD] protected route accessed")
    print(f"  is_authenticated={current_user.is_authenticated}")
    print(f"  user_id={current_user.id}")
    print(f"  role={current_user.role}")
    print(f"  session_keys={list(session.keys())}")
    print(f"  session_get('_user_id')={session.get('_user_id')}")
    print(f"  cookies={dict(request.cookies)}")
    try:
        q = _lab_orders_base_query()

        status_filter = request.args.get('status', 'all')
        flow_filter = request.args.get('filter', 'all')

        if status_filter and status_filter != 'all':
            q = q.filter(LabOrder.status == status_filter)

        if flow_filter == 'walkin':
            q = q.filter(LabOrder.source_type == SOURCE_WALK_IN)
        elif flow_filter == 'doctor':
            q = q.filter(LabOrder.source_type == SOURCE_DOCTOR)

        search_q = request.args.get('search', '').strip()
        if search_q:
            q = q.join(Patient, LabOrder.patient_id == Patient.id).filter(
                db.or_(
                    Patient.uhid.ilike(f'%{search_q.upper()}%'),
                    Patient.first_name.ilike(f'%{search_q}%'),
                    Patient.last_name.ilike(f'%{search_q}%'),
                    Patient.phone.ilike(f'%{search_q}%'),
                    LabOrder.test_name.ilike(f'%{search_q}%'),
                )
            )

        orders = q.order_by(LabOrder.created_at.desc()).all()

        all_q = _lab_orders_base_query()
        total = all_q.count()
        pending = all_q.filter(LabOrder.status == 'CREATED').count()
        sample_collected = all_q.filter(LabOrder.status == 'SAMPLE_COLLECTED').count()
        processing = all_q.filter(LabOrder.status == 'PROCESSING').count()
        completed = all_q.filter(LabOrder.status == 'COMPLETED').count()

        return render_template(
            'lab/dashboard.html',
            orders=orders,
            total=total,
            pending=pending,
            sample_collected=sample_collected,
            processing=processing,
            completed=completed,
            status_filter=status_filter,
            flow_filter=flow_filter,
            search_q=search_q,
            SOURCE_DOCTOR=SOURCE_DOCTOR,
            SOURCE_WALK_IN=SOURCE_WALK_IN,
            LAB_UI_BUILD_ID=LAB_UI_BUILD_ID,
        )
    except Exception as e:
        logger.exception(f"Error in lab dashboard: {e}")
        return f"Dashboard Error: {str(e)}", 500


# ─── API: create order (doctor / reception / lab admin) ──────────────────
@lab_bp.route('/create-order', methods=['POST'])
@login_required
def create_order():
    """
    Create one or more lab orders. JSON:
    {
      "patient_id": 1,
      "tests": [ {"test_name": "CBC", "test_category": "Hematology"} ],
      "source_type": "DOCTOR" | "WALK_IN",
      "notes": "optional"
    }
    Single-test shortcut: "test_name" at top level instead of tests[].
    """
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    notes = (data.get('notes') or '').strip() or None
    source_type = (data.get('source_type') or '').strip().upper()
    if source_type not in (SOURCE_DOCTOR, SOURCE_WALK_IN):
        return jsonify({'success': False, 'error': 'source_type must be DOCTOR or WALK_IN'}), 400

    tests = data.get('tests')
    if not tests:
        tn = (data.get('test_name') or '').strip()
        if not tn:
            return jsonify({'success': False, 'error': 'tests or test_name required'}), 400
        tests = [{'test_name': tn, 'test_category': data.get('test_category')}]

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    doctor_id = None
    if source_type == SOURCE_DOCTOR:
        if current_user.role not in (UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
            return jsonify({'success': False, 'error': 'Only doctors can create doctor-referred orders'}), 403
        if not hasattr(current_user, 'doctor') or not current_user.doctor:
            return jsonify({'success': False, 'error': 'Doctor profile required'}), 400
        doctor_id = current_user.doctor.id
    else:
        if current_user.role not in (
            UserRole.RECEPTIONIST, UserRole.LAB_STAFF, UserRole.HOST, UserRole.ADMIN
        ):
            return jsonify({'success': False, 'error': 'Reception or lab staff required for walk-in orders'}), 403

    created_ids = []
    try:
        for t in tests:
            name = (t.get('test_name') if isinstance(t, dict) else str(t)).strip()
            if not name:
                continue
            cat = (t.get('test_category') if isinstance(t, dict) else None) or None
            order = _create_lab_order_row(
                patient.id, name, source_type, doctor_id,
                test_category=cat, notes=notes,
            )
            created_ids.append(order.id)
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.exception('create_order')
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'order_ids': created_ids})


# ─── API: list orders (JSON, polling) ────────────────────────────────────
@lab_bp.route('/orders', methods=['GET'])
@login_required
@lab_access_required
def orders_api():
    q = _lab_orders_base_query()

    status_filter = request.args.get('status', 'all')
    flow_filter = request.args.get('filter', 'all')

    if status_filter and status_filter != 'all':
        q = q.filter(LabOrder.status == status_filter)

    if flow_filter == 'walkin':
        q = q.filter(LabOrder.source_type == SOURCE_WALK_IN)
    elif flow_filter == 'doctor':
        q = q.filter(LabOrder.source_type == SOURCE_DOCTOR)

    search_q = request.args.get('search', '').strip()
    if search_q:
        q = q.join(Patient, LabOrder.patient_id == Patient.id).filter(
            db.or_(
                Patient.uhid.ilike(f'%{search_q.upper()}%'),
                Patient.first_name.ilike(f'%{search_q}%'),
                Patient.last_name.ilike(f'%{search_q}%'),
                Patient.phone.ilike(f'%{search_q}%'),
                LabOrder.test_name.ilike(f'%{search_q}%'),
            )
        )

    rows = q.order_by(LabOrder.created_at.desc()).limit(500).all()
    return jsonify({'success': True, 'orders': [_order_to_dict(o) for o in rows]})


# ─── API: update status ─────────────────────────────────────────────────
@lab_bp.route('/update-status', methods=['POST'])
@lab_bp.route('/api/update-status', methods=['POST'])
@login_required
@lab_staff_only
def update_status():
    """Advance lab order status."""
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id') or data.get('report_id')
    new_status = (data.get('status') or '').strip().upper()

    if new_status not in LAB_ORDER_STATUSES:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    order = LabOrder.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    logger.info(f"LabOrder #{order_id} status → {new_status}")
    return jsonify({'success': True, 'order': _order_to_dict(order)})



# ─── Complete test (result + COMPLETED) ───────────────────────────────────
@lab_bp.route('/complete-order', methods=['POST'])
@login_required
@lab_staff_only
def complete_order():
    """Mark order COMPLETED; optional result_data merge."""
    data = request.get_json(silent=True) or {}
    order = LabOrder.query.get(data.get('order_id'))
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    extra = data.get('result_data')
    if isinstance(extra, dict):
        merged = {}
        if order.result_data:
            try:
                merged = json.loads(order.result_data)
                if not isinstance(merged, dict):
                    merged = {}
            except json.JSONDecodeError:
                merged = {}
        merged.update(extra)
        merged['completed_at'] = datetime.utcnow().isoformat()
        order.result_data = json.dumps(merged)

    order.status = 'COMPLETED'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'order': _order_to_dict(order)})


@lab_bp.route('/api/template/<path:test_name>', methods=['GET'])
@login_required
def get_template(test_name):
    # Retrieve template matching test_name
    from app.models.models import LabTestTemplate
    template = LabTestTemplate.query.filter_by(test_name=test_name).first()
    
    if not template:
        # Fallback to simple result string to allow dynamic tests
        return jsonify({
            "success": True,
            "name": test_name,
            "fields": '{"Result": "Value"}',
            "ranges": '{"Result": "N/A"}'
        })

    return jsonify({
        "success": True,
        "name": template.test_name,
        "fields": template.fields,
        "ranges": template.normal_ranges
    })

@lab_bp.route('/report/save', methods=['POST'])
@login_required
@lab_staff_only
def save_report():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    report_data = data.get('report_data')

    if not order_id or not report_data:
        return jsonify({"success": False, "error": "Order ID and report data required"}), 400

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid order ID"}), 400

    order = LabOrder.query.get(order_id)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    try:
        # Save to LabReport
        from app.models.models import LabReport

        # Normalize to dict for JSON column compatibility.
        stored_data = report_data
        if isinstance(report_data, str):
            try:
                parsed = json.loads(report_data)
                stored_data = parsed if isinstance(parsed, dict) else {"Result": report_data}
            except json.JSONDecodeError:
                stored_data = {"Result": report_data}
        elif not isinstance(report_data, dict):
            stored_data = {"Result": str(report_data)}
        
        if isinstance(stored_data, dict):
            normalized = {}
            for k, v in stored_data.items():
                key = str(k).strip()
                if not key:
                    continue
                value = v.strip() if isinstance(v, str) else v
                normalized[key] = value
            stored_data = normalized

            has_any_value = any(
                (v is not None) and (str(v).strip() != '')
                for v in stored_data.values()
            )
            if not has_any_value:
                return jsonify({"success": False, "error": "Please enter at least one result value before saving"}), 400

        report_file_path = stored_data.get('file_path') if isinstance(stored_data, dict) else None

        # Upsert one report per order so UI always opens the latest data.
        report = LabReport.query.filter_by(lab_order_id=order.id).order_by(LabReport.id.desc()).first()
        if report:
            report.patient_id = order.patient_id
            report.test_name = order.test_name
            report.doctor_id = order.doctor_id
            report.file_path = report_file_path
            report.report_data = stored_data
            report.status = 'Completed'
            report.conducted_at = datetime.utcnow()
            report.updated_at = datetime.utcnow()
        else:
            report = LabReport(
                patient_id=order.patient_id,
                lab_order_id=order.id,
                test_name=order.test_name,
                doctor_id=order.doctor_id,
                file_path=report_file_path,
                report_data=stored_data,
                status='Completed'
            )
            db.session.add(report)

        # Complete the order
        order.status = 'COMPLETED'
        order.updated_at = datetime.utcnow()
        order.result_data = json.dumps(stored_data) if isinstance(stored_data, dict) else str(stored_data)
        
        db.session.commit()
        return jsonify({"success": True, "report_id": report.id})
    except Exception as e:
        db.session.rollback()
        logger.exception(f"save_report error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@lab_bp.route('/report/view/<int:report_id>')
def view_report(report_id):
    from app.models.models import LabReport, LabTestTemplate
    report = LabReport.query.get_or_404(report_id)
    template = LabTestTemplate.query.filter_by(test_name=report.test_name).first()
    ranges = template.normal_ranges if template else {}

    if isinstance(ranges, str):
        try:
            ranges = json.loads(ranges)
        except json.JSONDecodeError:
            ranges = {}
    if not isinstance(ranges, dict):
        ranges = {}

    report_data = report.report_data or {}
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except json.JSONDecodeError:
            report_data = {}
    if not isinstance(report_data, dict):
        report_data = {}

    report_date = report.conducted_at or report.updated_at

    # Build display rows from template first (so reports always show expected parameters),
    # then append any extra keys found in stored report data.
    template_fields = template.fields if template else {}
    if isinstance(template_fields, str):
        try:
            template_fields = json.loads(template_fields)
        except json.JSONDecodeError:
            template_fields = {}
    if not isinstance(template_fields, dict):
        template_fields = {}

    report_rows = []
    seen = set()

    for field_name, unit_text in template_fields.items():
        value = report_data.get(field_name, '')
        report_rows.append({
            'name': field_name,
            'value': value if value not in (None, '') else '-',
            'unit': unit_text or '-',
            'range': ranges.get(field_name, '-') if isinstance(ranges, dict) else '-',
        })
        seen.add(field_name)

    for field_name, value in report_data.items():
        if field_name in seen:
            continue
        report_rows.append({
            'name': field_name,
            'value': value if value not in (None, '') else '-',
            'unit': '-',
            'range': ranges.get(field_name, '-') if isinstance(ranges, dict) else '-',
        })

    if not report_rows:
        # Fallback for legacy records (old code path: result_value/unit/reference_range stored directly)
        if report.result_value:
            report_rows.append({
                'name': 'Result',
                'value': report.result_value,
                'unit': report.unit or '-',
                'range': report.reference_range or '-',
            })
        elif report_data:
            # If report_data exists but got filtered, use raw keys
            for field_name, value in report_data.items():
                report_rows.append({
                    'name': field_name,
                    'value': value if value not in (None, '') else '-',
                    'unit': '-',
                    'range': ranges.get(field_name, '-') if isinstance(ranges, dict) else '-',
                })

    return render_template(
        'lab/report_view.html',
        report=report,
        ranges=ranges,
        report_data=report_data,
        report_date=report_date,
        report_rows=report_rows,
    )


@lab_bp.route('/report/pdf/<int:report_id>')
def download_report_pdf(report_id):
    """Download lab report as PDF from lab module."""
    from app.models.models import LabReport, LabTestTemplate
    from fpdf import FPDF

    report = LabReport.query.get_or_404(report_id)
    template = LabTestTemplate.query.filter_by(test_name=report.test_name).first()
    ranges = template.normal_ranges if template else {}

    if isinstance(ranges, str):
        try:
            ranges = json.loads(ranges)
        except json.JSONDecodeError:
            ranges = {}
    if not isinstance(ranges, dict):
        ranges = {}

    report_data = report.report_data or {}
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except json.JSONDecodeError:
            report_data = {}
    if not isinstance(report_data, dict):
        report_data = {}

    template_fields = template.fields if template else {}
    if isinstance(template_fields, str):
        try:
            template_fields = json.loads(template_fields)
        except json.JSONDecodeError:
            template_fields = {}
    if not isinstance(template_fields, dict):
        template_fields = {}

    rows = []
    seen = set()
    for field_name, unit_text in template_fields.items():
        rows.append({
            'name': field_name,
            'value': report_data.get(field_name, '-') or '-',
            'unit': unit_text or '-',
            'range': ranges.get(field_name, '-') if isinstance(ranges, dict) else '-',
        })
        seen.add(field_name)

    for field_name, value in report_data.items():
        if field_name in seen:
            continue
        rows.append({
            'name': field_name,
            'value': value if value not in (None, '') else '-',
            'unit': '-',
            'range': ranges.get(field_name, '-') if isinstance(ranges, dict) else '-',
        })

    if not rows and report.result_value:
        rows.append({
            'name': 'Result',
            'value': report.result_value or '-',
            'unit': report.unit or '-',
            'range': report.reference_range or '-',
        })

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'CarePoint Health - Lab Report', ln=True, align='C')
    pdf.ln(4)

    patient_name = f"{report.patient.first_name} {report.patient.last_name}" if report.patient else '-'
    uhid = report.patient.uhid if report.patient and report.patient.uhid else (report.patient.id if report.patient else '-')
    report_date = report.conducted_at or report.updated_at

    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, f'Report ID: LAB-{report.id}', ln=True)
    pdf.cell(0, 7, f'Patient: {patient_name}', ln=True)
    pdf.cell(0, 7, f'UHID / Patient ID: {uhid}', ln=True)
    pdf.cell(0, 7, f'Test: {report.test_name or "-"}', ln=True)
    pdf.cell(0, 7, f'Date: {report_date.strftime("%d %b %Y, %I:%M %p") if report_date else "-"}', ln=True)
    pdf.ln(4)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(55, 8, 'Parameter', border=1, align='C')
    pdf.cell(35, 8, 'Result', border=1, align='C')
    pdf.cell(35, 8, 'Units', border=1, align='C')
    pdf.cell(65, 8, 'Reference Range', border=1, ln=True, align='C')

    pdf.set_font('Arial', '', 10)
    for row in rows or [{'name': 'Result', 'value': '-', 'unit': '-', 'range': '-'}]:
        pdf.cell(55, 8, str(row['name'])[:30], border=1)
        pdf.cell(35, 8, str(row['value'])[:20], border=1)
        pdf.cell(35, 8, str(row['unit'])[:20], border=1)
        pdf.cell(65, 8, str(row['range'])[:38], border=1, ln=True)

    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 6, 'This is an electronically generated report. No signature is required.')

    output = pdf.output(dest='S').encode('latin-1')
    return Response(
        output,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=lab_report_{report.id}.pdf'}
    )


# ─── Legacy LabReport status API (kept for old clients) ──────────────────
@lab_bp.route('/api/legacy-report-status', methods=['POST'])
@login_required
@lab_staff_only
def legacy_report_status():
    data = request.get_json()
    report_id = data.get('report_id')
    new_status = data.get('status')
    remarks = data.get('remarks', '')

    if new_status not in ('Pending', 'In Progress', 'Completed'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    report = LabReport.query.get(report_id)
    if not report:
        return jsonify({'success': False, 'error': 'Report not found'}), 404

    report.status = new_status
    if remarks:
        report.remarks = remarks
    db.session.commit()

    logger.info(f"Lab report #{report_id} status → {new_status}")
    return jsonify({'success': True})


# ─── Request New Lab Test (Doctor modal on lab page) ─────────────────────
@lab_bp.route('/api/request-test', methods=['POST'])
@login_required
def request_test():
    """Doctor creates doctor-referred LabOrder(s)."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
        return jsonify({'success': False, 'error': 'Only doctors can request tests'}), 403
    if not hasattr(current_user, 'doctor') or not current_user.doctor:
        return jsonify({'success': False, 'error': 'Doctor profile required'}), 400

    data = request.get_json()
    patient_id = data.get('patient_id')
    test_name = data.get('test_name')

    if not patient_id or not test_name:
        return jsonify({'success': False, 'error': 'Patient and test name required'}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    try:
        order = _create_lab_order_row(
            patient.id,
            test_name.strip(),
            SOURCE_DOCTOR,
            current_user.doctor.id,
            notes=(data.get('notes') or '').strip() or None,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('request_test')
        return jsonify({'success': False, 'error': str(e)}), 500

    logger.info(f"LabOrder '{test_name}' for patient #{patient_id}")
    return jsonify({'success': True, 'order_id': order.id, 'report_id': order.id})


# ─── Search patients (AJAX) ─────────────────────────────────────────────
@lab_bp.route('/api/search-patients')
@login_required
@lab_access_required
def search_patients():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    patients = Patient.query.filter(
        db.or_(
            Patient.uhid.ilike(f'%{q.upper()}%'),
            Patient.first_name.ilike(f'%{q}%'),
            Patient.last_name.ilike(f'%{q}%'),
            Patient.phone.ilike(f'%{q}%'),
        )
    ).limit(10).all()

    return jsonify([{
        'id': p.id,
        'name': f"{p.first_name} {p.last_name}",
        'uhid': p.uhid,
        'phone': p.phone,
        'age': p.age,
        'gender': p.gender
    } for p in patients])



# ─── Add Remarks (legacy LabReport) ────────────────────────────────────
@lab_bp.route('/api/add-remarks', methods=['POST'])
@login_required
@lab_staff_only
def add_remarks():
    data = request.get_json()
    report = LabReport.query.get(data.get('report_id'))
    if not report:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    report.remarks = data.get('remarks', '')
    db.session.commit()
    return jsonify({'success': True})


@lab_bp.route('/download-order-file/<int:order_id>')
@login_required
def download_order_file(order_id):
    """Download the result attachment for a lab order."""
    from flask import send_file, abort

    order = LabOrder.query.get_or_404(order_id)
    rel_path = order.result_attachment_rel_path()
    if not rel_path:
        # Fallback: if the order has a generated report with a PDF, redirect there
        for report in (order.generated_reports or []):
            return redirect(url_for('lab.download_report_pdf', report_id=report.id))
        abort(404)

    # Resolve absolute path
    abs_path = os.path.join(current_app.root_path, '..', rel_path)
    if not os.path.isfile(abs_path):
        abs_path = os.path.join(current_app.root_path, rel_path)
    if not os.path.isfile(abs_path):
        abort(404)

    return send_file(abs_path, as_attachment=True)
