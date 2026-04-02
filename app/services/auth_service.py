"""
Advanced Authentication Service
Enterprise-grade security utilities for login, password reset, and account protection
"""

from datetime import datetime, timedelta
from user_agents import parse as parse_user_agent
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, current_app
import secrets
import re

from app.models.models import db, User, UserRole, Patient, Doctor, Hospital
from app.services.patient_service import PatientService
from app.models.auth_models import (
    LoginAttempt, AccountLock, PasswordResetToken, 
    UserSession, LoginActivity, OAuthAccount
)


class AuthService:
    """
    Enterprise Authentication Service
    Handles login attempts, account locking, password reset, and activity logging
    """
    
    # Configuration
    MAX_FAILED_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 15
    PASSWORD_RESET_EXPIRES_MINUTES = 15
    REMEMBER_ME_DAYS = 30
    SESSION_TIMEOUT_HOURS = 24
    
    @staticmethod
    def get_client_info():
        """Extract client information from request"""
        user_agent_string = request.headers.get('User-Agent', '')
        ua = parse_user_agent(user_agent_string)
        
        # Determine device type
        if ua.is_mobile:
            device_type = 'mobile'
        elif ua.is_tablet:
            device_type = 'tablet'
        else:
            device_type = 'desktop'
        
        return {
            'ip_address': request.remote_addr or request.headers.get('X-Forwarded-For', '0.0.0.0'),
            'device_type': device_type,
            'browser': f"{ua.browser.family} {ua.browser.version_string}",
            'os': f"{ua.os.family} {ua.os.version_string}",
            'user_agent': user_agent_string[:500]  # Limit length
        }
    
    @classmethod
    def check_account_lock(cls, email_or_username):
        """Check if account is locked"""
        lock = AccountLock.query.filter_by(email_or_username=email_or_username).first()
        if lock and lock.is_currently_locked:
            return {
                'is_locked': True,
                'minutes_remaining': lock.minutes_until_unlock,
                'reason': lock.lock_reason,
                'is_permanent': lock.is_permanently_locked
            }
        return {'is_locked': False}
    
    @classmethod
    def record_failed_attempt(cls, email_or_username, reason='invalid_password', role=None):
        """Record a failed login attempt and lock account if needed"""
        client_info = cls.get_client_info()
        
        # Record the attempt
        attempt = LoginAttempt(
            email_or_username=email_or_username,
            ip_address=client_info['ip_address'],
            device_type=client_info['device_type'],
            user_agent=client_info['user_agent'],
            was_successful=False,
            failure_reason=reason,
            role_attempted=role
        )
        db.session.add(attempt)
        
        # Update or create lock record
        lock = AccountLock.query.filter_by(email_or_username=email_or_username).first()
        if not lock:
            lock = AccountLock(email_or_username=email_or_username, failed_attempts=0)
            db.session.add(lock)
        
        lock.failed_attempts += 1
        lock.last_attempt_ip = client_info['ip_address']
        
        # Lock account if max attempts reached
        if lock.failed_attempts >= cls.MAX_FAILED_ATTEMPTS:
            lock.locked_at = datetime.utcnow()
            lock.lock_expires_at = datetime.utcnow() + timedelta(minutes=cls.LOCK_DURATION_MINUTES)
            lock.lock_reason = 'too_many_failed_attempts'
        
        db.session.commit()
        
        return {
            'attempts_remaining': max(0, cls.MAX_FAILED_ATTEMPTS - lock.failed_attempts),
            'is_locked': lock.is_currently_locked,
            'lock_duration': cls.LOCK_DURATION_MINUTES if lock.is_currently_locked else 0
        }
    
    @classmethod
    def record_successful_login(cls, user, login_method='password', remember_me=False):
        """Record a successful login"""
        client_info = cls.get_client_info()
        
        # Record successful attempt
        attempt = LoginAttempt(
            email_or_username=user.email,
            ip_address=client_info['ip_address'],
            device_type=client_info['device_type'],
            user_agent=client_info['user_agent'],
            was_successful=True,
            role_attempted=user.role.value.lower() if user.role else None
        )
        db.session.add(attempt)
        
        # Clear any existing lock
        lock = AccountLock.query.filter_by(email_or_username=user.email).first()
        if lock:
            lock.failed_attempts = 0
            lock.locked_at = None
            lock.lock_expires_at = None
        
        # Record login activity
        activity = LoginActivity(
            user_id=user.id,
            ip_address=client_info['ip_address'],
            device_type=client_info['device_type'],
            browser=client_info['browser'],
            os=client_info['os'],
            user_agent=client_info['user_agent'],
            login_method=login_method,
            is_suspicious=cls._check_suspicious_activity(user, client_info)
        )
        db.session.add(activity)
        db.session.commit()
        
        return activity
    
    @classmethod
    def _check_suspicious_activity(cls, user, client_info):
        """Check for suspicious login patterns"""
        # Get last successful login
        last_login = LoginActivity.query.filter_by(
            user_id=user.id
        ).order_by(LoginActivity.login_time.desc()).first()
        
        if last_login:
            # Check for new IP address
            if last_login.ip_address != client_info['ip_address']:
                return True
            # Check for new device type
            if last_login.device_type != client_info['device_type']:
                return True
        
        return False
    
    @classmethod
    def create_password_reset_token(cls, user):
        """Create a secure password reset token"""
        client_info = cls.get_client_info()
        
        # Invalidate any existing tokens
        PasswordResetToken.query.filter_by(
            user_id=user.id, 
            is_used=False
        ).update({'is_used': True})
        
        # Create new token
        raw_token, token_record = PasswordResetToken.create_token(
            user_id=user.id,
            ip_address=client_info['ip_address'],
            expires_in_minutes=cls.PASSWORD_RESET_EXPIRES_MINUTES
        )
        db.session.add(token_record)
        db.session.commit()
        
        return raw_token
    
    @classmethod
    def verify_password_reset_token(cls, token):
        """Verify a password reset token"""
        token_hash = PasswordResetToken.hash_token(token)
        token_record = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
        
        if not token_record:
            return None, 'Invalid reset link'
        if token_record.is_used:
            return None, 'This reset link has already been used'
        if datetime.utcnow() > token_record.expires_at:
            return None, 'This reset link has expired'
        
        return token_record, None
    
    @classmethod
    def reset_password(cls, token, new_password):
        """Reset user password using token"""
        token_record, error = cls.verify_password_reset_token(token)
        if error:
            return False, error
        
        # Update user password
        user = User.query.get(token_record.user_id)
        if not user:
            return False, 'User not found'
        
        user.password_hash = generate_password_hash(new_password)
        token_record.is_used = True
        token_record.used_at = datetime.utcnow()
        db.session.commit()
        
        return True, 'Password reset successfully'
    
    @classmethod
    def validate_password_strength(cls, password):
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('Password must contain at least one special character')
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_login_activity(cls, user_id=None, limit=50):
        """Get login activity for admin monitoring"""
        query = LoginActivity.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(LoginActivity.login_time.desc()).limit(limit).all()
    
    @classmethod
    def get_suspicious_activities(cls, limit=100):
        """Get suspicious login activities for admin review"""
        return LoginActivity.query.filter_by(
            is_suspicious=True
        ).order_by(LoginActivity.login_time.desc()).limit(limit).all()
    
    @classmethod
    def find_or_create_oauth_user(cls, provider, provider_user_id, email, name, role_value):
        """Find or create user from OAuth provider"""
        # Check if OAuth account exists
        oauth = OAuthAccount.query.filter_by(
            provider=provider,
            provider_user_id=provider_user_id
        ).first()
        
        if oauth:
            return oauth.user, False  # Existing user
        
        # Check if user with email exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            role = UserRole(role_value.upper())
            
            # Get default hospital
            default_hospital = Hospital.query.first()
            
            user = User(
                username=email.split('@')[0] + '_' + secrets.token_hex(4),
                email=email,
                password_hash=generate_password_hash(secrets.token_urlsafe(32)),  # Random password
                role=role,
                hospital_id=default_hospital.id if default_hospital else None
            )
            db.session.add(user)
            db.session.flush()
            
            # Create role-specific profile
            if role == UserRole.PATIENT:
                name_parts = name.split(' ', 1)
                patient = Patient(
                    user_id=user.id,
                    uhid=PatientService.generate_uhid(),
                    hospital_id=default_hospital.id if default_hospital else None,
                    first_name=name_parts[0],
                    last_name=name_parts[1] if len(name_parts) > 1 else '',
                    age=0,  # To be updated later
                    gender='Not Specified'
                )
                db.session.add(patient)
        
        # Create OAuth account link
        oauth = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            name=name
        )
        db.session.add(oauth)
        db.session.commit()
        
        return user, True  # New user
