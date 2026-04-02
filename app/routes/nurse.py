"""
Nurse Portal — Complete hospital nurse workflow module.
Dashboard, patients, vitals, tasks, notes, lab coordination,
medication administration, and shift handover.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (
    db, Nurse, NurseTask, NurseNote, Patient, PatientVitals, UserRole,
    Prescription, PrescriptionMedicine, LabOrder, Bed,
    MedicationAdministration, NurseHandover, Appointment, PatientCheckIn,
    NursePatientAssignment
)
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, or_, and_, desc

nurse_bp = Blueprint('nurse', __name__, url_prefix='/nurse')


# ─── Access Decorator ───────────────────────────────────────────
def nurse_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access the Nurse Portal.', 'danger')
            return redirect(url_for('auth.staff_login', role='NURSE'))
        if current_user.role not in (UserRole.NURSE, UserRole.HOST, UserRole.ADMIN):
            flash('Access denied. Nurse credentials required.', 'danger')
            return redirect(url_for('auth.choose_login'))
        return f(*args, **kwargs)
    return decorated


def _get_nurse():
    return Nurse.query.filter_by(user_id=current_user.id).first()


def _my_claimed_patient_ids():
    """Get patient IDs claimed by the current nurse (active assignments)."""
    return db.session.query(NursePatientAssignment.patient_id).filter(
        NursePatientAssignment.nurse_id == current_user.id,
        NursePatientAssignment.is_active == True
    ).subquery()


def _all_claimed_patient_ids():
    """Get patient IDs claimed by ANY nurse (active assignments)."""
    return db.session.query(NursePatientAssignment.patient_id).filter(
        NursePatientAssignment.is_active == True
    ).subquery()


def _my_patients_query():
    """Get only patients claimed by the current nurse."""
    my_ids = _my_claimed_patient_ids()
    return Patient.query.filter(Patient.id.in_(my_ids))


def _all_patients_today():
    """Get ALL patients relevant for today: registered, OP, walk-ins, appointments, check-ins.
    Shows everyone who visited today plus all admitted/active patients."""
    today = datetime.now().date()

    # Patients with appointments today
    appt_today = db.session.query(Appointment.patient_id).filter(
        func.date(Appointment.appointment_date) == today,
        Appointment.status.in_(['pending', 'confirmed', 'completed'])
    ).distinct().subquery()

    # Patients who checked in today
    checkin_today = db.session.query(PatientCheckIn.patient_id).filter(
        func.date(PatientCheckIn.created_at) == today
    ).distinct().subquery()

    # Patients in occupied beds (admitted/IP)
    in_bed = db.session.query(Bed.patient_id).filter(
        Bed.is_occupied == True,
        Bed.patient_id.isnot(None)
    ).subquery()

    # Patients with vitals recorded today (already being monitored)
    vitals_today = db.session.query(PatientVitals.patient_id).filter(
        func.date(PatientVitals.recorded_at) == today
    ).distinct().subquery()

    # Patients registered today (new registrations / walk-ins)
    registered_today = db.session.query(Patient.id).filter(
        func.date(Patient.created_at) == today
    ).subquery()

    # Patients with active tasks
    active_tasks = db.session.query(NurseTask.patient_id).filter(
        NurseTask.status.in_(['Pending', 'In Progress'])
    ).distinct().subquery()

    return Patient.query.filter(
        or_(
            Patient.id.in_(appt_today),
            Patient.id.in_(checkin_today),
            Patient.id.in_(in_bed),
            Patient.id.in_(vitals_today),
            Patient.id.in_(registered_today),
            Patient.id.in_(active_tasks),
        )
    ).order_by(Patient.first_name.asc())


# ═══════════════════════════════════════════════════════════════
# 1. DASHBOARD
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/')
@nurse_bp.route('/dashboard')
@login_required
@nurse_access_required
def dashboard():
    nurse = _get_nurse()
    today = datetime.now().date()

    # Task counts
    base_tasks = NurseTask.query.filter(
        or_(
            NurseTask.assigned_nurse_id == current_user.id,
            NurseTask.assigned_nurse_id.is_(None)
        )
    )
    pending_count = base_tasks.filter(NurseTask.status == 'Pending').count()
    in_progress_count = base_tasks.filter(NurseTask.status == 'In Progress').count()

    completed_today = base_tasks.filter(
        NurseTask.status == 'Completed',
        func.date(NurseTask.completed_at) == today
    ).count()

    urgent_count = base_tasks.filter(
        NurseTask.status.in_(['Pending', 'In Progress']),
        NurseTask.priority == 'urgent'
    ).count()

    # Patient counts
    assigned_patients = _my_patients_query().all()
    assigned_count = len(assigned_patients)

    # Available pool count (unclaimed)
    all_claimed = _all_claimed_patient_ids()
    available_count = _all_patients_today().filter(
        ~Patient.id.in_(all_claimed)
    ).count()
    if available_count == 0:
        available_count = Patient.query.filter(
            ~Patient.id.in_(all_claimed)
        ).count()

    # Vitals recorded today
    vitals_today = PatientVitals.query.filter(
        PatientVitals.nurse_id == current_user.id,
        func.date(PatientVitals.recorded_at) == today
    ).count()

    # Medications due
    meds_due = MedicationAdministration.query.filter(
        MedicationAdministration.administration_status == 'Pending'
    ).count()

    # Lab samples pending
    patient_ids = [p.id for p in assigned_patients]
    lab_pending = 0
    if patient_ids:
        lab_pending = LabOrder.query.filter(
            LabOrder.patient_id.in_(patient_ids),
            LabOrder.status.in_(['CREATED', 'PENDING'])
        ).count()

    # Critical alerts from recent vitals
    critical_alerts = []
    if patient_ids:
        recent_vitals = PatientVitals.query.filter(
            PatientVitals.patient_id.in_(patient_ids),
            func.date(PatientVitals.recorded_at) == today
        ).all()
        for v in recent_vitals:
            for alert_type in (v.has_alerts or []):
                critical_alerts.append({
                    'patient': v.patient,
                    'type': alert_type,
                    'vitals': v,
                })

    # Pending tasks list (top 10)
    pending_tasks = (
        base_tasks
        .filter(NurseTask.status.in_(['Pending', 'In Progress']))
        .order_by(
            db.case(
                (NurseTask.priority == 'urgent', 0),
                (NurseTask.priority == 'high', 1),
                (NurseTask.priority == 'normal', 2),
                else_=3
            ),
            db.case((NurseTask.due_date.is_(None), 1), else_=0),
            NurseTask.due_date.asc(),
            NurseTask.created_at.desc()
        )
        .limit(10)
        .all()
    )

    # Recent activity
    recent_vitals_log = PatientVitals.query.filter(
        PatientVitals.nurse_id == current_user.id
    ).order_by(PatientVitals.recorded_at.desc()).limit(5).all()

    recent_notes = NurseNote.query.filter(
        NurseNote.nurse_id == current_user.id
    ).order_by(NurseNote.created_at.desc()).limit(5).all()

    recent_completed = (
        NurseTask.query
        .filter(
            NurseTask.completed_by_id == current_user.id,
            NurseTask.status == 'Completed'
        )
        .order_by(NurseTask.completed_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'nurse/dashboard.html',
        nurse=nurse,
        assigned_count=assigned_count,
        available_count=available_count,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_today=completed_today,
        urgent_count=urgent_count,
        vitals_today=vitals_today,
        meds_due=meds_due,
        lab_pending=lab_pending,
        critical_alerts=critical_alerts,
        assigned_patients=assigned_patients[:10],
        pending_tasks=pending_tasks,
        recent_vitals_log=recent_vitals_log,
        recent_notes=recent_notes,
        recent_completed=recent_completed,
    )


# ═══════════════════════════════════════════════════════════════
# 2. ASSIGNED PATIENTS + AVAILABLE POOL
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/patients')
@login_required
@nurse_access_required
def patients():
    nurse = _get_nurse()
    search = request.args.get('search', '').strip()
    tab = request.args.get('tab', 'my')  # 'my' or 'available'

    # My claimed patients
    my_query = _my_patients_query()
    if search and tab == 'my':
        my_query = my_query.filter(
            or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.name.ilike(f'%{search}%'),
                Patient.uhid.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%'),
            )
        )
    my_patients = my_query.order_by(Patient.created_at.desc()).all()

    # Available patients pool: today's patients NOT claimed by any nurse
    all_claimed = _all_claimed_patient_ids()
    available_query = _all_patients_today().filter(
        ~Patient.id.in_(all_claimed)
    )
    if search and tab == 'available':
        available_query = available_query.filter(
            or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.name.ilike(f'%{search}%'),
                Patient.uhid.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%'),
            )
        )
    available_patients = available_query.all()

    # If no patients in today's pool, show all unclaimed patients
    if not available_patients and not search:
        available_patients = Patient.query.filter(
            ~Patient.id.in_(all_claimed)
        ).order_by(Patient.first_name.asc()).limit(50).all()

    # Attach bed info
    beds = {b.patient_id: b for b in Bed.query.filter(
        Bed.is_occupied == True,
        Bed.patient_id.isnot(None)
    ).all()}

    return render_template(
        'nurse/patients.html',
        nurse=nurse,
        my_patients=my_patients,
        available_patients=available_patients,
        beds=beds,
        search=search,
        tab=tab,
    )


@nurse_bp.route('/patient/claim/<int:patient_id>', methods=['POST'])
@login_required
@nurse_access_required
def claim_patient(patient_id):
    """Nurse claims a patient — removes from other nurses' available pool."""
    patient = Patient.query.get_or_404(patient_id)

    # Check if already claimed by someone
    existing = NursePatientAssignment.query.filter_by(
        patient_id=patient_id, is_active=True
    ).first()
    if existing:
        if existing.nurse_id == current_user.id:
            flash('This patient is already assigned to you.', 'info')
        else:
            flash('This patient has already been taken by another nurse.', 'warning')
        return redirect(url_for('nurse.patients', tab='available'))

    assignment = NursePatientAssignment(
        nurse_id=current_user.id,
        patient_id=patient_id,
    )
    db.session.add(assignment)
    db.session.commit()
    flash(f'Patient {patient.first_name} {patient.last_name} assigned to you.', 'success')
    return redirect(url_for('nurse.patients', tab='my'))


@nurse_bp.route('/patient/release/<int:patient_id>', methods=['POST'])
@login_required
@nurse_access_required
def release_patient(patient_id):
    """Nurse releases a patient — returns to available pool."""
    assignment = NursePatientAssignment.query.filter_by(
        nurse_id=current_user.id,
        patient_id=patient_id,
        is_active=True
    ).first()
    if assignment:
        assignment.is_active = False
        assignment.released_at = datetime.now()
        db.session.commit()
        flash('Patient released back to available pool.', 'success')
    else:
        flash('Assignment not found.', 'danger')
    return redirect(url_for('nurse.patients', tab='my'))


# ═══════════════════════════════════════════════════════════════
# 3. PATIENT DETAIL
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/patient/<int:patient_id>')
@login_required
@nurse_access_required
def patient_detail(patient_id):
    nurse = _get_nurse()
    patient = Patient.query.get_or_404(patient_id)

    bed = Bed.query.filter_by(patient_id=patient_id, is_occupied=True).first()

    # Latest vitals
    latest_vitals = PatientVitals.query.filter_by(
        patient_id=patient_id
    ).order_by(PatientVitals.recorded_at.desc()).first()

    vitals_history = PatientVitals.query.filter_by(
        patient_id=patient_id
    ).order_by(PatientVitals.recorded_at.desc()).limit(10).all()

    # Doctor tasks
    tasks = NurseTask.query.filter_by(
        patient_id=patient_id
    ).order_by(
        db.case(
            (NurseTask.status == 'Pending', 0),
            (NurseTask.status == 'In Progress', 1),
            else_=2
        ),
        NurseTask.created_at.desc()
    ).limit(20).all()

    # Nurse notes
    notes = NurseNote.query.filter_by(
        patient_id=patient_id
    ).order_by(NurseNote.created_at.desc()).limit(20).all()

    # Lab orders
    lab_orders = LabOrder.query.filter_by(
        patient_id=patient_id
    ).order_by(LabOrder.created_at.desc()).limit(10).all()

    # Prescriptions + medications
    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id
    ).order_by(Prescription.prescribed_at.desc()).limit(5).all()

    med_records = MedicationAdministration.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicationAdministration.created_at.desc()).limit(20).all()

    # Handovers
    handovers = NurseHandover.query.filter_by(
        patient_id=patient_id
    ).order_by(NurseHandover.created_at.desc()).limit(5).all()

    return render_template(
        'nurse/patient_detail.html',
        nurse=nurse,
        patient=patient,
        bed=bed,
        latest_vitals=latest_vitals,
        vitals_history=vitals_history,
        tasks=tasks,
        notes=notes,
        lab_orders=lab_orders,
        prescriptions=prescriptions,
        med_records=med_records,
        handovers=handovers,
    )


# ═══════════════════════════════════════════════════════════════
# 4. VITALS
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/api/search-patients')
@login_required
@nurse_access_required
def api_search_patients():
    """Search ALL patients by name, UHID, or phone."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Patient.query.filter(
        or_(
            Patient.first_name.ilike(f'%{q}%'),
            Patient.last_name.ilike(f'%{q}%'),
            Patient.name.ilike(f'%{q}%'),
            Patient.uhid.ilike(f'%{q}%'),
            Patient.phone.ilike(f'%{q}%'),
        )
    ).order_by(Patient.first_name.asc()).limit(20).all()
    return jsonify([
        {'id': p.id, 'name': f'{p.first_name} {p.last_name}', 'uhid': p.uhid or ''}
        for p in results
    ])


@nurse_bp.route('/vitals')
@login_required
@nurse_access_required
def vitals():
    nurse = _get_nurse()
    patient_id = request.args.get('patient_id', type=int)

    # Show today's patients; if none, show all patients
    patients_list = _all_patients_today().all()
    if not patients_list:
        patients_list = Patient.query.order_by(Patient.first_name.asc()).limit(100).all()

    vitals_list = []
    selected_patient = None
    if patient_id:
        selected_patient = Patient.query.get(patient_id)
        vitals_list = PatientVitals.query.filter_by(
            patient_id=patient_id
        ).order_by(PatientVitals.recorded_at.desc()).limit(30).all()

    return render_template(
        'nurse/vitals.html',
        nurse=nurse,
        patients=patients_list,
        vitals_list=vitals_list,
        selected_patient=selected_patient,
        patient_id=patient_id,
    )


@nurse_bp.route('/vitals/add', methods=['POST'])
@login_required
@nurse_access_required
def vitals_add():
    data = request.form if request.form else request.get_json(silent=True) or {}

    patient_id = data.get('patient_id', type=int) if hasattr(data, 'get') else data.get('patient_id')
    if not patient_id:
        flash('Please select a patient.', 'danger')
        return redirect(url_for('nurse.vitals'))

    try:
        v = PatientVitals(
            patient_id=int(patient_id),
            nurse_id=current_user.id,
            temperature=float(data.get('temperature', 0)),
            systolic_bp=int(data.get('systolic_bp', 0)),
            diastolic_bp=int(data.get('diastolic_bp', 0)),
            heart_rate=int(data.get('heart_rate', 0)),
            oxygen_level=float(data.get('oxygen_level', 0)),
            respiratory_rate=int(data.get('respiratory_rate', 0)) if data.get('respiratory_rate') else None,
            blood_sugar=float(data.get('blood_sugar')) if data.get('blood_sugar') else None,
            notes=data.get('notes', '').strip() or None,
            recorded_at=datetime.now(),
        )
        db.session.add(v)
        db.session.commit()

        alerts = v.has_alerts
        if alerts:
            flash(f'Vitals recorded with alerts: {", ".join(alerts)}', 'warning')
        else:
            flash('Vitals recorded successfully.', 'success')
    except (ValueError, TypeError) as e:
        flash(f'Invalid vitals data: {e}', 'danger')

    return redirect(url_for('nurse.vitals', patient_id=patient_id))


# ═══════════════════════════════════════════════════════════════
# 5. TASKS / DOCTOR INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/tasks')
@login_required
@nurse_access_required
def tasks():
    nurse = _get_nurse()
    status_filter = request.args.get('status', 'active')

    query = NurseTask.query.filter(
        or_(
            NurseTask.assigned_nurse_id == current_user.id,
            NurseTask.assigned_nurse_id.is_(None)
        )
    )

    if status_filter == 'active':
        query = query.filter(NurseTask.status.in_(['Pending', 'In Progress']))
    elif status_filter == 'completed':
        query = query.filter(NurseTask.status == 'Completed')
    elif status_filter == 'cancelled':
        query = query.filter(NurseTask.status == 'Cancelled')

    tasks_list = query.order_by(
        db.case(
            (NurseTask.priority == 'urgent', 0),
            (NurseTask.priority == 'high', 1),
            (NurseTask.priority == 'normal', 2),
            else_=3
        ),
        db.case((NurseTask.due_date.is_(None), 1), else_=0),
        NurseTask.due_date.asc(),
        NurseTask.created_at.desc()
    ).all()

    return render_template(
        'nurse/tasks.html',
        nurse=nurse,
        tasks=tasks_list,
        status_filter=status_filter,
    )


@nurse_bp.route('/task/complete/<int:task_id>', methods=['POST'])
@login_required
@nurse_access_required
def complete_task(task_id):
    task = NurseTask.query.get_or_404(task_id)
    notes = request.form.get('completion_notes', '').strip()
    new_status = request.form.get('status', 'Completed')

    if new_status in ('Pending', 'In Progress', 'Completed', 'Cancelled'):
        task.status = new_status
        if new_status == 'Completed':
            task.is_completed = True
            task.completed_at = datetime.now()
            task.completed_by_id = current_user.id
        if notes:
            task.completion_notes = notes
        task.updated_at = datetime.now()
        db.session.commit()
        flash(f'Task marked as {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')

    redirect_to = request.form.get('redirect_to', '')
    if redirect_to:
        return redirect(redirect_to)
    return redirect(url_for('nurse.tasks'))


# Keep old route for backward compat
@nurse_bp.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
@nurse_access_required
def update_task(task_id):
    return complete_task(task_id)


# ═══════════════════════════════════════════════════════════════
# 6. NURSE NOTES
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/notes')
@login_required
@nurse_access_required
def notes():
    nurse = _get_nurse()
    patient_id = request.args.get('patient_id', type=int)
    patients_list = _all_patients_today().all()

    query = NurseNote.query.filter(NurseNote.nurse_id == current_user.id)
    if patient_id:
        query = query.filter(NurseNote.patient_id == patient_id)

    notes_list = query.order_by(NurseNote.created_at.desc()).limit(50).all()

    return render_template(
        'nurse/notes.html',
        nurse=nurse,
        notes=notes_list,
        patients=patients_list,
        patient_id=patient_id,
    )


@nurse_bp.route('/notes/add', methods=['POST'])
@login_required
@nurse_access_required
def add_note():
    data = request.form if request.form else request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    content = data.get('content', '').strip()
    note_type = data.get('note_type', 'general')
    is_critical = data.get('is_critical') in ('true', 'True', True, '1', 'on')

    if not patient_id or not content:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Patient and content required'}), 400
        flash('Patient and content are required.', 'danger')
        return redirect(url_for('nurse.notes'))

    note = NurseNote(
        patient_id=int(patient_id),
        nurse_id=current_user.id,
        note_type=note_type,
        content=content,
        is_critical=is_critical,
    )
    db.session.add(note)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Note added'})
    flash('Nursing note added.', 'success')

    redirect_to = request.form.get('redirect_to', '')
    if redirect_to:
        return redirect(redirect_to)
    return redirect(url_for('nurse.notes', patient_id=patient_id))


# ═══════════════════════════════════════════════════════════════
# 7. LAB COORDINATION
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/lab')
@login_required
@nurse_access_required
def lab():
    nurse = _get_nurse()
    patient_ids = [p.id for p in _my_patients_query().all()]

    lab_orders = []
    if patient_ids:
        lab_orders = LabOrder.query.filter(
            LabOrder.patient_id.in_(patient_ids)
        ).order_by(LabOrder.created_at.desc()).limit(50).all()

    return render_template(
        'nurse/lab.html',
        nurse=nurse,
        lab_orders=lab_orders,
    )


# ═══════════════════════════════════════════════════════════════
# 8. MEDICATION ADMINISTRATION
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/medications')
@login_required
@nurse_access_required
def medications():
    nurse = _get_nurse()
    patient_ids = [p.id for p in _my_patients_query().all()]

    med_records = []
    if patient_ids:
        med_records = MedicationAdministration.query.filter(
            MedicationAdministration.patient_id.in_(patient_ids)
        ).order_by(
            db.case(
                (MedicationAdministration.administration_status == 'Pending', 0),
                (MedicationAdministration.administration_status == 'Delayed', 1),
                (MedicationAdministration.administration_status == 'Missed', 2),
                else_=3
            ),
            MedicationAdministration.created_at.desc()
        ).limit(50).all()

    return render_template(
        'nurse/medications.html',
        nurse=nurse,
        med_records=med_records,
    )


@nurse_bp.route('/medication/update', methods=['POST'])
@login_required
@nurse_access_required
def medication_update():
    med_id = request.form.get('med_id', type=int)
    status = request.form.get('status', '')
    remarks = request.form.get('remarks', '').strip()

    if not med_id or status not in ('Given', 'Missed', 'Delayed'):
        flash('Invalid medication update.', 'danger')
        return redirect(url_for('nurse.medications'))

    record = MedicationAdministration.query.get_or_404(med_id)
    record.administration_status = status
    record.administered_by_nurse_id = current_user.id
    if status == 'Given':
        record.administration_time = datetime.now()
    if remarks:
        record.remarks = remarks
    db.session.commit()

    flash(f'Medication marked as {status}.', 'success')
    return redirect(url_for('nurse.medications'))


# ═══════════════════════════════════════════════════════════════
# 9. SHIFT HANDOVER
# ═══════════════════════════════════════════════════════════════
@nurse_bp.route('/handover')
@login_required
@nurse_access_required
def handover():
    nurse = _get_nurse()
    patients_list = _all_patients_today().all()

    # Recent handovers by this nurse
    handovers = NurseHandover.query.filter(
        or_(
            NurseHandover.from_nurse_id == current_user.id,
            NurseHandover.to_nurse_id == current_user.id,
        )
    ).order_by(NurseHandover.created_at.desc()).limit(20).all()

    return render_template(
        'nurse/handover.html',
        nurse=nurse,
        patients=patients_list,
        handovers=handovers,
    )


@nurse_bp.route('/handover/save', methods=['POST'])
@login_required
@nurse_access_required
def handover_save():
    patient_id = request.form.get('patient_id', type=int)
    summary = request.form.get('summary', '').strip()
    pending = request.form.get('pending_tasks', '').strip()
    urgent = request.form.get('urgent_concerns', '').strip()

    if not patient_id or not summary:
        flash('Patient and summary are required.', 'danger')
        return redirect(url_for('nurse.handover'))

    h = NurseHandover(
        patient_id=patient_id,
        from_nurse_id=current_user.id,
        to_nurse_id=None,
        summary=summary,
        pending_tasks=pending or None,
        urgent_concerns=urgent or None,
    )
    db.session.add(h)
    db.session.commit()

    flash('Handover note saved.', 'success')
    return redirect(url_for('nurse.handover'))
