from collections import Counter
from datetime import datetime
import json

from app.models.models import (
    Appointment,
    LabOrder,
    LabReport,
    Patient,
    PharmacyOrder,
    PharmacySale,
    Prescription,
    PrescriptionMedicine,
    ReceptionQueue,
    Visit,
)
from app.services.patient_service import PatientService


class PatientHistoryService:
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 100

    @classmethod
    def get_patient_history_payload(cls, patient_id, page=1, limit=None):
        patient = PatientService.get_patient_by_id(patient_id)
        if not patient:
            return None

        limit = min(max(int(limit or cls.DEFAULT_LIMIT), 1), cls.MAX_LIMIT)
        page = max(int(page or 1), 1)

        visits = cls._serialize_visits(
            Visit.query.filter_by(patient_id=patient.id)
            .order_by(Visit.visit_date.desc(), Visit.id.desc())
            .limit(limit)
            .all()
        )
        prescriptions = cls._serialize_prescriptions(
            Prescription.query.filter_by(patient_id=patient.id)
            .order_by(Prescription.prescribed_at.desc(), Prescription.id.desc())
            .limit(limit)
            .all()
        )
        lab_orders = cls._serialize_lab_orders(
            LabOrder.query.filter_by(patient_id=patient.id)
            .order_by(LabOrder.created_at.desc(), LabOrder.id.desc())
            .limit(limit)
            .all()
        )
        lab_reports = cls._serialize_lab_reports(
            LabReport.query.filter_by(patient_id=patient.id)
            .order_by(LabReport.conducted_at.desc(), LabReport.updated_at.desc(), LabReport.id.desc())
            .limit(limit)
            .all()
        )
        pharmacy = cls._serialize_pharmacy(
            cls._pharmacy_rows_for_patient(patient.id, limit=limit)
        )

        timeline = cls._build_timeline(
            patient=patient,
            visits=visits,
            prescriptions=prescriptions,
            lab_orders=lab_orders,
            lab_reports=lab_reports,
            pharmacy=pharmacy,
        )

        start = (page - 1) * limit
        end = start + limit
        paged_timeline = timeline[start:end]

        return {
            'patient': cls._serialize_patient(patient),
            'visits': visits,
            'prescriptions': prescriptions,
            'lab_orders': lab_orders,
            'lab_reports': lab_reports,
            'pharmacy': pharmacy,
            'timeline': paged_timeline,
            'suggestions': {
                'previously_used_medicines': cls._previously_used_medicines(pharmacy, prescriptions),
            },
            'pagination': {
                'page': page,
                'limit': limit,
                'total_timeline_entries': len(timeline),
                'returned_entries': len(paged_timeline),
                'has_next': end < len(timeline),
            }
        }

    @staticmethod
    def _serialize_patient(patient):
        payload = PatientService.get_patient_summary(patient)
        payload.update({
            'allergies': patient.allergies,
            'medical_history': patient.medical_history,
            'current_medications': patient.current_medications,
            'blood_type': patient.blood_type,
            'emergency_contact': patient.emergency_contact,
        })
        return payload

    @staticmethod
    def _doctor_name(doctor):
        if not doctor:
            return None
        return f"Dr. {doctor.first_name} {doctor.last_name}".strip()

    @classmethod
    def _serialize_visits(cls, visits):
        out = []
        for visit in visits:
            out.append({
                'id': visit.id,
                'patient_id': visit.patient_id,
                'visit_type': visit.visit_type,
                'visit_date': cls._iso(visit.visit_date),
                'doctor_id': visit.doctor_id,
                'doctor_name': cls._doctor_name(visit.doctor),
                'notes': visit.notes,
                'created_at': cls._iso(visit.created_at),
            })
        return out

    @classmethod
    def _serialize_prescriptions(cls, prescriptions):
        out = []
        for rx in prescriptions:
            medicines = []
            try:
                items = rx.medicine_items.all()
            except Exception:
                items = []
            if items:
                medicines = [{
                    'name': item.medicine_name,
                    'dosage': item.dosage,
                    'frequency': item.frequency,
                    'duration': item.duration,
                    'instruction': item.instruction,
                } for item in items]
            else:
                medicines = cls._parse_legacy_medicines(rx.medicines)

            out.append({
                'id': rx.id,
                'patient_id': rx.patient_id,
                'doctor_id': rx.doctor_id,
                'doctor_name': cls._doctor_name(rx.doctor),
                'diagnosis': rx.diagnosis,
                'medicines': medicines,
                'dosage': rx.dosage,
                'instructions': rx.instructions,
                'notes': rx.notes,
                'created_at': cls._iso(rx.prescribed_at),
                'prescribed_at': cls._iso(rx.prescribed_at),
            })
        return out

    @classmethod
    def _serialize_lab_orders(cls, orders):
        out = []
        for order in orders:
            out.append({
                'id': order.id,
                'patient_id': order.patient_id,
                'test_name': order.test_name,
                'status': cls._normalize_lab_status(order.status),
                'source_type': order.source_type,
                'doctor_id': order.doctor_id,
                'doctor_name': cls._doctor_name(order.doctor),
                'created_at': cls._iso(order.created_at),
                'updated_at': cls._iso(order.updated_at),
                'result_preview': order.result_preview() if hasattr(order, 'result_preview') else '',
            })
        return out

    @classmethod
    def _serialize_lab_reports(cls, reports):
        out = []
        for report in reports:
            file_path = report.file_path
            report_data = report.report_data
            if isinstance(report_data, str):
                try:
                    report_data = json.loads(report_data)
                except json.JSONDecodeError:
                    report_data = {}
            if not file_path and isinstance(report_data, dict):
                file_path = report_data.get('file_path') or report_data.get('pdf_path')

            out.append({
                'id': report.id,
                'patient_id': report.patient_id,
                'lab_order_id': report.lab_order_id,
                'test_name': report.test_name,
                'status': report.status,
                'file_path': file_path,
                'created_at': cls._iso(report.conducted_at or report.updated_at),
                'conducted_at': cls._iso(report.conducted_at),
                'updated_at': cls._iso(report.updated_at),
            })
        out.sort(key=lambda item: item.get('created_at') or '', reverse=True)
        return out

    @classmethod
    def _pharmacy_rows_for_patient(cls, patient_id, limit):
        sales = (
            PharmacySale.query.filter_by(patient_id=patient_id)
            .order_by(PharmacySale.sold_at.desc(), PharmacySale.id.desc())
            .limit(limit)
            .all()
        )
        if sales:
            return sales
        return (
            PharmacyOrder.query.filter_by(patient_id=patient_id)
            .order_by(PharmacyOrder.dispensed_at.desc(), PharmacyOrder.created_at.desc(), PharmacyOrder.id.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def _serialize_pharmacy(cls, rows):
        out = []
        for row in rows:
            if isinstance(row, PharmacySale):
                sold_at = row.sold_at
                order = row.pharmacy_order
                out.append({
                    'id': row.id,
                    'patient_id': row.patient_id,
                    'medicine_name': row.medicine_name,
                    'quantity': row.quantity,
                    'price': row.price,
                    'status': 'Sold',
                    'sold_at': cls._iso(sold_at),
                    'created_at': cls._iso(sold_at),
                    'dosage': order.dosage if order else None,
                    'notes': row.notes or (order.notes if order else None),
                    'doctor_name': cls._doctor_name(order.doctor) if order and order.doctor else None,
                })
            else:
                sold_at = row.dispensed_at or row.created_at
                out.append({
                    'id': row.id,
                    'patient_id': row.patient_id,
                    'medicine_name': row.medicine_name,
                    'quantity': row.quantity,
                    'price': None,
                    'status': row.status,
                    'sold_at': cls._iso(sold_at),
                    'created_at': cls._iso(sold_at),
                    'dosage': row.dosage,
                    'notes': row.notes,
                    'doctor_name': cls._doctor_name(row.doctor) if row.doctor else None,
                })
        out.sort(key=lambda item: item.get('sold_at') or item.get('created_at') or '', reverse=True)
        return out

    @classmethod
    def _build_timeline(cls, patient, visits, prescriptions, lab_orders, lab_reports, pharmacy):
        items = []

        for visit in visits:
            visit_type = (visit.get('visit_type') or '').upper()
            title = {
                'OP': 'Outpatient visit',
                'LAB': 'Lab visit',
                'PHARMACY': 'Pharmacy visit',
            }.get(visit_type, f'{visit_type} visit' if visit_type else 'Visit')
            doctor_part = f" with {visit['doctor_name']}" if visit.get('doctor_name') else ''
            notes = visit.get('notes') or 'Patient interaction recorded.'
            items.append({
                'type': 'Visit',
                'title': title,
                'description': f"{notes}{doctor_part}",
                'date': visit.get('visit_date'),
                'status': visit_type or None,
                'color': 'slate',
                'filter_key': 'all',
            })

        for rx in prescriptions:
            med_names = ', '.join([m.get('name') or '' for m in rx.get('medicines', []) if (m.get('name') or '').strip()])
            desc_parts = []
            if rx.get('diagnosis'):
                desc_parts.append(f"Diagnosis: {rx['diagnosis']}")
            if med_names:
                desc_parts.append(f"Medicines: {med_names}")
            if rx.get('doctor_name'):
                desc_parts.append(f"Prescribed by {rx['doctor_name']}")
            items.append({
                'type': 'Prescription',
                'title': rx.get('diagnosis') or 'Prescription issued',
                'description': ' | '.join(desc_parts) or 'Prescription created.',
                'date': rx.get('prescribed_at'),
                'status': 'Active',
                'color': 'green',
                'filter_key': 'medicines',
            })

        for order in lab_orders:
            doctor_name = order.get('doctor_name')
            by_doctor = f" by {doctor_name}" if doctor_name else ''
            items.append({
                'type': 'Lab',
                'title': order.get('test_name') or 'Lab order',
                'description': f"Lab test ordered{by_doctor}",
                'date': order.get('created_at'),
                'status': order.get('status'),
                'color': 'blue',
                'filter_key': 'lab',
            })

        for report in lab_reports:
            file_path = report.get('file_path')
            suffix = f" File: {file_path}" if file_path else ' Report uploaded.'
            items.append({
                'type': 'Lab',
                'title': f"{report.get('test_name') or 'Lab report'} report",
                'description': f"Lab report available.{suffix}",
                'date': report.get('created_at'),
                'status': report.get('status') or 'Completed',
                'color': 'blue',
                'filter_key': 'lab',
            })

        for sale in pharmacy:
            notes = sale.get('dosage') or sale.get('notes') or 'Medicine supplied to patient.'
            items.append({
                'type': 'Pharmacy',
                'title': sale.get('medicine_name') or 'Medicine sold',
                'description': f"Qty {sale.get('quantity') or 1}. {notes}",
                'date': sale.get('sold_at') or sale.get('created_at'),
                'status': sale.get('status'),
                'color': 'orange',
                'filter_key': 'medicines',
            })

        items.sort(
            key=lambda entry: cls._sort_key(entry.get('date')),
            reverse=True,
        )
        return items[:cls.MAX_LIMIT]

    @classmethod
    def _previously_used_medicines(cls, pharmacy, prescriptions):
        counts = Counter()
        for row in pharmacy:
            name = (row.get('medicine_name') or '').strip()
            if name:
                counts[name] += 2
        for rx in prescriptions:
            for med in rx.get('medicines', []):
                name = (med.get('name') or '').strip()
                if name:
                    counts[name] += 1
        return [name for name, _ in counts.most_common(10)]

    @staticmethod
    def _parse_legacy_medicines(raw_value):
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                out = []
                for item in parsed:
                    if isinstance(item, dict):
                        out.append({
                            'name': item.get('medicine_name') or item.get('name') or '',
                            'dosage': item.get('dosage'),
                            'frequency': item.get('frequency'),
                            'duration': item.get('duration'),
                            'instruction': item.get('instruction'),
                        })
                    elif isinstance(item, str):
                        out.append({'name': item})
                return out
        except (TypeError, json.JSONDecodeError):
            pass
        return [{'name': part.strip()} for part in str(raw_value).split(',') if part.strip()]

    @staticmethod
    def _normalize_lab_status(status):
        mapping = {
            'CREATED': 'Ordered',
            'PENDING': 'Ordered',
            'SAMPLE_COLLECTED': 'Collected',
            'PROCESSING': 'Processing',
            'COMPLETED': 'Completed',
        }
        return mapping.get((status or '').upper(), status)

    @staticmethod
    def _iso(value):
        if not value:
            return None
        if isinstance(value, str):
            return value
        return value.isoformat()

    @staticmethod
    def _sort_key(value):
        if not value:
            return datetime.min
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return datetime.min
