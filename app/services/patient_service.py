"""
Patient Service Module
- UHID generation (format: CHN-YYYY-XXXXXX)
- Patient registration (walk-in and user-based)
- Patient search and retrieval
- Duplicate detection
- Patient history management
"""

from datetime import datetime, date
from difflib import SequenceMatcher
import logging
import re

from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError

from app.models.models import db, Patient, User

logger = logging.getLogger(__name__)


class PatientService:
    @staticmethod
    def split_name(full_name):
        """Split canonical full name into first_name/last_name."""
        raw = ' '.join((full_name or '').strip().split())
        if not raw:
            return '', ''
        parts = raw.split(' ')
        return parts[0], ' '.join(parts[1:]) if len(parts) > 1 else ''

    """Service class for patient-related operations"""

    @staticmethod
    def normalize_phone(phone):
        """Normalize phone to digits-only national/international suffix."""
        if not phone:
            return ''
        digits = re.sub(r'[^0-9]', '', str(phone))
        return digits[-10:] if len(digits) >= 10 else digits

    @staticmethod
    def validate_phone(phone):
        """Validate phone length if provided."""
        if not phone:
            return True
        digits = re.sub(r'[^0-9]', '', str(phone))
        return 10 <= len(digits) <= 15

    @staticmethod
    def generate_uhid():
        """
        Generate a unique UHID in format: CHN-YYYY-XXXX
        Where YYYY = current year, XXXX = 4-digit sequential number
        Example: CHN-2026-0001, CHN-2026-0002, etc.
        """
        current_year = datetime.utcnow().year
        prefix = f'CHN-{current_year}'

        # Find the last patient created this year (supports CHN- and legacy PAT- prefixes)
        last_patient = Patient.query.filter(
            Patient.uhid.like(f'{prefix}-%')
        ).order_by(Patient.id.desc()).first()

        if last_patient:
            last_seq = int(last_patient.uhid.split('-')[-1])
            next_seq = last_seq + 1
        else:
            legacy_prefix = f'PAT-{current_year}'
            legacy_patient = Patient.query.filter(
                Patient.uhid.like(f'{legacy_prefix}-%')
            ).order_by(Patient.id.desc()).first()
            if legacy_patient:
                last_seq = int(legacy_patient.uhid.split('-')[-1])
                next_seq = last_seq + 1
            else:
                next_seq = 1

        uhid = f'{prefix}-{next_seq:04d}'

        # Best-effort uniqueness pre-check; insert path still handles race safely.
        while Patient.query.filter_by(uhid=uhid).first():
            next_seq += 1
            uhid = f'{prefix}-{next_seq:04d}'

        return uhid

    @staticmethod
    def create_walk_in_patient(name, age, gender, phone=None, address=None, hospital_id=None, date_of_birth=None):
        """
        Create a walk-in patient record without requiring a user account.
        Returns Patient or None.
        """
        try:
            name = ' '.join((name or '').strip().split())
            first_name, last_name = PatientService.split_name(name)
            gender = (gender or '').strip()

            if not name or not gender:
                logger.error('Error creating walk-in patient: name and gender are required')
                return None

            age = int(age) if age is not None and str(age).strip() != '' else None
            if age is not None and (age < 0 or age > 150):
                logger.error('Error creating walk-in patient: invalid age %s', age)
                return None

            if not PatientService.validate_phone(phone):
                logger.error('Error creating walk-in patient: invalid phone %s', phone)
                return None
            phone_norm = PatientService.normalize_phone(phone) or None

            # Retry on UHID race condition under concurrent writes.
            for _ in range(5):
                uhid = PatientService.generate_uhid()
                patient = Patient(
                    uhid=uhid,
                    name=name,
                    date_of_birth=date_of_birth if isinstance(date_of_birth, date) else None,
                    first_name=first_name,
                    last_name=last_name,
                    age=age,
                    gender=gender,
                    phone=phone_norm,
                    address=address,
                    hospital_id=hospital_id,
                    user_id=None,
                    is_walk_in=True,
                    created_at=datetime.utcnow()
                )
                patient.sync_legacy_name_fields()
                db.session.add(patient)
                try:
                    db.session.commit()
                    logger.info(f'Walk-in patient created: {uhid} - {patient.full_name}')
                    return patient
                except IntegrityError as ie:
                    db.session.rollback()
                    err = str(ie.orig).lower()
                    if 'uhid' in err:
                        continue
                    logger.error(f'Error creating walk-in patient: {str(ie)}')
                    return None

            logger.error('Error creating walk-in patient: failed after UHID retries')
            return None

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating walk-in patient: {str(e)}')
            return None

    @staticmethod
    def create_registered_patient(user, name, age, gender, phone=None, address=None, hospital_id=None, date_of_birth=None):
        """
        Create a patient record linked to a user account.
        Returns Patient or None.
        """
        try:
            if not isinstance(user, User):
                logger.error('Error creating registered patient: invalid user')
                return None

            existing = Patient.query.filter_by(user_id=user.id).first()
            if existing:
                logger.warning(f'Patient already exists for user {user.username}')
                return existing

            if not PatientService.validate_phone(phone):
                logger.error('Error creating registered patient: invalid phone %s', phone)
                return None
            phone_norm = PatientService.normalize_phone(phone) or None

            for _ in range(5):
                uhid = PatientService.generate_uhid()
                name = ' '.join((name or '').strip().split())
                first_name, last_name = PatientService.split_name(name)
                patient = Patient(
                    uhid=uhid,
                    user_id=user.id,
                    name=name or f"{first_name} {last_name}".strip(),
                    date_of_birth=date_of_birth if isinstance(date_of_birth, date) else None,
                    first_name=(first_name or '').strip(),
                    last_name=(last_name or '').strip(),
                    age=int(age) if age is not None and str(age).strip() != '' else None,
                    gender=(gender or '').strip(),
                    phone=phone_norm,
                    address=address,
                    hospital_id=hospital_id,
                    is_walk_in=False,
                    created_at=datetime.utcnow()
                )
                patient.sync_legacy_name_fields()
                db.session.add(patient)
                try:
                    db.session.commit()
                    logger.info(f'Registered patient created: {uhid} for user {user.username}')
                    return patient
                except IntegrityError as ie:
                    db.session.rollback()
                    err = str(ie.orig).lower()
                    if 'uhid' in err:
                        continue
                    logger.error(f'Error creating registered patient: {str(ie)}')
                    return None

            logger.error('Error creating registered patient: failed after UHID retries')
            return None

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating registered patient: {str(e)}')
            return None

    @staticmethod
    def find_similar_patients(name=None, phone=None, age=None, threshold=0.7):
        """
        Find potentially duplicate patients based on name, phone, and age.
        Returns list of dicts: { patient, similarity, reason }
        """
        filters = []
        name_norm = ' '.join((name or '').lower().split()) if name else ''
        phone_norm = PatientService.normalize_phone(phone) if phone else ''

        # Deterministic duplicate check requested by business:
        # same/similar name + same age should always be considered.
        if name_norm and age is not None and str(age).strip() != '':
            try:
                age_i = int(age)
                deterministic = Patient.query.filter(
                    Patient.name.ilike(f'%{name_norm}%'),
                    Patient.age == age_i
                ).limit(25).all()
                seeded = [{
                    'patient': p,
                    'similarity': 0.99,
                    'reason': 'Name + age match'
                } for p in deterministic]
            except (TypeError, ValueError):
                seeded = []
        else:
            seeded = []

        if phone_norm:
            filters.append(Patient.phone.ilike(f'%{phone_norm}%'))

        if age is not None and str(age).strip() != '':
            try:
                age = int(age)
                filters.append(and_(Patient.age >= age - 2, Patient.age <= age + 2))
            except (TypeError, ValueError):
                age = None

        if name_norm:
            tokens = [t for t in name_norm.split() if len(t) >= 2]
            if tokens:
                name_filters = []
                for token in tokens:
                    name_filters.append(Patient.name.ilike(f'%{token}%'))
                    name_filters.append(Patient.first_name.ilike(f'%{token}%'))
                    name_filters.append(Patient.last_name.ilike(f'%{token}%'))
                filters.append(or_(*name_filters))

        candidates_q = Patient.query
        if filters:
            candidates_q = candidates_q.filter(or_(*filters))
        candidates = candidates_q.limit(200).all()

        similar_patients = list(seeded)
        for patient in candidates:
            reasons = []
            score = 0.0

            if name_norm:
                patient_name = ' '.join(patient.full_name.lower().split())
                ratio = SequenceMatcher(None, name_norm, patient_name).ratio()
                score = max(score, ratio)
                if ratio >= threshold:
                    reasons.append(f'Name match ({round(ratio * 100, 1)}%)')
                if age is not None and patient.age == age:
                    score = max(score, min(1.0, ratio + 0.15))
                    reasons.append('Same age')

            if age is not None and patient.age == age and not name_norm:
                score = max(score, 0.75)
                reasons.append('Same age')

            if phone_norm and patient.phone:
                patient_phone = PatientService.normalize_phone(patient.phone)
                if patient_phone and phone_norm == patient_phone:
                    score = max(score, 0.98)
                    reasons.append('Exact phone match')
                elif patient_phone and (phone_norm in patient_phone or patient_phone in phone_norm):
                    score = max(score, 0.85)
                    reasons.append('Phone match')

            if score >= threshold:
                similar_patients.append({
                    'patient': patient,
                    'similarity': round(score, 2),
                    'reason': ', '.join(dict.fromkeys(reasons)) if reasons else 'Potential duplicate'
                })

        # De-duplicate by patient id (keep highest similarity).
        best = {}
        for item in similar_patients:
            pid = item['patient'].id
            if pid not in best or item['similarity'] > best[pid]['similarity']:
                best[pid] = item
        similar_patients = list(best.values())

        similar_patients.sort(
            key=lambda s: (s['similarity'], s['patient'].created_at or datetime.min),
            reverse=True
        )
        return similar_patients

    @staticmethod
    def search_patients(query, hospital_id=None, limit=10):
        """
        Search patients by UHID, name, or phone.
        Returns relevance-sorted patient list.
        """
        raw_query = (query or '').strip()
        if not raw_query:
            return []

        query_upper = raw_query.upper()
        phone_query = PatientService.normalize_phone(raw_query)

        filters = [
            Patient.uhid.ilike(f'%{query_upper}%'),
            Patient.name.ilike(f'%{raw_query}%'),
            Patient.first_name.ilike(f'%{raw_query}%'),
            Patient.last_name.ilike(f'%{raw_query}%'),
            Patient.phone.ilike(f'%{raw_query}%')
        ]
        if phone_query:
            filters.append(Patient.phone.ilike(f'%{phone_query}%'))

        q = Patient.query.filter(or_(*filters))
        if hospital_id:
            q = q.filter_by(hospital_id=hospital_id)

        candidates = q.limit(max(limit * 5, 50)).all()

        def score(patient):
            s = 0
            p_uhid = (patient.uhid or '').upper()
            p_name = patient.full_name.lower()
            p_phone = PatientService.normalize_phone(patient.phone)
            raw_lower = raw_query.lower()

            if p_uhid == query_upper:
                s += 100
            elif p_uhid.startswith(query_upper):
                s += 80
            elif query_upper in p_uhid:
                s += 60

            if p_name == raw_lower:
                s += 70
            elif p_name.startswith(raw_lower):
                s += 50
            elif raw_lower in p_name:
                s += 35

            if phone_query and p_phone:
                if p_phone == phone_query:
                    s += 65
                elif p_phone.endswith(phone_query) or phone_query in p_phone:
                    s += 45

            if raw_query.isdigit() and patient.id == int(raw_query):
                s += 55

            return s

        ranked = sorted(
            candidates,
            key=lambda p: (score(p), p.created_at or datetime.min),
            reverse=True
        )
        return ranked[:limit]

    @staticmethod
    def get_patient_by_uhid(uhid):
        """Get a patient by UHID."""
        return Patient.query.filter_by(uhid=uhid).first()

    @staticmethod
    def get_patient_by_id(patient_id):
        """Get a patient by database ID."""
        return Patient.query.get(patient_id)

    @staticmethod
    def get_patient_by_phone(phone):
        """Get patients by phone number."""
        search_digits = PatientService.normalize_phone(phone)
        if not search_digits:
            return []
        return Patient.query.filter(Patient.phone.ilike(f'%{search_digits}%')).all()

    @staticmethod
    def update_patient(patient, **kwargs):
        """Update patient information."""
        try:
            for key, value in kwargs.items():
                if hasattr(patient, key) and key not in ['id', 'uhid', 'user_id', 'created_at']:
                    if key == 'phone' and value and not PatientService.validate_phone(value):
                        logger.error('Invalid phone update for patient %s', patient.uhid)
                        return None
                    setattr(patient, key, PatientService.normalize_phone(value) if key == 'phone' else value)

            patient.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f'Patient {patient.uhid} updated')
            return patient

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating patient {patient.uhid}: {str(e)}')
            return None

    @staticmethod
    def get_all_patients(hospital_id=None, is_walk_in=None, limit=100, offset=0):
        """Get all patients with optional filtering."""
        q = Patient.query

        if hospital_id:
            q = q.filter_by(hospital_id=hospital_id)

        if is_walk_in is not None:
            q = q.filter_by(is_walk_in=is_walk_in)

        total = q.count()
        patients = q.order_by(Patient.created_at.desc()).limit(limit).offset(offset).all()

        return patients, total

    @staticmethod
    def get_patient_summary(patient):
        """Get a summary of patient information for API responses."""
        return {
            'id': patient.id,
            'uhid': patient.uhid,
            'name': patient.full_name,
            'display_name': patient.display_name,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'age': patient.age,
            'gender': patient.gender,
            'phone': patient.phone,
            'address': patient.address,
            'is_walk_in': patient.is_walk_in,
            'has_account': patient.is_registered_user(),
            'created_at': patient.created_at.isoformat() if patient.created_at else None,
            'updated_at': patient.updated_at.isoformat() if patient.updated_at else None
        }
