from flask_socketio import SocketIO, emit
from flask_login import current_user
from flask import request

# Global SocketIO instance
socketio = SocketIO(cors_allowed_origins="*")

# Simple mapping of user_id to socket session id
# Format: {1: "abcd123...", 2: "efgh456..."}
connected_clients = {}

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        connected_clients[current_user.id] = request.sid
        print(f"[Socket] Client connected: UID {current_user.id} - SID {request.sid}")
    else:
        print("[Socket] Unauthenticated client connected")

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        if current_user.id in connected_clients:
            del connected_clients[current_user.id]
        print(f"[Socket] Client disconnected: UID {current_user.id}")

@socketio.on('typing')
def handle_typing(data):
    """Forward typing indicator to the other party"""
    if not current_user.is_authenticated:
        return
    
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')
    sender_type = data.get('sender_type')
    
    if not patient_id or not doctor_id or not sender_type:
        return
    
    try:
        from app.models.models import Patient, Doctor, User
        
        if sender_type == 'patient':
            # Patient is typing -> forward to doctor
            doctor_user = User.query.filter_by(role='doctor').join(Doctor).filter(Doctor.id == doctor_id).first()
            if doctor_user:
                emit_to_user(doctor_user.id, 'typing', data)
        elif sender_type == 'doctor':
            # Doctor is typing -> forward to patient
            patient_obj = Patient.query.get(patient_id)
            if patient_obj and patient_obj.user:
                emit_to_user(patient_obj.user.id, 'typing', data)
    except Exception as e:
        print(f"[Socket] Typing relay error: {e}")

@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read and notify sender"""
    if not current_user.is_authenticated:
        return
    try:
        from app.models.models import Message, Patient, Doctor, User
        from app import db
        
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        reader_type = data.get('reader_type')  # 'patient' or 'doctor'
        
        if not patient_id or not doctor_id or not reader_type:
            return
        
        # Mark messages from the other party as read
        sender_type = 'doctor' if reader_type == 'patient' else 'patient'
        unread = Message.query.filter_by(
            patient_id=patient_id, doctor_id=doctor_id,
            sender_type=sender_type, is_read=False
        ).all()
        
        for msg in unread:
            msg.is_read = True
        db.session.commit()
        
        # Notify sender that their messages were read
        if sender_type == 'doctor':
            doctor_user = User.query.filter_by(role='doctor').join(Doctor).filter(Doctor.id == doctor_id).first()
            if doctor_user:
                emit_to_user(doctor_user.id, 'messages_read', {
                    'patient_id': patient_id,
                    'doctor_id': doctor_id,
                    'reader_type': reader_type
                })
        else:
            patient_obj = Patient.query.get(patient_id)
            if patient_obj and patient_obj.user:
                emit_to_user(patient_obj.user.id, 'messages_read', {
                    'patient_id': patient_id,
                    'doctor_id': doctor_id,
                    'reader_type': reader_type
                })
    except Exception as e:
        print(f"[Socket] Mark read error: {e}")

def emit_to_user(user_id, event_name, data):
    """Utility function to emit a socket event to a specific user if they are online"""
    sid = connected_clients.get(int(user_id))
    if sid:
        socketio.emit(event_name, data, room=sid)
        print(f"[Socket] Emitted '{event_name}' to user {user_id}")
    else:
        print(f"[Socket] User {user_id} not connected, skipping emit")
