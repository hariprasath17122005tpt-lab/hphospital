from flask import Blueprint, render_template, request, jsonify
from app.models.models import db, Doctor, Appointment, PatientFeedback
from sqlalchemy import func

doctor_search_bp = Blueprint('doctor_search', __name__, url_prefix='/find-doctor')


def _base_query():
    """Return a query for active, verified, non-deleted, non-suspended doctors."""
    return Doctor.query.filter(
        Doctor.verified == True,
        Doctor.is_deleted == False,
        Doctor.is_suspended == False,
    )


@doctor_search_bp.route('/')
def listing():
    """Public doctor directory page."""
    q = request.args.get('q', '').strip()
    specialty = request.args.get('specialty', '').strip()

    query = _base_query()

    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Doctor.first_name.ilike(like),
                Doctor.last_name.ilike(like),
                Doctor.specialization.ilike(like),
                Doctor.qualification.ilike(like),
            )
        )

    if specialty:
        query = query.filter(Doctor.specialization.ilike(f'%{specialty}%'))

    doctors = query.order_by(
        db.case((Doctor.experience_years.is_(None), 0), else_=Doctor.experience_years).desc(),
        Doctor.first_name
    ).all()

    # Gather all specializations for filter buttons
    all_specs = (
        db.session.query(Doctor.specialization)
        .filter(Doctor.verified == True, Doctor.is_deleted == False, Doctor.is_suspended == False)
        .distinct()
        .all()
    )
    specializations = sorted({s[0] for s in all_specs if s[0]})

    # Pre-compute average ratings per doctor
    ratings_q = (
        db.session.query(
            PatientFeedback.doctor_id,
            func.avg(PatientFeedback.doctor_rating).label('avg_rating'),
            func.count(PatientFeedback.id).label('review_count'),
        )
        .filter(PatientFeedback.doctor_id.isnot(None))
        .group_by(PatientFeedback.doctor_id)
        .all()
    )
    ratings_map = {r.doctor_id: {'avg': round(r.avg_rating or 0, 1), 'count': r.review_count} for r in ratings_q}

    return render_template(
        'doctor_search/listing.html',
        doctors=doctors,
        specializations=specializations,
        ratings=ratings_map,
        q=q,
        selected_specialty=specialty,
    )


@doctor_search_bp.route('/api/search')
def api_search():
    """JSON API for doctor search (AJAX)."""
    q = request.args.get('q', '').strip()
    specialty = request.args.get('specialty', '').strip()

    query = _base_query()

    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Doctor.first_name.ilike(like),
                Doctor.last_name.ilike(like),
                Doctor.specialization.ilike(like),
                Doctor.qualification.ilike(like),
            )
        )

    if specialty:
        query = query.filter(Doctor.specialization.ilike(f'%{specialty}%'))

    doctors = query.order_by(Doctor.experience_years.desc().nullslast(), Doctor.first_name).limit(50).all()

    # Ratings
    doc_ids = [d.id for d in doctors]
    ratings_q = (
        db.session.query(
            PatientFeedback.doctor_id,
            func.avg(PatientFeedback.doctor_rating).label('avg_rating'),
            func.count(PatientFeedback.id).label('review_count'),
        )
        .filter(PatientFeedback.doctor_id.in_(doc_ids))
        .group_by(PatientFeedback.doctor_id)
        .all()
    ) if doc_ids else []
    ratings_map = {r.doctor_id: {'avg': round(r.avg_rating or 0, 1), 'count': r.review_count} for r in ratings_q}

    results = []
    for d in doctors:
        rating_info = ratings_map.get(d.id, {'avg': 0, 'count': 0})
        results.append({
            'id': d.id,
            'first_name': d.first_name,
            'last_name': d.last_name,
            'specialization': d.specialization or '',
            'qualification': d.qualification or '',
            'experience_years': d.experience_years or 0,
            'consultation_fee': d.consultation_fee or 0,
            'phone': d.phone or '',
            'avg_rating': rating_info['avg'],
            'review_count': rating_info['count'],
        })

    return jsonify({'success': True, 'doctors': results})


@doctor_search_bp.route('/<int:doctor_id>')
def detail(doctor_id):
    """Public doctor profile page."""
    doctor = _base_query().filter(Doctor.id == doctor_id).first_or_404()

    # Rating info
    rating_data = (
        db.session.query(
            func.avg(PatientFeedback.doctor_rating).label('avg_rating'),
            func.count(PatientFeedback.id).label('review_count'),
        )
        .filter(PatientFeedback.doctor_id == doctor_id)
        .first()
    )
    avg_rating = round(rating_data.avg_rating or 0, 1) if rating_data else 0
    review_count = rating_data.review_count if rating_data else 0

    # Recent published reviews
    reviews = (
        PatientFeedback.query
        .filter(
            PatientFeedback.doctor_id == doctor_id,
            PatientFeedback.is_published == True,
        )
        .order_by(PatientFeedback.created_at.desc())
        .limit(10)
        .all()
    )

    # Appointment count (total completed)
    appt_count = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'Completed',
    ).count()

    return render_template(
        'doctor_search/detail.html',
        doctor=doctor,
        avg_rating=avg_rating,
        review_count=review_count,
        reviews=reviews,
        appt_count=appt_count,
    )
