"""
QR Visit System — QR code generation, scanning, and visit detail viewing.
Every OP/IP registration creates a unique QR linked to the visit (not just the patient).
"""
from flask import Blueprint, render_template, request, jsonify, url_for, current_app, send_file
from flask_login import login_required, current_user
from app.models.models import (
    db, Visit, Patient, Doctor, Consultation, Prescription, PrescriptionMedicine,
    LabOrder, LabReport, PatientVitals, NurseNote, Billing, BillItem,
    IPAdmission, PatientMedicalHistory,
)
from datetime import datetime
import uuid
import os
import logging

logger = logging.getLogger(__name__)

qr_bp = Blueprint('qr', __name__, url_prefix='/qr')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def generate_qr_token():
    """Generate a secure unique token for a visit QR."""
    return f"VISIT-{uuid.uuid4().hex[:12].upper()}"


def generate_qr_image(qr_token, base_url=None):
    """Generate QR image file and return its relative path under static/."""
    try:
        import qrcode
        from qrcode.image.styledpil import StyledPilImage
    except ImportError:
        import qrcode

    if base_url is None:
        base_url = request.host_url.rstrip('/')

    qr_url = f"{base_url}/qr/visit/{qr_token}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1f36", back_color="white")

    # Save to static/qr/
    qr_dir = os.path.join(current_app.static_folder, 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"{qr_token}.png"
    filepath = os.path.join(qr_dir, filename)
    img.save(filepath)

    return f"qr/{filename}"


def create_visit_qr(visit, base_url=None):
    """Attach a QR token and image to an existing Visit object (must be in an active session)."""
    if visit.qr_token:
        return visit.qr_token, visit.qr_image_path

    token = generate_qr_token()
    image_path = generate_qr_image(token, base_url=base_url)
    visit.qr_token = token
    visit.qr_image_path = image_path
    return token, image_path


# ─── Public: View visit details via QR ────────────────────────────────────────

@qr_bp.route('/visit/<qr_token>')
def view_visit(qr_token):
    """Public page — anyone with the QR link can view visit details."""
    visit = Visit.query.filter_by(qr_token=qr_token).first()
    if not visit:
        return render_template('qr/not_found.html'), 404

    patient = Patient.query.get(visit.patient_id)
    doctor = Doctor.query.get(visit.doctor_id) if visit.doctor_id else None

    # Medical history
    medical_history = PatientMedicalHistory.query.filter_by(
        patient_id=patient.id
    ).order_by(PatientMedicalHistory.created_at.desc()).all() if patient else []

    # Consultations for this visit
    consultations = Consultation.query.filter_by(patient_id=patient.id).order_by(
        Consultation.visit_date.desc()
    ).limit(5).all() if patient else []

    # Prescriptions
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.prescribed_at.desc()
    ).limit(10).all() if patient else []

    # Lab orders & reports
    lab_orders = LabOrder.query.filter_by(patient_id=patient.id).order_by(
        LabOrder.created_at.desc()
    ).limit(10).all() if patient else []

    lab_reports = LabReport.query.filter_by(patient_id=patient.id).order_by(
        LabReport.conducted_at.desc()
    ).limit(10).all() if patient else []

    # Vitals
    vitals = PatientVitals.query.filter_by(patient_id=patient.id).order_by(
        PatientVitals.recorded_at.desc()
    ).limit(5).all() if patient else []

    # Nurse notes
    nurse_notes = NurseNote.query.filter_by(patient_id=patient.id).order_by(
        NurseNote.created_at.desc()
    ).limit(10).all() if patient else []

    # Billing
    billing_records = Billing.query.filter_by(patient_id=patient.id).order_by(
        Billing.created_at.desc()
    ).limit(5).all() if patient else []

    # IP Admission (if IP visit)
    ip_admission = None
    if visit.visit_type == 'IP' and patient:
        ip_admission = IPAdmission.query.filter_by(
            patient_id=patient.id
        ).order_by(IPAdmission.admission_date.desc()).first()

    return render_template('qr/visit_detail.html',
        visit=visit,
        patient=patient,
        doctor=doctor,
        medical_history=medical_history,
        consultations=consultations,
        prescriptions=prescriptions,
        lab_orders=lab_orders,
        lab_reports=lab_reports,
        vitals=vitals,
        nurse_notes=nurse_notes,
        billing_records=billing_records,
        ip_admission=ip_admission,
    )


# ─── QR Scanner Page ─────────────────────────────────────────────────────────

@qr_bp.route('/scan')
def scan_page():
    """Page with camera-based QR scanner."""
    return render_template('qr/scan.html')


# ─── API: Generate QR for an existing visit ───────────────────────────────────

@qr_bp.route('/api/generate/<int:visit_id>', methods=['POST'])
def api_generate_qr(visit_id):
    """Generate QR for a visit that doesn't have one yet."""
    visit = Visit.query.get(visit_id)
    if not visit:
        return jsonify({'success': False, 'error': 'Visit not found'}), 404

    try:
        token, image_path = create_visit_qr(visit)
        db.session.commit()

        patient = Patient.query.get(visit.patient_id)
        return jsonify({
            'success': True,
            'qr_token': token,
            'qr_image_url': url_for('static', filename=image_path),
            'qr_visit_url': url_for('qr.view_visit', qr_token=token, _external=True),
            'patient_name': patient.name if patient else '',
            'uhid': patient.uhid if patient else '',
            'visit_id': visit.id,
            'visit_type': visit.visit_type,
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"QR generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── API: Get QR info for a visit ────────────────────────────────────────────

@qr_bp.route('/api/info/<int:visit_id>')
def api_qr_info(visit_id):
    """Get QR data for a visit (if already generated)."""
    visit = Visit.query.get(visit_id)
    if not visit:
        return jsonify({'success': False, 'error': 'Visit not found'}), 404

    if not visit.qr_token:
        return jsonify({'success': False, 'error': 'No QR generated for this visit'}), 404

    patient = Patient.query.get(visit.patient_id)
    doctor = Doctor.query.get(visit.doctor_id) if visit.doctor_id else None

    return jsonify({
        'success': True,
        'qr_token': visit.qr_token,
        'qr_image_url': url_for('static', filename=visit.qr_image_path) if visit.qr_image_path else None,
        'qr_visit_url': url_for('qr.view_visit', qr_token=visit.qr_token, _external=True),
        'patient_name': patient.name if patient else '',
        'uhid': patient.uhid if patient else '',
        'phone': patient.phone if patient else '',
        'visit_id': visit.id,
        'visit_type': visit.visit_type,
        'visit_date': visit.visit_date.strftime('%Y-%m-%d %H:%M') if visit.visit_date else '',
        'doctor_name': f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else 'Not assigned',
    })


# ─── Download QR image ───────────────────────────────────────────────────────

@qr_bp.route('/download/<qr_token>')
def download_qr(qr_token):
    """Download the QR image as a PNG file."""
    visit = Visit.query.filter_by(qr_token=qr_token).first()
    if not visit or not visit.qr_image_path:
        return "QR not found", 404

    filepath = os.path.join(current_app.static_folder, visit.qr_image_path)
    if not os.path.exists(filepath):
        return "QR image file not found", 404

    patient = Patient.query.get(visit.patient_id)
    download_name = f"QR_{patient.uhid}_{qr_token}.png" if patient else f"QR_{qr_token}.png"
    return send_file(filepath, as_attachment=True, download_name=download_name)
