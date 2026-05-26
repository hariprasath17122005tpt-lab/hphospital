"""Health Tools Module - BMI Calculator, Risk Assessors, Health Tips"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

health_tools_bp = Blueprint('health_tools', __name__, url_prefix='/health-tools')


@health_tools_bp.route('/')
def index():
    """Public health tools page."""
    return render_template('health_tools/index.html')


@health_tools_bp.route('/bmi-calculator')
def bmi_calculator():
    """BMI Calculator page."""
    return render_template('health_tools/bmi_calculator.html')


@health_tools_bp.route('/api/calculate-bmi', methods=['POST'])
def calculate_bmi():
    data = request.get_json(silent=True) or {}
    weight = data.get('weight', 0)
    height_cm = data.get('height', 0)

    if not weight or not height_cm or height_cm <= 0:
        return jsonify({'success': False, 'error': 'Invalid input'})

    height_m = height_cm / 100
    bmi = round(weight / (height_m ** 2), 1)

    if bmi < 18.5:
        category = 'Underweight'
        color = '#3b82f6'
        advice = 'You may need to gain weight. Consult a nutritionist for a balanced diet plan.'
    elif bmi < 25:
        category = 'Normal'
        color = '#10b981'
        advice = 'Great! You have a healthy weight. Maintain it with regular exercise and balanced nutrition.'
    elif bmi < 30:
        category = 'Overweight'
        color = '#f59e0b'
        advice = 'Consider lifestyle changes including regular exercise and dietary improvements.'
    else:
        category = 'Obese'
        color = '#ef4444'
        advice = 'Please consult a doctor for a weight management plan. Regular monitoring recommended.'

    ideal_min = round(18.5 * (height_m ** 2), 1)
    ideal_max = round(24.9 * (height_m ** 2), 1)

    return jsonify({
        'success': True,
        'bmi': bmi,
        'category': category,
        'color': color,
        'advice': advice,
        'ideal_weight_range': f'{ideal_min} - {ideal_max} kg',
        'height_m': round(height_m, 2)
    })


@health_tools_bp.route('/api/heart-risk', methods=['POST'])
def heart_risk():
    """Simple heart risk calculator."""
    data = request.get_json(silent=True) or {}
    age = data.get('age', 30)
    systolic = data.get('systolic', 120)
    cholesterol = data.get('cholesterol', 200)
    smoker = data.get('smoker', False)
    diabetic = data.get('diabetic', False)

    risk_score = 0
    if age > 45: risk_score += 2
    if age > 55: risk_score += 2
    if age > 65: risk_score += 3
    if systolic > 140: risk_score += 3
    elif systolic > 130: risk_score += 1
    if cholesterol > 240: risk_score += 3
    elif cholesterol > 200: risk_score += 1
    if smoker: risk_score += 4
    if diabetic: risk_score += 3

    if risk_score <= 3:
        level = 'Low'
        color = '#10b981'
    elif risk_score <= 7:
        level = 'Moderate'
        color = '#f59e0b'
    elif risk_score <= 12:
        level = 'High'
        color = '#ef4444'
    else:
        level = 'Very High'
        color = '#991b1b'

    return jsonify({
        'success': True,
        'risk_score': risk_score,
        'risk_level': level,
        'color': color,
        'max_score': 18
    })
