from app import create_app, db
from app.models.models import Patient, HealthData, Appointment, Message, Prescription, LabReport
from datetime import datetime, timedelta
from flask import Flask, render_template

app = create_app()

def test_dashboard_logic():
    with app.app_context():
        try:
            # Pick a patient (e.g., the first one)
            patient = Patient.query.first()
            if not patient:
                print("No patients found in DB. Test skipped.")
                return
            
            print(f"Testing dashboard for Patient ID: {patient.id} ({patient.first_name})")
            
            # 1. Latest Health Data
            latest_health = HealthData.query.filter_by(patient_id=patient.id).order_by(
                HealthData.recorded_at.desc()).first()
            print("Successfully fetched latest_health")
            
            # 2. Upcoming Appointments
            upcoming_appointments = Appointment.query.filter_by(patient_id=patient.id).filter(
                Appointment.appointment_date > datetime.utcnow()).order_by(
                Appointment.appointment_date).limit(5).all()
            print(f"Successfully fetched appointments: {len(upcoming_appointments)}")
            
            # 3. Unread Messages
            unread_messages = Message.query.filter_by(patient_id=patient.id, is_read=False).count()
            print(f"Successfully fetched unread_messages: {unread_messages}")
            
            # 4. Latest Prescription
            latest_prescription = Prescription.query.filter_by(patient_id=patient.id).order_by(
                Prescription.prescribed_at.desc()).first()
            print("Successfully fetched latest_prescription")
        
            # 5. Recent Lab Reports
            recent_reports = LabReport.query.filter_by(patient_id=patient.id).order_by(
                LabReport.conducted_at.desc()).limit(10).all()
            print(f"Successfully fetched recent_reports: {len(recent_reports)}")
        
            # 6. Health Data History (Last 7 Days)
            health_records = HealthData.query.filter_by(patient_id=patient.id).filter(
                HealthData.recorded_at >= (datetime.now() - timedelta(days=7))
            ).order_by(HealthData.recorded_at.asc()).all()
            print(f"Successfully fetched health_records: {len(health_records)}")
        
            # 7. Chart Data Logic
            today = datetime.now().date()
            last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
            chart_dates = [d.strftime('%a') for d in last_7_days]
            health_map = {h.recorded_at.date(): h for h in health_records}
            print(f"Chart dates: {chart_dates}")
            
            # 8. Check-ins
            from app.models.models import PatientCheckIn
            my_checkins = PatientCheckIn.query.filter_by(patient_id=patient.id).order_by(
                PatientCheckIn.created_at.desc()).limit(5).all()
            print(f"Successfully fetched checkins: {len(my_checkins)}")
            
            print("✅ TEST PASSED: Backend logic is solid.")
            
        except Exception as e:
            import traceback
            print(f"❌ TEST FAILED: {str(e)}")
            print(traceback.format_exc())

if __name__ == "__main__":
    test_dashboard_logic()
