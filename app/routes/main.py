from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page with Doctor/Patient selection"""
    # Always show home page - let users navigate via navbar
    # Don't redirect authenticated users to prevent session issues
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@main_bp.route('/api/health-status', methods=['GET'])
@login_required
def api_health_status():
    """API endpoint for health status"""
    return jsonify({'status': 'ok', 'user': current_user.username})
