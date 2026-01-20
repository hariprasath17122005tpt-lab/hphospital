from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config
from app.models.models import db, User

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.patient_login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    @app.context_processor
    def inject_system_settings():
        from app.models.models import SystemSettings
        settings = SystemSettings.query.first()
        return dict(system_settings=settings)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.features import features_bp
    from app.routes.ai_chatbot import ai_bp
    from app.routes.diet_plan import diet_plan_bp
    from app.routes.diet_plan_dashboard import diet_plan_dashboard_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(features_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(diet_plan_bp)

    app.register_blueprint(diet_plan_dashboard_bp)

    from app.routes.host import host_bp
    app.register_blueprint(host_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app
