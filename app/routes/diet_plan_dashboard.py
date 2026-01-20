"""
Smart Diet Plan Patient Portal Integration Routes
Handles the display and interaction of the diet plan feature in patient dashboard
"""

from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import json

from app.models.models import db, ClinicalDietPlan, Patient, UserRole

diet_plan_dashboard_bp = Blueprint('diet_plan_dashboard', __name__, url_prefix='/patient/dashboard')

@diet_plan_dashboard_bp.route('/diet-plan-card', methods=['GET'])
@login_required
def get_diet_plan_card():
    """
    Return the Smart Diet Plan card component for patient dashboard
    Shows card with status and access to personalized diet plan
    """
    if current_user.role != UserRole.PATIENT:
        return jsonify({'status': 'error', 'message': 'Patient access only'}), 403
    
    try:
        patient = current_user.patient
        
        # Check if patient has an active diet plan
        diet_plan = ClinicalDietPlan.query.filter_by(
            patient_id=patient.id,
            is_active=True
        ).first()
        
        card_data = {
            'has_diet_plan': bool(diet_plan),
            'patient_id': patient.id,
            'status': 'Plan Available Now' if diet_plan else 'No Plan Yet'
        }
        
        if diet_plan:
            card_data['generated_date'] = diet_plan.generated_at.strftime('%B %d, %Y')
            card_data['next_review'] = diet_plan.next_review_date.strftime('%B %d, %Y') if diet_plan.next_review_date else 'TBD'
        
        return render_template('patient_dashboard_diet_card.html', **card_data)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering diet plan card: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error loading diet plan card'}), 500


@diet_plan_dashboard_bp.route('/diet-plan-status', methods=['GET'])
@login_required
def get_diet_plan_status():
    """
    Get the current status of patient's diet plan
    Used for checking if plan exists and displaying appropriate UI
    """
    if current_user.role != UserRole.PATIENT:
        return jsonify({'status': 'error', 'message': 'Patient access only'}), 403
    
    try:
        patient = current_user.patient
        diet_plan = ClinicalDietPlan.query.filter_by(
            patient_id=patient.id,
            is_active=True
        ).first()
        
        return jsonify({
            'status': 'success',
            'has_plan': bool(diet_plan),
            'plan_data': {
                'id': diet_plan.id,
                'generated_at': diet_plan.generated_at.isoformat(),
                'next_review_date': diet_plan.next_review_date.isoformat() if diet_plan.next_review_date else None,
                'is_active': diet_plan.is_active
            } if diet_plan else None
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error checking diet plan status: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error checking diet plan status'}), 500


@diet_plan_dashboard_bp.route('/diet-plan-quick-info', methods=['GET'])
@login_required
def get_quick_info():
    """
    Get quick information about patient's diet plan
    Used for mini display cards and quick stats
    """
    if current_user.role != UserRole.PATIENT:
        return jsonify({'status': 'error', 'message': 'Patient access only'}), 403
    
    try:
        patient = current_user.patient
        diet_plan = ClinicalDietPlan.query.filter_by(
            patient_id=patient.id,
            is_active=True
        ).first()
        
        if not diet_plan:
            return jsonify({
                'status': 'success',
                'has_plan': False,
                'message': 'No active diet plan found'
            }), 200
        
        return jsonify({
            'status': 'success',
            'has_plan': True,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'diet_type': diet_plan.diet_type,
            'bmi': round(diet_plan.bmi, 1),
            'caloric_target': diet_plan.caloric_target_weight_loss,
            'medical_conditions': json.loads(diet_plan.medical_conditions),
            'generated_at': diet_plan.generated_at.isoformat(),
            'days_since_generated': (datetime.now() - diet_plan.generated_at).days
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting quick info: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error getting quick info'}), 500
