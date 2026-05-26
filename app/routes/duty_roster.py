"""
Duty Roster / Staff Scheduling — Weekly calendar with shift assignments.
Supports Morning / Afternoon / Night shifts across multiple wards.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import db, User, UserRole, DutyRoster
from functools import wraps
from datetime import datetime, date, timedelta

duty_roster_bp = Blueprint('duty_roster', __name__, url_prefix='/duty-roster')

SHIFTS = ['Morning', 'Afternoon', 'Night']
WARDS = ['General', 'ICU', 'Emergency', 'OPD', 'Pharmacy', 'Lab']
STAFF_ROLES = ['Doctor', 'Nurse', 'Lab', 'Pharmacy', 'Reception']


# ─── Access Decorator ───────────────────────────────────────────
def roster_access_required(f):
    """Allow HOST, ADMIN, DOCTOR roles only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access the Duty Roster.', 'danger')
            return redirect(url_for('auth.staff_login'))
        allowed = (UserRole.HOST, UserRole.ADMIN, UserRole.DOCTOR)
        if current_user.role not in allowed:
            flash('Access denied. Duty Roster requires Host, Admin, or Doctor credentials.', 'danger')
            return redirect(url_for('auth.choose_login'))
        return f(*args, **kwargs)
    return decorated


# ─── Helpers ────────────────────────────────────────────────────
def _get_week_bounds(ref_date=None):
    """Return (monday, sunday) of the week containing ref_date."""
    if ref_date is None:
        ref_date = date.today()
    monday = ref_date - timedelta(days=ref_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _roster_to_dict(r):
    return {
        'id': r.id,
        'staff_id': r.staff_id,
        'staff_name': r.staff_name,
        'staff_role': r.staff_role,
        'shift': r.shift,
        'duty_date': r.duty_date.isoformat(),
        'ward': r.ward,
        'notes': r.notes or '',
    }


# ─── Dashboard ──────────────────────────────────────────────────
@duty_roster_bp.route('/')
@login_required
@roster_access_required
def dashboard():
    """Weekly roster calendar view."""
    # Determine which week to show
    week_offset = request.args.get('week', 0, type=int)
    today = date.today()
    ref = today + timedelta(weeks=week_offset)
    monday, sunday = _get_week_bounds(ref)

    # Filter params
    filter_ward = request.args.get('ward', '')
    filter_role = request.args.get('role', '')

    query = DutyRoster.query.filter(
        DutyRoster.duty_date >= monday,
        DutyRoster.duty_date <= sunday,
    )
    if filter_ward:
        query = query.filter(DutyRoster.ward == filter_ward)
    if filter_role:
        query = query.filter(DutyRoster.staff_role == filter_role)

    entries = query.order_by(DutyRoster.duty_date, DutyRoster.shift).all()

    # Build a grid: shift -> day_index -> [entries]
    days = [(monday + timedelta(days=i)) for i in range(7)]
    day_labels = [d.strftime('%a %d %b') for d in days]

    grid = {}
    for shift in SHIFTS:
        grid[shift] = {}
        for i, d in enumerate(days):
            grid[shift][i] = []

    for entry in entries:
        day_idx = (entry.duty_date - monday).days
        if 0 <= day_idx <= 6 and entry.shift in SHIFTS:
            grid[entry.shift][day_idx].append(entry)

    # Staff list for the assignment form
    staff_users = User.query.filter(
        User.role.in_([UserRole.DOCTOR, UserRole.NURSE, UserRole.LAB_STAFF,
                        UserRole.PHARMACIST, UserRole.RECEPTIONIST]),
        User.is_active == True,
    ).order_by(User.username).all()

    return render_template(
        'duty_roster/dashboard.html',
        grid=grid,
        shifts=SHIFTS,
        wards=WARDS,
        staff_roles=STAFF_ROLES,
        days=days,
        day_labels=day_labels,
        monday=monday,
        sunday=sunday,
        week_offset=week_offset,
        filter_ward=filter_ward,
        filter_role=filter_role,
        staff_users=staff_users,
    )


# ─── API: Assign Staff to Shift ────────────────────────────────
@duty_roster_bp.route('/api/assign', methods=['POST'])
@login_required
@roster_access_required
def api_assign():
    """Create a new duty roster entry."""
    data = request.get_json(silent=True) or {}
    staff_id = data.get('staff_id')
    shift = data.get('shift')
    duty_date_str = data.get('duty_date')
    ward = data.get('ward')
    notes = data.get('notes', '')

    # Validate required fields
    if not all([staff_id, shift, duty_date_str, ward]):
        return jsonify({'success': False, 'error': 'staff_id, shift, duty_date, and ward are required.'}), 400

    if shift not in SHIFTS:
        return jsonify({'success': False, 'error': f'Invalid shift. Choose from: {", ".join(SHIFTS)}'}), 400
    if ward not in WARDS:
        return jsonify({'success': False, 'error': f'Invalid ward. Choose from: {", ".join(WARDS)}'}), 400

    try:
        duty_date = datetime.strptime(duty_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    staff = User.query.get(staff_id)
    if not staff:
        return jsonify({'success': False, 'error': 'Staff member not found.'}), 404

    # Determine display name and role label
    staff_name = staff.username
    role_map = {
        UserRole.DOCTOR: 'Doctor',
        UserRole.NURSE: 'Nurse',
        UserRole.LAB_STAFF: 'Lab',
        UserRole.PHARMACIST: 'Pharmacy',
        UserRole.RECEPTIONIST: 'Reception',
    }
    staff_role = role_map.get(staff.role, staff.role.value if staff.role else 'Staff')

    # Check for duplicate assignment
    existing = DutyRoster.query.filter_by(
        staff_id=staff.id,
        shift=shift,
        duty_date=duty_date,
        ward=ward,
    ).first()
    if existing:
        return jsonify({'success': False, 'error': 'This staff member is already assigned to this shift/ward/date.'}), 409

    entry = DutyRoster(
        staff_id=staff.id,
        staff_name=staff_name,
        staff_role=staff_role,
        shift=shift,
        duty_date=duty_date,
        ward=ward,
        notes=notes,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({'success': True, 'entry': _roster_to_dict(entry)})


# ─── API: Get Current Week's Roster ────────────────────────────
@duty_roster_bp.route('/api/week')
@login_required
@roster_access_required
def api_week():
    """Return the current week's roster as JSON."""
    week_offset = request.args.get('week', 0, type=int)
    ref = date.today() + timedelta(weeks=week_offset)
    monday, sunday = _get_week_bounds(ref)

    filter_ward = request.args.get('ward', '')
    filter_role = request.args.get('role', '')

    query = DutyRoster.query.filter(
        DutyRoster.duty_date >= monday,
        DutyRoster.duty_date <= sunday,
    )
    if filter_ward:
        query = query.filter(DutyRoster.ward == filter_ward)
    if filter_role:
        query = query.filter(DutyRoster.staff_role == filter_role)

    entries = query.order_by(DutyRoster.duty_date, DutyRoster.shift).all()

    return jsonify({
        'success': True,
        'monday': monday.isoformat(),
        'sunday': sunday.isoformat(),
        'entries': [_roster_to_dict(e) for e in entries],
    })
