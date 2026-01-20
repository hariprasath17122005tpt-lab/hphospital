import logging
from datetime import datetime
from flask import current_app

# Configure logger for notifications
handler = logging.FileHandler('notifications.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger('notifications')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

class NotificationService:
    """
    Service to handle sending notifications via Email and SMS.
    Currently simulates sending by logging to a file, but designed to
    be easily extended with real SMTP/Twilio providers.
    """

    @staticmethod
    def send_email(to_email, subject, body):
        """
        Send an email notification.
        """
        try:
            # In a real app, use Flask-Mail here
            # msg = Message(subject, recipients=[to_email], body=body)
            # mail.send(msg)
            
            # Simulation
            log_message = f"EMAIL SENT | To: {to_email} | Subject: {subject} | Body: {body}"
            logger.info(log_message)
            print(f"[{datetime.now()}] {log_message}") # Print to console for dev visibility
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def send_sms(phone_number, message):
        """
        Send an SMS notification.
        """
        try:
            # In a real app, use Twilio here
            # client.messages.create(body=message, from_=sender, to=phone_number)
            
            # Simulation
            log_message = f"SMS SENT | To: {phone_number} | Message: {message}"
            logger.info(log_message)
            print(f"[{datetime.now()}] {log_message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return False

    @staticmethod
    def send_appointment_confirmation(patient, doctor, appointment):
        """
        Send confirmation details to patient.
        """
        subject = f"Appointment Confirmed - {appointment.appointment_date.strftime('%Y-%m-%d')}"
        
        email_body = f"""
        Dear {patient.first_name},
        
        Your appointment with Dr. {doctor.first_name} {doctor.last_name} ({doctor.specialization}) has been confirmed.
        
        Date: {appointment.appointment_date.strftime('%Y-%m-%d')}
        Time: {appointment.appointment_date.strftime('%H:%M')}
        Location: {doctor.hospital.name if doctor.hospital else 'Main Hospital'}, {doctor.clinic_address or 'General Wing'}
        
        Please arrive 10 minutes early.
        
        Regards,
        Hospital Management System
        """
        
        sms_body = f"Appt Confirmed: Dr. {doctor.last_name} on {appointment.appointment_date.strftime('%Y-%m-%d @ %H:%M')}. Pls arrive early."
        
        NotificationService.send_email(patient.user.email, subject, email_body)
        if patient.phone:
            NotificationService.send_sms(patient.phone, sms_body)

    @staticmethod
    def send_appointment_request_acknowledgement(patient, doctor, appointment):
        """
        Send acknowledgement to patient for new request.
        """
        subject = f"Appointment Request Received - {appointment.appointment_date.strftime('%Y-%m-%d')}"
        
        email_body = f"""
        Dear {patient.first_name},
        
        We have received your appointment request for Dr. {doctor.last_name} on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}.
        
        Status: PENDING APPROVAL
        
        You will receive another notification once the doctor approves the request.
        
        Regards,
        Hospital Management System
        """
        
        NotificationService.send_email(patient.user.email, subject, email_body)

    @staticmethod
    def send_appointment_status_update(patient, doctor, appointment, status):
        """
        Send approval/rejection notification.
        """
        subject = f"Appointment Update - Status: {status.upper()}"
        
        email_body = f"""
        Dear {patient.first_name},
        
        Your appointment with Dr. {doctor.last_name} on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')} has been {status.upper()}.
        
        {'We look forward to seeing you.' if status == 'confirmed' else 'Please contact us to reschedule.'}
        
        Regards,
        Hospital Admin
        """
        
        sms_body = f"Appt Update: Dr. {doctor.last_name} encounter is now {status.upper()}."
        
        NotificationService.send_email(patient.user.email, subject, email_body)
        if patient.phone:
            NotificationService.send_sms(patient.phone, sms_body)
