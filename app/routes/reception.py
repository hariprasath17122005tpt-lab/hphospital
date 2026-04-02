"""
Reception / Queue Management Module â€” Patient flow management
Flow: Patient (books appointment/check-in) â†’ Reception (accepts/rejects) â†’ Doctor (accepts/cancels)
Accessible by: RECEPTIONIST (full), DOCTOR (view queue, respond), ADMIN/HOST
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user, login_user
from app.models.models import db, User, UserRole, Patient, Doctor, ReceptionQueue, Appointment, PatientCheckIn, Visit
from datetime import datetime, date
from functools import wraps
import logging

logger = logging.getLogger(__name__)

reception_bp = Blueprint('reception', __name__, url_prefix='/reception')


# Allow RECEPTIONIST, DOCTOR, HOST, ADMIN
def _is_api_request():
    accept = request.headers.get('Accept', '')
    return (
        request.path.startswith('/reception/api/') or
        request.path.startswith('/api/') or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in accept or
        request.is_json
    )


def _try_recover_staff_session():
    """
    Recover a dropped Flask-Login context from the signed session cookie.
    Some browser/runtime combinations can occasionally lose `current_user`
    during XHR calls while `_user_id` is still present in session.
    """
    if current_user.is_authenticated:
        return current_user

    raw_user_id = session.get('_user_id')
    if not raw_user_id:
        return None

    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        return None

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return None

    try:
        login_user(user, remember=False, force=True)
        logger.warning("Recovered staff session for user_id=%s on %s", user_id, request.path)
    except Exception:
        return None
    return user


def reception_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _try_recover_staff_session()
        if not current_user.is_authenticated:
            if _is_api_request():
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('auth.staff_login', role='RECEPTIONIST'))
        if current_user.role not in (UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
            if _is_api_request():
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.staff_login', role='RECEPTIONIST', switch='1'))
        return f(*args, **kwargs)
    return decorated


# Only RECEPTIONIST and HOST/ADMIN
def receptionist_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Log session info for debugging
        logger.info(f"Auth check: path={request.path}")
        logger.info(f"  current_user.is_authenticated={current_user.is_authenticated}")
        logger.info(f"  session._user_id={session.get('_user_id')}")
        logger.info(f"  X-Requested-With={request.headers.get('X-Requested-With')}")
        logger.info(f"  is_api_request={_is_api_request()}")
        
        _try_recover_staff_session()
        
        logger.info(f"  After recovery: current_user.is_authenticated={current_user.is_authenticated}")
        
        if not current_user.is_authenticated:
            logger.warning(f"Auth failed for {request.path} - user not authenticated")
            if _is_api_request():
                logger.info("  Returning 401 JSON (API request)")
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            logger.info("  Redirecting to login (not API request)")
            return redirect(url_for('auth.staff_login', role='RECEPTIONIST'))
        if current_user.role not in (UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.HOST, UserRole.ADMIN):
            logger.warning(f"Access denied for {request.path} - user role={current_user.role}")
            if _is_api_request():
                return jsonify({'success': False, 'error': 'Access denied. Receptionist only.'}), 403
            flash('Access denied. Receptionist only.', 'danger')
            return redirect(url_for('auth.staff_login', role='RECEPTIONIST', switch='1'))
        return f(*args, **kwargs)
    return decorated


# Generate next token number for today
def _next_token():
    today_start = datetime.combine(date.today(), datetime.min.time())
    last = ReceptionQueue.query.filter(
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.desc()).first()
    return (last.token_number + 1) if last else 1


def _resolve_queue_entry_for_doctor_action(entry_id=None, patient_id=None):
    """Resolve a queue row for doctor actions with a safe fallback by patient id."""
    entry = None

    if entry_id:
        entry = ReceptionQueue.query.get(entry_id)

    if entry:
        return entry

    # Backward compatibility: some clients may send patient_id in entry_id.
    if not patient_id and entry_id:
        patient_id = entry_id

    if not patient_id:
        return None

    today_start = datetime.combine(date.today(), datetime.min.time())
    query = ReceptionQueue.query.filter(
        ReceptionQueue.patient_id == patient_id,
        ReceptionQueue.reception_status == 'Accepted',
        ReceptionQueue.doctor_status.in_(['Pending', 'Accepted']),
        ReceptionQueue.created_at >= today_start
    )

    if current_user.role == UserRole.DOCTOR:
        doctor = getattr(current_user, 'doctor', None)
        if not doctor:
            return None
        query = query.filter(ReceptionQueue.doctor_id == doctor.id)

    return query.order_by(ReceptionQueue.created_at.desc()).first()


def _record_visit(patient_id, visit_type, doctor_id=None, notes=None, visit_date=None):
    visit = Visit(
        patient_id=patient_id,
        visit_type=visit_type,
        doctor_id=doctor_id,
        notes=notes,
        visit_date=visit_date or datetime.utcnow(),
    )
    db.session.add(visit)
    return visit


# â”€â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/')
@reception_bp.route('/dashboard')
@reception_access_required
def dashboard():
    """Reception dashboard â€” incoming bookings, queue, and stats"""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # â”€â”€ Incoming appointments (booked by patients, not yet in queue) â”€â”€
    incoming_appointments = Appointment.query.filter(
        Appointment.status.in_(['pending', 'confirmed']),
        Appointment.appointment_date >= today_start
    ).order_by(Appointment.created_at.desc()).all()

    # Filter out appointments already added to queue
    queued_appt_ids = [q.appointment_id for q in ReceptionQueue.query.filter(
        ReceptionQueue.appointment_id.isnot(None)
    ).all()]
    incoming_appointments = [a for a in incoming_appointments if a.id not in queued_appt_ids]

    # â”€â”€ Incoming check-ins (submitted by patients, not yet in queue) â”€â”€
    incoming_checkins = PatientCheckIn.query.filter(
        PatientCheckIn.status.in_(['pending']),
        PatientCheckIn.created_at >= today_start
    ).order_by(PatientCheckIn.created_at.desc()).all()

    queued_checkin_ids = [q.checkin_id for q in ReceptionQueue.query.filter(
        ReceptionQueue.checkin_id.isnot(None)
    ).all()]
    incoming_checkins = [c for c in incoming_checkins if c.id not in queued_checkin_ids]

    # â”€â”€ Today's queue entries â”€â”€
    today_queue = ReceptionQueue.query.filter(
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.asc()).all()

    # Stats
    waiting = sum(1 for q in today_queue if q.reception_status == 'Pending')
    accepted_by_reception = sum(1 for q in today_queue if q.reception_status == 'Accepted' and q.doctor_status == 'Pending')
    with_doctor = sum(1 for q in today_queue if q.doctor_status in ('Accepted', 'In Consultation'))
    completed = sum(1 for q in today_queue if q.status == 'Completed')
    cancelled_by_doctor = sum(1 for q in today_queue if q.doctor_status == 'Cancelled')

    # If doctor, filter to their queue
    doctor_queue = today_queue
    if current_user.role == UserRole.DOCTOR and hasattr(current_user, 'doctor') and current_user.doctor:
        doctor_queue = [q for q in today_queue
                       if q.doctor_id == current_user.doctor.id
                       and q.reception_status == 'Accepted']

    # Get list of doctors for assignment dropdown
    doctors = Doctor.query.filter_by(verified=True, is_suspended=False, is_deleted=False).all()

    return render_template('reception/dashboard.html',
                           incoming_appointments=incoming_appointments,
                           incoming_checkins=incoming_checkins,
                           queue=today_queue,
                           doctor_queue=doctor_queue,
                           waiting=waiting,
                           accepted_by_reception=accepted_by_reception,
                           with_doctor=with_doctor,
                           completed_count=completed,
                           cancelled_by_doctor=cancelled_by_doctor,
                           total=len(today_queue),
                           doctors=doctors)


@reception_bp.route('/history')
@receptionist_only
def patient_history():
    """Reception patient history workspace."""
    return render_template('reception/patient_history.html')


# â”€â”€â”€ Accept Appointment into Queue (Reception) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/accept-appointment', methods=['POST'])
@receptionist_only
def accept_appointment():
    """Reception accepts an appointment and adds patient to queue"""
    data = request.get_json()
    appointment_id = data.get('appointment_id')
    notes = data.get('notes', '')

    appt = Appointment.query.get(appointment_id)
    if not appt:
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404

    # Check if already in queue
    existing = ReceptionQueue.query.filter_by(appointment_id=appointment_id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Already in queue'}), 400

    token = _next_token()
    entry = ReceptionQueue(
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        token_number=token,
        status='Accepted by Reception',
        visit_reason=appt.reason,
        patient_type='Appointment',
        appointment_id=appt.id,
        reception_status='Accepted',
        reception_notes=notes,
        accepted_by_reception_at=datetime.utcnow(),
        sent_to_doctor_at=datetime.utcnow(),
        doctor_status='Pending',
        arrival_time=datetime.utcnow()
    )
    db.session.add(entry)
    _record_visit(
        patient_id=appt.patient_id,
        visit_type='OP',
        doctor_id=appt.doctor_id,
        notes=f"Reception accepted appointment. Reason: {appt.reason or 'General consultation'}",
        visit_date=appt.appointment_date or datetime.utcnow(),
    )

    # Update appointment status
    appt.status = 'confirmed'
    db.session.commit()

    logger.info(f"Appointment #{appointment_id} accepted, Token #{token}")
    return jsonify({
        'success': True,
        'token': token,
        'message': f'Patient accepted, Token #{token} assigned. Sent to doctor.'
    })


# â”€â”€â”€ Accept Check-in into Queue (Reception) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/accept-checkin', methods=['POST'])
@receptionist_only
def accept_checkin():
    """Reception accepts a check-in and adds patient to queue"""
    data = request.get_json()
    checkin_id = data.get('checkin_id')
    notes = data.get('notes', '')

    ci = PatientCheckIn.query.get(checkin_id)
    if not ci:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404

    existing = ReceptionQueue.query.filter_by(checkin_id=checkin_id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Already in queue'}), 400

    token = _next_token()
    entry = ReceptionQueue(
        patient_id=ci.patient_id,
        doctor_id=ci.doctor_id,
        token_number=token,
        status='Accepted by Reception',
        visit_reason=ci.check_in_reason,
        patient_type='Check-in',
        checkin_id=ci.id,
        reception_status='Accepted',
        reception_notes=notes,
        accepted_by_reception_at=datetime.utcnow(),
        sent_to_doctor_at=datetime.utcnow(),
        doctor_status='Pending',
        arrival_time=datetime.utcnow()
    )
    db.session.add(entry)
    _record_visit(
        patient_id=ci.patient_id,
        visit_type='OP',
        doctor_id=ci.doctor_id,
        notes=f"Reception accepted check-in. Reason: {ci.check_in_reason or 'General consultation'}",
        visit_date=ci.created_at or datetime.utcnow(),
    )

    # Update check-in status
    ci.status = 'accepted'
    ci.acceptance_time = datetime.utcnow()
    db.session.commit()

    logger.info(f"Check-in #{checkin_id} accepted, Token #{token}")
    return jsonify({
        'success': True,
        'token': token,
        'message': f'Check-in accepted, Token #{token} assigned. Sent to doctor.'
    })


# â”€â”€â”€ Reject Appointment (Reception) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/reject-appointment', methods=['POST'])
@receptionist_only
def reject_appointment():
    """Reception rejects an appointment"""
    data = request.get_json()
    appointment_id = data.get('appointment_id')
    reason = data.get('reason', 'Rejected by reception')

    appt = Appointment.query.get(appointment_id)
    if not appt:
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404

    appt.status = 'cancelled'
    appt.notes = f'Rejected by reception: {reason}'
    db.session.commit()

    logger.info(f"Appointment #{appointment_id} rejected by reception")
    return jsonify({'success': True, 'message': 'Appointment rejected.'})


# â”€â”€â”€ Reject Check-in (Reception) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/reject-checkin', methods=['POST'])
@receptionist_only
def reject_checkin():
    """Reception rejects a check-in"""
    data = request.get_json()
    checkin_id = data.get('checkin_id')
    reason = data.get('reason', 'Rejected by reception')

    ci = PatientCheckIn.query.get(checkin_id)
    if not ci:
        return jsonify({'success': False, 'error': 'Check-in not found'}), 404

    ci.status = 'rejected'
    ci.doctor_notes = f'Rejected by reception: {reason}'
    db.session.commit()

    logger.info(f"Check-in #{checkin_id} rejected by reception")
    return jsonify({'success': True, 'message': 'Check-in rejected.'})


# â”€â”€â”€ Doctor Accepts Patient from Queue â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/doctor-accept', methods=['POST'])
@reception_access_required
def doctor_accept():
    """Doctor accepts a patient that was sent by reception"""
    data = request.get_json()
    entry_id = data.get('entry_id') or data.get('id') or data.get('queue_entry_id')
    patient_id = data.get('patient_id')
    notes = data.get('notes', '')

    entry = _resolve_queue_entry_for_doctor_action(entry_id=entry_id, patient_id=patient_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Queue entry not found'}), 404

    # Verify doctor
    if current_user.role == UserRole.DOCTOR:
        if not hasattr(current_user, 'doctor') or not current_user.doctor or entry.doctor_id != current_user.doctor.id:
            return jsonify({'success': False, 'error': 'Not your patient'}), 403

    entry.doctor_status = 'Accepted'
    entry.doctor_notes = notes
    entry.doctor_responded_at = datetime.utcnow()
    entry.status = 'Accepted by Doctor'
    entry.consultation_time = datetime.utcnow()
    db.session.commit()

    logger.info(f"Queue #{entry.id} accepted by doctor")
    return jsonify({'success': True, 'message': 'Patient accepted. Ready for consultation.'})


# â”€â”€â”€ Doctor Cancels/Rejects Patient â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/doctor-cancel', methods=['POST'])
@reception_access_required
def doctor_cancel():
    """Doctor cancels/rejects a patient that was sent by reception"""
    data = request.get_json()
    entry_id = data.get('entry_id') or data.get('id') or data.get('queue_entry_id')
    patient_id = data.get('patient_id')
    reason = data.get('reason', '')

    entry = _resolve_queue_entry_for_doctor_action(entry_id=entry_id, patient_id=patient_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Queue entry not found'}), 404

    if current_user.role == UserRole.DOCTOR:
        if not hasattr(current_user, 'doctor') or not current_user.doctor or entry.doctor_id != current_user.doctor.id:
            return jsonify({'success': False, 'error': 'Not your patient'}), 403

    entry.doctor_status = 'Cancelled'
    entry.doctor_notes = reason
    entry.doctor_responded_at = datetime.utcnow()
    entry.status = 'Rejected by Doctor'
    db.session.commit()

    logger.info(f"Queue #{entry.id} cancelled by doctor: {reason}")
    return jsonify({'success': True, 'message': 'Patient cancelled. Reception notified.'})


# â”€â”€â”€ Doctor Completes Consultation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/doctor-complete', methods=['POST'])
@reception_access_required
def doctor_complete():
    """Doctor marks consultation complete"""
    data = request.get_json()
    entry_id = data.get('entry_id')

    entry = ReceptionQueue.query.get(entry_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Queue entry not found'}), 404

    entry.doctor_status = 'Completed'
    entry.status = 'Completed'
    entry.completed_time = datetime.utcnow()
    db.session.commit()

    logger.info(f"Queue #{entry_id} completed")
    return jsonify({'success': True, 'message': 'Consultation completed.'})


# â”€â”€â”€ Search Patients (reception AJAX) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/search-patients')
@receptionist_only
def search_patients():
    """Search patients by UHID, name, or phone for reception lookup."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    from sqlalchemy import or_
    filters = []

    # UHID search (exact or prefix)
    if q.upper().startswith('CHN-') or q.upper().startswith('PAT-'):
        filters.append(Patient.uhid.ilike(f'{q}%'))
    else:
        # Name search
        filters.append(Patient.name.ilike(f'%{q}%'))
        filters.append(Patient.first_name.ilike(f'%{q}%'))
        filters.append(Patient.last_name.ilike(f'%{q}%'))
        # Phone search
        if q.replace(' ', '').replace('-', '').replace('+', '').isdigit():
            filters.append(Patient.phone.ilike(f'%{q}%'))

    patients = Patient.query.filter(or_(*filters)).limit(15).all()

    return jsonify([{
        'id': p.id,
        'name': p.full_name,
        'uhid': p.uhid,
        'age': p.age,
        'gender': p.gender,
        'phone': p.phone
    } for p in patients])


# â”€â”€â”€ Register Existing / Returning Patient â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/register-existing', methods=['POST'])
@receptionist_only
def register_existing():
    """Queue an existing/returning patient (no new record created)."""
    data = request.get_json()
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')
    reason = data.get('reason', 'Follow-up / General Consultation')

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404

    parsed_doctor_id = None
    if doctor_id:
        try:
            parsed_doctor_id = int(doctor_id)
            doc = Doctor.query.get(parsed_doctor_id)
            if not doc:
                parsed_doctor_id = None
        except (ValueError, TypeError):
            parsed_doctor_id = None

    try:
        token = _next_token()
        entry = ReceptionQueue(
            patient_id=patient.id,
            doctor_id=parsed_doctor_id,
            token_number=token,
            status='Accepted by Reception',
            visit_reason=reason,
            patient_type='Returning',
            reception_status='Accepted',
            accepted_by_reception_at=datetime.utcnow(),
            sent_to_doctor_at=datetime.utcnow() if parsed_doctor_id else None,
            doctor_status='Pending',
            arrival_time=datetime.utcnow()
        )
        db.session.add(entry)
        _record_visit(
            patient_id=patient.id,
            visit_type='OP',
            doctor_id=parsed_doctor_id,
            notes=f"Reception queued returning patient. Reason: {reason}",
        )
        db.session.commit()

        msg = f'Returning patient queued. Token #{token}'
        if patient.uhid:
            msg += f' | UHID: {patient.uhid}'
        if parsed_doctor_id:
            doc = Doctor.query.get(parsed_doctor_id)
            msg += f' â€” Sent to Dr. {doc.first_name} {doc.last_name}'

        return jsonify({
            'success': True,
            'token': token,
            'uhid': patient.uhid,
            'message': msg
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Register existing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# â”€â”€â”€ Register Walk-in Patient â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/register-walkin', methods=['POST'])
@receptionist_only
def register_walkin():
    """Register a walk-in patient and generate token.
    Uses PatientService â€” NO fake User accounts created.
    """
    from app.services.patient_service import PatientService
    from app.models.models import Hospital

    data = request.get_json()

    first_name = data.get('first_name', '').strip()
    last_name  = data.get('last_name', '').strip()
    phone      = data.get('phone', '').strip() or None
    age        = data.get('age')
    gender     = data.get('gender', 'Other')
    reason     = data.get('reason', 'General Consultation')
    doctor_id  = data.get('doctor_id')

    if not first_name:
        return jsonify({'success': False, 'error': 'First name is required'}), 400

    try:
        if phone and not PatientService.validate_phone(phone):
            return jsonify({'success': False, 'error': 'Invalid phone format'}), 400

        if age is not None and str(age).strip() != '':
            age_int = int(age)
            if age_int < 0 or age_int > 150:
                return jsonify({'success': False, 'error': 'Invalid age'}), 400
        else:
            age_int = 0

        # Robustly parse doctor_id
        parsed_doctor_id = None
        if doctor_id:
            try:
                parsed_doctor_id = int(doctor_id)
                doc = Doctor.query.get(parsed_doctor_id)
                if not doc:
                    parsed_doctor_id = None
            except (ValueError, TypeError):
                parsed_doctor_id = None

        # Check if patient already exists by phone (duplicate detection)
        patient = None
        if phone:
            patient = Patient.query.filter_by(phone=phone).first()

        # If no existing patient, use PatientService (UHID auto-generated, no User created)
        if not patient:
            hospital = Hospital.query.first()
            patient = PatientService.create_walk_in_patient(
                name=f"{first_name} {last_name}".strip(),
                age=age_int,
                gender=gender,
                phone=phone,
                hospital_id=hospital.id if hospital else None
            )
            if not patient:
                return jsonify({'success': False, 'error': 'Failed to create patient record'}), 500

        token = _next_token()
        entry = ReceptionQueue(
            patient_id=patient.id,
            doctor_id=parsed_doctor_id,
            token_number=token,
            status='Accepted by Reception',
            visit_reason=reason,
            patient_type='Walk-in',
            reception_status='Accepted',
            accepted_by_reception_at=datetime.utcnow(),
            sent_to_doctor_at=datetime.utcnow() if parsed_doctor_id else None,
            doctor_status='Pending',
            arrival_time=datetime.utcnow()
        )
        db.session.add(entry)
        _record_visit(
            patient_id=patient.id,
            visit_type='OP',
            doctor_id=parsed_doctor_id,
            notes=f"Reception registered walk-in. Reason: {reason}",
        )
        db.session.commit()

        msg = f'Walk-in registered. Token #{token}'
        if patient.uhid:
            msg += f' | UHID: {patient.uhid}'
        if parsed_doctor_id:
            doc = Doctor.query.get(parsed_doctor_id)
            msg += f' â€” Sent to Dr. {doc.first_name} {doc.last_name}'
        else:
            msg += ' â€” No doctor assigned yet. Assign from the queue.'

        return jsonify({
            'success': True,
            'token': token,
            'uhid': patient.uhid,
            'patient_name': f"{first_name} {last_name}",
            'message': msg
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Walk-in registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# â”€â”€â”€ Lab-only walk-in (independent lab; no doctor referral) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/lab-only-visit', methods=['POST'])
@receptionist_only
def lab_only_visit():
    """
    Register or resolve patient and create walk-in lab orders (doctor_id NULL).
    Uses PatientService â€” NO fake User accounts created.
    JSON: { patient_id?, first_name?, last_name?, phone?, age?, gender?, tests: [str, ...] }
    """
    from app.models.models import Hospital
    from app.routes.lab import _create_lab_order_row, SOURCE_WALK_IN
    from app.services.patient_service import PatientService

    data = request.get_json() or {}
    tests = [str(t).strip() for t in (data.get('tests') or []) if str(t).strip()]
    if not tests:
        return jsonify({'success': False, 'error': 'Select at least one laboratory test'}), 400

    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id) if patient_id else None

    if not patient:
        first_name = (data.get('first_name') or '').strip()
        if not first_name:
            return jsonify({'success': False, 'error': 'First name or existing patient_id required'}), 400
        last_name = (data.get('last_name') or '').strip()
        phone = (data.get('phone') or '').strip() or None
        age = data.get('age')
        gender = (data.get('gender') or 'Other').strip()

        if phone and not PatientService.validate_phone(phone):
            return jsonify({'success': False, 'error': 'Invalid phone format'}), 400

        # Check for existing patient by phone
        if phone:
            patient = Patient.query.filter_by(phone=phone).first()

        # Create via PatientService (no fake User account)
        if not patient:
            hospital = Hospital.query.first()
            patient = PatientService.create_walk_in_patient(
                name=f"{first_name} {last_name}".strip(),
                age=int(age) if str(age).isdigit() else 0,
                gender=gender,
                phone=phone,
                hospital_id=hospital.id if hospital else None
            )
            if not patient:
                return jsonify({'success': False, 'error': 'Failed to create patient record'}), 500

    order_ids = []
    try:
        for test_name in tests:
            order = _create_lab_order_row(patient.id, test_name, SOURCE_WALK_IN, None)
            order_ids.append(order.id)
        _record_visit(
            patient_id=patient.id,
            visit_type='LAB',
            notes=f"Lab-only walk-in created for tests: {', '.join(tests)}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception('lab_only_visit')
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({
        'success': True,
        'patient_id': patient.id,
        'uhid': patient.uhid,
        'order_ids': order_ids,
        'message': f'{len(order_ids)} lab order(s) created for {patient.full_name} ({patient.uhid}). Patient may proceed to sample collection.',
    })


# â”€â”€â”€ Update Queue Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/update-status', methods=['POST'])
@reception_access_required
def update_status():
    """Update queue entry status"""
    data = request.get_json()
    entry_id = data.get('entry_id')
    new_status = data.get('status')

    entry = ReceptionQueue.query.get(entry_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Queue entry not found'}), 404

    entry.status = new_status
    if new_status == 'In Consultation':
        entry.consultation_time = datetime.utcnow()
    elif new_status == 'Completed':
        entry.completed_time = datetime.utcnow()
        entry.doctor_status = 'Completed'

    db.session.commit()
    logger.info(f"Queue #{entry_id} â†’ {new_status}")
    return jsonify({'success': True})


# â”€â”€â”€ Assign Doctor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/assign-doctor', methods=['POST'])
@receptionist_only
def assign_doctor():
    """Assign a doctor to a queue entry"""
    data = request.get_json()
    entry_id = data.get('entry_id')
    doctor_id = data.get('doctor_id')

    entry = ReceptionQueue.query.get(entry_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Queue entry not found'}), 404

    entry.doctor_id = int(doctor_id)
    entry.sent_to_doctor_at = datetime.utcnow()
    entry.doctor_status = 'Pending'
    db.session.commit()

    doctor = Doctor.query.get(int(doctor_id))
    doc_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor"
    logger.info(f"Queue #{entry_id} assigned to {doc_name}")
    return jsonify({'success': True, 'message': f'Assigned to {doc_name}'})


# â”€â”€â”€ Doctor's Incoming Patients (API) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/api/doctor-queue')
@reception_access_required
def doctor_queue_api():
    """Get patients sent to the current doctor by reception"""
    if current_user.role != UserRole.DOCTOR or not hasattr(current_user, 'doctor') or not current_user.doctor:
        return jsonify({'success': False, 'error': 'Doctor only'}), 403

    today_start = datetime.combine(date.today(), datetime.min.time())
    entries = ReceptionQueue.query.filter(
        ReceptionQueue.doctor_id == current_user.doctor.id,
        ReceptionQueue.reception_status == 'Accepted',
        ReceptionQueue.created_at >= today_start
    ).order_by(ReceptionQueue.token_number.asc()).all()

    result = []
    for e in entries:
        patient = e.patient
        result.append({
            'id': e.id,
            'token': e.token_number,
            'patient_name': f"{patient.first_name} {patient.last_name}" if patient else 'Unknown',
            'patient_type': e.patient_type,
            'visit_reason': e.visit_reason or 'N/A',
            'arrival_time': e.arrival_time.strftime('%I:%M %p') if e.arrival_time else '',
            'doctor_status': e.doctor_status,
            'status': e.status
        })

    return jsonify({'success': True, 'queue': result})



# â”€â”€â”€ Queue Display (Public-ish â€” token board) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@reception_bp.route('/queue-display')
def queue_display():
    """Large-screen queue display for waiting area"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    queue = ReceptionQueue.query.filter(
        ReceptionQueue.created_at >= today_start,
        ReceptionQueue.reception_status == 'Accepted'
    ).order_by(ReceptionQueue.token_number.asc()).all()

    doctors = Doctor.query.filter_by(verified=True, is_suspended=False, is_deleted=False).all()

    return render_template('reception/queue_display.html',
                           queue=queue, doctors=doctors)
