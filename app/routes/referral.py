from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import db, Doctor, Patient, PatientReferral
from app.routes.auth import doctor_required
from datetime import datetime

referral_bp = Blueprint('referral', __name__, url_prefix='/referral')


def _get_current_doctor():
    """Return the Doctor record for the currently logged-in doctor user."""
    return Doctor.query.filter_by(user_id=current_user.id).first()


@referral_bp.route('/')
@login_required
@doctor_required
def dashboard():
    """Referral management dashboard for the logged-in doctor."""
    doctor = _get_current_doctor()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('doctor.portal'))

    outgoing = (
        PatientReferral.query
        .filter_by(referring_doctor_id=doctor.id)
        .order_by(PatientReferral.created_at.desc())
        .all()
    )

    incoming = (
        PatientReferral.query
        .filter_by(referred_to_doctor_id=doctor.id)
        .order_by(PatientReferral.created_at.desc())
        .all()
    )

    # Patients assigned to this doctor (for the create form)
    patients = (
        Patient.query
        .join(db.session.query(db.func.literal(1)).filter(db.literal(True)).subquery(), db.literal(True))
        .order_by(Patient.name)
        .limit(500)
        .all()
    )
    # Simpler: just grab all patients (limited)
    patients = Patient.query.order_by(Patient.name).limit(500).all()

    # All verified doctors for the referral target selector
    doctors = (
        Doctor.query
        .filter(Doctor.verified == True, Doctor.is_deleted == False, Doctor.is_suspended == False, Doctor.id != doctor.id)
        .order_by(Doctor.first_name)
        .all()
    )

    return render_template(
        'referral/dashboard.html',
        doctor=doctor,
        outgoing=outgoing,
        incoming=incoming,
        patients=patients,
        doctors=doctors,
    )


@referral_bp.route('/create', methods=['POST'])
@login_required
@doctor_required
def create():
    """Create a new patient referral."""
    doctor = _get_current_doctor()
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found.'}), 400

    data = request.get_json() if request.is_json else request.form

    patient_id = data.get('patient_id')
    referral_type = data.get('referral_type', 'Internal')
    referred_to_doctor_id = data.get('referred_to_doctor_id') or None
    referred_to_department = data.get('referred_to_department', '').strip()
    referred_to_external = data.get('referred_to_external', '').strip()
    reason = data.get('reason', '').strip()
    clinical_notes = data.get('clinical_notes', '').strip()
    urgency = data.get('urgency', 'Routine')

    if not patient_id or not reason:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Patient and reason are required.'}), 400
        flash('Patient and reason are required.', 'danger')
        return redirect(url_for('referral.dashboard'))

    referral = PatientReferral(
        patient_id=int(patient_id),
        referring_doctor_id=doctor.id,
        referred_to_doctor_id=int(referred_to_doctor_id) if referred_to_doctor_id else None,
        referred_to_department=referred_to_department or None,
        referred_to_external=referred_to_external or None,
        referral_type=referral_type,
        reason=reason,
        clinical_notes=clinical_notes or None,
        urgency=urgency,
    )

    db.session.add(referral)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Failed to create referral: {e}', 'danger')
        return redirect(url_for('referral.dashboard'))

    if request.is_json:
        return jsonify({'success': True, 'referral_id': referral.id})

    flash('Referral created successfully.', 'success')
    return redirect(url_for('referral.dashboard'))


@referral_bp.route('/api/update', methods=['POST'])
@login_required
@doctor_required
def api_update():
    """Update the status of a referral (accept / decline / complete)."""
    doctor = _get_current_doctor()
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found.'}), 400

    data = request.get_json() if request.is_json else request.form

    referral_id = data.get('referral_id')
    new_status = data.get('status', '').strip()

    if not referral_id or not new_status:
        return jsonify({'success': False, 'error': 'referral_id and status are required.'}), 400

    valid_statuses = ['Pending', 'Accepted', 'Completed', 'Declined']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    referral = PatientReferral.query.get(int(referral_id))
    if not referral:
        return jsonify({'success': False, 'error': 'Referral not found.'}), 404

    # Only the referring or referred doctor can update
    if referral.referring_doctor_id != doctor.id and referral.referred_to_doctor_id != doctor.id:
        return jsonify({'success': False, 'error': 'You are not authorized to update this referral.'}), 403

    referral.status = new_status
    referral.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'referral_id': referral.id, 'status': referral.status})


@referral_bp.route('/api/incoming')
@login_required
@doctor_required
def api_incoming():
    """Get incoming referrals for the current doctor (JSON)."""
    doctor = _get_current_doctor()
    if not doctor:
        return jsonify({'success': False, 'error': 'Doctor profile not found.'}), 400

    incoming = (
        PatientReferral.query
        .filter_by(referred_to_doctor_id=doctor.id)
        .order_by(PatientReferral.created_at.desc())
        .all()
    )

    results = []
    for r in incoming:
        results.append({
            'id': r.id,
            'patient_name': r.patient.full_name if r.patient else 'Unknown',
            'referring_doctor': f'Dr. {r.referring_doctor.first_name} {r.referring_doctor.last_name}' if r.referring_doctor else 'Unknown',
            'department': r.referred_to_department or '',
            'referral_type': r.referral_type or '',
            'reason': r.reason or '',
            'urgency': r.urgency or 'Routine',
            'status': r.status or 'Pending',
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
        })

    return jsonify({'success': True, 'referrals': results})
