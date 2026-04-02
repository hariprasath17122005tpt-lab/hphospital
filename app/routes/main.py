from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort, send_from_directory, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app.models.models import Medicine, UserRole, LabReport, LabTestTemplate, FrontpageDoctor, SystemSettings
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import os
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - redirects to dashboard if logged in"""
    if current_user.is_authenticated:
        role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        destinations = {
            'PATIENT': 'patient.dashboard',
            'DOCTOR': 'doctor.dashboard',
            'HOST': 'host.dashboard',
            'ADMIN': 'host.dashboard',
            'NURSE': 'nurse.dashboard',
            'LAB_STAFF': 'lab.dashboard',
            'PHARMACIST': 'pharmacy_ops.dashboard',
            'RECEPTIONIST': 'reception.dashboard',
        }
        endpoint = destinations.get(role)
        if endpoint:
            return redirect(url_for(endpoint))
    frontpage_doctors = FrontpageDoctor.query.filter_by(is_active=True).order_by(
        FrontpageDoctor.display_order.asc(), FrontpageDoctor.id.asc()).all()
    settings = SystemSettings.query.first()
    whatsapp = settings.whatsapp_number if settings and settings.whatsapp_number else '919443966329'
    return render_template('index.html', frontpage_doctors=frontpage_doctors, whatsapp_number=whatsapp)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@main_bp.route('/api/health-status', methods=['GET'])
@login_required
def api_health_status():
    """API endpoint for health status"""
    return jsonify({'status': 'ok', 'user': current_user.username})


@main_bp.route('/search_medicine')
@login_required
def search_medicine():
    """Global medicine autocomplete endpoint used by prescription UI."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN):
        return jsonify([]), 403

    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])

    try:
        limit = int(request.args.get('limit', 12))
    except (TypeError, ValueError):
        limit = 12
    limit = max(1, min(limit, 25))

    prefix = f"{q}%"
    contains = f"%{q}%"

    medicines = (
        Medicine.query
        .filter(Medicine.name.ilike(contains))
        .order_by(
            case((Medicine.name.ilike(prefix), 0), else_=1),
            func.length(Medicine.name),
            Medicine.name.asc()
        )
        .limit(limit)
        .all()
    )

    names = []
    seen = set()
    for med in medicines:
        if not med.name:
            continue
        key = med.name.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        names.append(med.name)

    return jsonify(names)


@main_bp.route('/check_medicine', methods=['POST'])
@login_required
def check_medicine():
    """Global medicine stock check endpoint used by prescription UI."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.PHARMACIST, UserRole.HOST, UserRole.ADMIN):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    medicine = (data.get('medicine') or '').strip()
    if not medicine:
        return jsonify({'success': False, 'error': 'medicine is required'}), 400

    med = Medicine.query.filter(func.lower(Medicine.name) == medicine.lower()).first()
    if med is None:
        med = Medicine.query.filter(Medicine.name.ilike(medicine)).first()

    if med is None:
        return jsonify({
            'name': medicine,
            'status': 'not_found',
            'stock_quantity': 0
        })

    return jsonify({
        'name': med.name,
        'status': 'available' if (med.stock or 0) > 0 else 'out_of_stock',
        'stock_quantity': int(med.stock or 0)
    })


def _normalize_report_payload(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _build_report_rows(report):
    template = LabTestTemplate.query.filter_by(test_name=report.test_name).first()
    report_data = _normalize_report_payload(report.report_data)
    ranges = _normalize_report_payload(template.normal_ranges if template else {})
    fields = _normalize_report_payload(template.fields if template else {})

    rows = []
    seen = set()
    for field_name, unit_text in fields.items():
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
    return rows


def _render_pdf_file(report, pdf_path, rows):
    def _safe_pdf_text(value):
        return str(value or '-').encode('latin-1', errors='replace').decode('latin-1')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'CarePoint Health - Lab Report', ln=True, align='C')
    pdf.ln(4)

    patient_name = report.patient.full_name if report.patient else '-'
    uhid = report.patient.uhid if report.patient and report.patient.uhid else (report.patient.id if report.patient else '-')
    report_date = report.conducted_at or report.updated_at

    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, _safe_pdf_text(f'Report ID: LAB-{report.id}'), ln=True)
    pdf.cell(0, 7, _safe_pdf_text(f'Patient: {patient_name}'), ln=True)
    pdf.cell(0, 7, _safe_pdf_text(f'UHID / Patient ID: {uhid}'), ln=True)
    pdf.cell(0, 7, _safe_pdf_text(f'Test: {report.test_name or "-"}'), ln=True)
    pdf.cell(0, 7, _safe_pdf_text(f'Date: {report_date.strftime("%d %b %Y, %I:%M %p") if report_date else "-"}'), ln=True)
    pdf.ln(4)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(55, 8, 'Parameter', border=1, align='C')
    pdf.cell(35, 8, 'Result', border=1, align='C')
    pdf.cell(35, 8, 'Units', border=1, align='C')
    pdf.cell(65, 8, 'Reference Range', border=1, ln=True, align='C')

    pdf.set_font('Arial', '', 10)
    for row in rows or [{'name': 'Result', 'value': '-', 'unit': '-', 'range': '-'}]:
        pdf.cell(55, 8, _safe_pdf_text(str(row['name'])[:30]), border=1)
        pdf.cell(35, 8, _safe_pdf_text(str(row['value'])[:20]), border=1)
        pdf.cell(35, 8, _safe_pdf_text(str(row['unit'])[:20]), border=1)
        pdf.cell(65, 8, _safe_pdf_text(str(row['range'])[:38]), border=1, ln=True)

    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 6, 'This is an electronically generated report. No signature is required.')
    pdf.output(pdf_path)


def _render_png_file(report, png_path, rows):
    width, height = 1240, 1754
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()

    x = 60
    y = 50
    line_h = 24

    draw.text((x, y), 'CarePoint Health - Lab Report', fill='black', font=title_font)
    y += line_h * 2

    patient_name = report.patient.full_name if report.patient else '-'
    uhid = report.patient.uhid if report.patient and report.patient.uhid else (report.patient.id if report.patient else '-')
    report_date = report.conducted_at or report.updated_at

    meta_lines = [
        f'Report ID: LAB-{report.id}',
        f'Patient: {patient_name}',
        f'UHID / Patient ID: {uhid}',
        f'Test: {report.test_name or "-"}',
        f'Date: {report_date.strftime("%d %b %Y, %I:%M %p") if report_date else "-"}',
        '',
        'Parameter | Result | Units | Reference Range',
        '------------------------------------------------------------'
    ]
    for line in meta_lines:
        draw.text((x, y), line, fill='black', font=text_font)
        y += line_h

    for row in rows[:45]:
        line = f"{str(row['name'])[:26]} | {str(row['value'])[:14]} | {str(row['unit'])[:10]} | {str(row['range'])[:24]}"
        draw.text((x, y), line, fill='black', font=text_font)
        y += line_h
        if y > height - 80:
            break

    draw.text((x, height - 50), 'Electronically generated report.', fill='black', font=text_font)
    image.save(png_path, format='PNG')


def _ensure_report_assets(report_id):
    report = LabReport.query.get(report_id)
    if not report:
        return None, None, None

    reports_dir = os.path.join(current_app.static_folder, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    pdf_filename = f'report_{report_id}.pdf'
    png_filename = f'report_{report_id}.png'
    pdf_path = os.path.join(reports_dir, pdf_filename)
    png_path = os.path.join(reports_dir, png_filename)

    rows = _build_report_rows(report)

    if not os.path.exists(pdf_path):
        _render_pdf_file(report, pdf_path, rows)
    if not os.path.exists(png_path):
        _render_png_file(report, png_path, rows)

    return report, pdf_filename, png_filename


@main_bp.route('/reports/<int:report_id>/image')
def view_report_image(report_id):
    _, _, png_filename = _ensure_report_assets(report_id)
    if not png_filename:
        abort(404)
    reports_dir = os.path.join(current_app.static_folder, 'reports')
    file_path = os.path.join(reports_dir, png_filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(reports_dir, png_filename)


@main_bp.route('/reports/<int:report_id>/pdf')
def get_report_pdf(report_id):
    _, pdf_filename, _ = _ensure_report_assets(report_id)
    if not pdf_filename:
        abort(404)
    reports_dir = os.path.join(current_app.static_folder, 'reports')
    file_path = os.path.join(reports_dir, pdf_filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(reports_dir, pdf_filename)


@main_bp.route('/reports/<int:report_id>/download')
def download_report(report_id):
    _, pdf_filename, _ = _ensure_report_assets(report_id)
    if not pdf_filename:
        abort(404)
    reports_dir = os.path.join(current_app.static_folder, 'reports')
    file_path = os.path.join(reports_dir, pdf_filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(reports_dir, pdf_filename, as_attachment=True)
