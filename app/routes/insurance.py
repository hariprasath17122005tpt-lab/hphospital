"""Insurance & TPA Management Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, InsurancePolicy, InsuranceClaim, Patient, IPAdmission, UserRole)
from datetime import datetime
from sqlalchemy import func
import uuid

insurance_bp = Blueprint('insurance', __name__, url_prefix='/insurance')


def _staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.doctor_login'))
        role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()
        if role_val not in ('DOCTOR', 'HOST', 'ADMIN', 'RECEPTIONIST', 'NURSE'):
            flash('Access denied.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@insurance_bp.route('/')
@insurance_bp.route('/dashboard')
@login_required
@_staff_required
def dashboard():
    claims = InsuranceClaim.query.order_by(InsuranceClaim.created_at.desc()).limit(50).all()
    policies = InsurancePolicy.query.filter_by(is_active=True).count()

    stats = {
        'active_policies': policies,
        'pending_claims': InsuranceClaim.query.filter(InsuranceClaim.status.in_(['Initiated', 'Submitted'])).count(),
        'under_review': InsuranceClaim.query.filter_by(status='Under Review').count(),
        'approved_this_month': InsuranceClaim.query.filter(
            InsuranceClaim.status.in_(['Approved', 'Settled']),
            func.extract('month', InsuranceClaim.approved_at) == datetime.utcnow().month
        ).count(),
        'total_claimed': db.session.query(func.coalesce(func.sum(InsuranceClaim.claim_amount), 0)).scalar(),
        'total_approved': db.session.query(func.coalesce(func.sum(InsuranceClaim.approved_amount), 0)).scalar(),
    }

    return render_template('insurance/dashboard.html', claims=claims, stats=stats)


@insurance_bp.route('/policy/add', methods=['GET', 'POST'])
@login_required
@_staff_required
def add_policy():
    if request.method == 'POST':
        try:
            policy = InsurancePolicy(
                patient_id=request.form.get('patient_id', type=int),
                provider_name=request.form.get('provider_name'),
                policy_number=request.form.get('policy_number'),
                policy_type=request.form.get('policy_type', 'Individual'),
                tpa_name=request.form.get('tpa_name'),
                tpa_id=request.form.get('tpa_id'),
                sum_insured=request.form.get('sum_insured', 0, type=float),
                balance_available=request.form.get('sum_insured', 0, type=float),
                valid_from=datetime.strptime(request.form.get('valid_from'), '%Y-%m-%d').date() if request.form.get('valid_from') else None,
                valid_until=datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d').date() if request.form.get('valid_until') else None,
                is_cashless_eligible=bool(request.form.get('is_cashless')),
                is_active=True
            )
            db.session.add(policy)
            db.session.commit()
            flash('Insurance policy added successfully!', 'success')
            return redirect(url_for('insurance.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    patients = Patient.query.order_by(Patient.name).all()
    return render_template('insurance/add_policy.html', patients=patients)


@insurance_bp.route('/claim/create', methods=['GET', 'POST'])
@login_required
@_staff_required
def create_claim():
    if request.method == 'POST':
        try:
            claim = InsuranceClaim(
                policy_id=request.form.get('policy_id', type=int),
                patient_id=request.form.get('patient_id', type=int),
                admission_id=request.form.get('admission_id', type=int),
                claim_number=f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                claim_type=request.form.get('claim_type', 'Cashless'),
                claim_amount=request.form.get('claim_amount', 0, type=float),
                diagnosis=request.form.get('diagnosis'),
                treatment_type=request.form.get('treatment_type'),
                status='Initiated'
            )
            db.session.add(claim)
            db.session.commit()
            flash('Insurance claim created!', 'success')
            return redirect(url_for('insurance.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    patients = Patient.query.order_by(Patient.name).all()
    policies = InsurancePolicy.query.filter_by(is_active=True).all()
    return render_template('insurance/create_claim.html', patients=patients, policies=policies)


@insurance_bp.route('/api/update-claim', methods=['POST'])
@login_required
@_staff_required
def update_claim():
    data = request.get_json(silent=True) or {}
    claim = InsuranceClaim.query.get(data.get('claim_id'))
    if not claim:
        return jsonify({'success': False, 'error': 'Claim not found'}), 404

    if 'status' in data:
        claim.status = data['status']
        if data['status'] in ('Approved', 'Partially Approved'):
            claim.approved_amount = data.get('approved_amount', claim.claim_amount)
            claim.approved_at = datetime.utcnow()
        elif data['status'] == 'Rejected':
            claim.rejection_reason = data.get('rejection_reason', '')
        elif data['status'] == 'Settled':
            claim.settled_at = datetime.utcnow()
    if 'submitted_at' not in str(claim.submitted_at) and data.get('status') == 'Submitted':
        claim.submitted_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True})


@insurance_bp.route('/patient/<int:patient_id>')
@login_required
@_staff_required
def patient_insurance(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    policies = InsurancePolicy.query.filter_by(patient_id=patient_id).all()
    claims = InsuranceClaim.query.filter_by(patient_id=patient_id).order_by(InsuranceClaim.created_at.desc()).all()
    return render_template('insurance/patient_insurance.html', patient=patient, policies=policies, claims=claims)


@insurance_bp.route('/api/patient-policies/<int:patient_id>')
@login_required
def get_patient_policies(patient_id):
    policies = InsurancePolicy.query.filter_by(patient_id=patient_id, is_active=True).all()
    return jsonify([{
        'id': p.id,
        'provider_name': p.provider_name,
        'policy_number': p.policy_number,
        'sum_insured': p.sum_insured,
        'balance': p.balance_available,
        'is_cashless': p.is_cashless_eligible,
        'valid_until': p.valid_until.isoformat() if p.valid_until else None
    } for p in policies])
