"""Patient Feedback & Doctor Rating Module"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import (db, PatientFeedback, Patient, Doctor, UserRole)
from datetime import datetime
from sqlalchemy import func

feedback_bp = Blueprint('feedback_module', __name__, url_prefix='/feedback')


@feedback_bp.route('/')
@feedback_bp.route('/dashboard')
@login_required
def dashboard():
    role_val = getattr(current_user.role, 'value', str(current_user.role)).upper()

    if role_val == 'PATIENT':
        patient = current_user.patient
        if not patient:
            return redirect(url_for('patient.dashboard'))
        feedbacks = PatientFeedback.query.filter_by(patient_id=patient.id).order_by(
            PatientFeedback.created_at.desc()
        ).all()
    elif role_val == 'DOCTOR':
        doctor = current_user.doctor
        if not doctor:
            return redirect(url_for('doctor.portal'))
        feedbacks = PatientFeedback.query.filter_by(doctor_id=doctor.id, is_published=True).order_by(
            PatientFeedback.created_at.desc()
        ).all()
    else:
        feedbacks = PatientFeedback.query.order_by(PatientFeedback.created_at.desc()).limit(100).all()

    avg_rating = db.session.query(func.avg(PatientFeedback.rating)).scalar() or 0
    total_feedback = PatientFeedback.query.count()
    recommend_pct = 0
    if total_feedback > 0:
        recommend_count = PatientFeedback.query.filter_by(would_recommend=True).count()
        recommend_pct = round((recommend_count / total_feedback) * 100)

    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[i] = PatientFeedback.query.filter_by(rating=i).count()

    stats = {
        'avg_rating': round(avg_rating, 1),
        'total': total_feedback,
        'recommend_pct': recommend_pct,
        'rating_distribution': rating_dist,
        '5_star_pct': round((rating_dist.get(5, 0) / max(total_feedback, 1)) * 100),
    }

    # Top-rated doctors
    top_doctors = db.session.query(
        Doctor.id, Doctor.first_name, Doctor.last_name, Doctor.specialization,
        func.avg(PatientFeedback.doctor_rating).label('avg_rating'),
        func.count(PatientFeedback.id).label('count')
    ).join(PatientFeedback, PatientFeedback.doctor_id == Doctor.id).group_by(
        Doctor.id
    ).having(func.count(PatientFeedback.id) >= 1).order_by(
        func.avg(PatientFeedback.doctor_rating).desc()
    ).limit(10).all()

    return render_template('feedback_module/dashboard.html',
                           feedbacks=feedbacks, stats=stats,
                           top_doctors=top_doctors, role=role_val)


@feedback_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        try:
            patient = current_user.patient
            if not patient:
                flash('Patient profile required.', 'error')
                return redirect(url_for('patient.dashboard'))

            fb = PatientFeedback(
                patient_id=patient.id,
                doctor_id=request.form.get('doctor_id', type=int),
                feedback_type=request.form.get('feedback_type', 'Overall'),
                rating=request.form.get('rating', 5, type=int),
                review_text=request.form.get('review_text'),
                doctor_rating=request.form.get('doctor_rating', type=int),
                staff_rating=request.form.get('staff_rating', type=int),
                facility_rating=request.form.get('facility_rating', type=int),
                cleanliness_rating=request.form.get('cleanliness_rating', type=int),
                wait_time_rating=request.form.get('wait_time_rating', type=int),
                would_recommend=bool(request.form.get('would_recommend')),
                is_anonymous=bool(request.form.get('is_anonymous')),
            )
            db.session.add(fb)
            db.session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('feedback_module.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    doctors = Doctor.query.filter_by(is_deleted=False).all()
    return render_template('feedback_module/submit.html', doctors=doctors)


@feedback_bp.route('/api/respond', methods=['POST'])
@login_required
def respond():
    """Admin/Doctor can respond to feedback."""
    data = request.get_json(silent=True) or {}
    fb = PatientFeedback.query.get(data.get('feedback_id'))
    if not fb:
        return jsonify({'success': False}), 404
    fb.response_text = data.get('response', '')
    fb.responded_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})
