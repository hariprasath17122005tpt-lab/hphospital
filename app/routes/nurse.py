"""
Nurse Portal — dashboard, tasks, and patient notes.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (
    db, Nurse, NurseTask, NurseNote, Patient, UserRole
)
from functools import wraps
from datetime import datetime

nurse_bp = Blueprint('nurse', __name__, url_prefix='/nurse')


def nurse_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access the Nurse Portal.', 'danger')
            return redirect(url_for('auth.nurse_login'))
        if current_user.role not in (UserRole.NURSE, UserRole.HOST, UserRole.ADMIN):
            flash('Access denied. Nurse credentials required.', 'danger')
            return redirect(url_for('auth.choose_login'))
        return f(*args, **kwargs)
    return decorated


@nurse_bp.route('/')
@nurse_bp.route('/dashboard')
@login_required
@nurse_access_required
def dashboard():
    """Nurse dashboard — tasks overview and patient list."""
    nurse = Nurse.query.filter_by(user_id=current_user.id).first()

    # Task stats
    all_tasks = NurseTask.query
    if nurse:
        all_tasks = all_tasks.filter(
            db.or_(
                NurseTask.assigned_nurse_id == current_user.id,
                NurseTask.assigned_nurse_id.is_(None)
            )
        )

    pending_tasks = all_tasks.filter(NurseTask.status == 'Pending').all()
    in_progress_tasks = all_tasks.filter(NurseTask.status == 'In Progress').all()
    completed_today = all_tasks.filter(
        NurseTask.status == 'Completed',
        db.func.date(NurseTask.completed_at) == datetime.utcnow().date()
    ).all()

    urgent_tasks = [t for t in pending_tasks if t.priority == 'urgent']

    # Recent patients with tasks
    recent_tasks = (
        NurseTask.query
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
        .limit(20)
        .all()
    )

    return render_template(
        'nurse/dashboard.html',
        nurse=nurse,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_today=completed_today,
        urgent_tasks=urgent_tasks,
        recent_tasks=recent_tasks,
    )


@nurse_bp.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
@nurse_access_required
def update_task(task_id):
    """Update a nurse task status."""
    task = NurseTask.query.get_or_404(task_id)
    new_status = request.form.get('status') or request.json.get('status')
    notes = request.form.get('notes') or request.json.get('notes', '')

    if new_status in ('Pending', 'In Progress', 'Completed', 'Cancelled'):
        task.status = new_status
        if new_status == 'Completed':
            task.is_completed = True
            task.completed_at = datetime.utcnow()
            task.completed_by_id = current_user.id
        if notes:
            task.completion_notes = notes
        task.updated_at = datetime.utcnow()
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': f'Task updated to {new_status}'})
        flash(f'Task updated to {new_status}', 'success')
    else:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        flash('Invalid status', 'danger')

    return redirect(url_for('nurse.dashboard'))


@nurse_bp.route('/notes/add', methods=['POST'])
@login_required
@nurse_access_required
def add_note():
    """Add a nursing note for a patient."""
    data = request.form if request.form else request.get_json()
    patient_id = data.get('patient_id')
    content = data.get('content', '').strip()
    note_type = data.get('note_type', 'general')
    is_critical = data.get('is_critical') in ('true', 'True', True, '1')

    if not patient_id or not content:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Patient and content required'}), 400
        flash('Patient and content are required.', 'danger')
        return redirect(url_for('nurse.dashboard'))

    note = NurseNote(
        patient_id=patient_id,
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
    return redirect(url_for('nurse.dashboard'))
