"""
Advanced Authentication Models for Hospital Management System
Enterprise-grade security with login tracking, account protection, and OAuth support
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets
import hashlib

from app.models.models import db


class LoginAttempt(db.Model):
    """Track login attempts for security monitoring and brute force protection"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    email_or_username = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(50))
    device_type = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    attempt_time = db.Column(db.DateTime, default=datetime.utcnow)
    was_successful = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(100))  # 'invalid_password', 'no_user', 'locked', etc.
    role_attempted = db.Column(db.String(20))  # 'patient', 'doctor', 'admin'
    
    def __repr__(self):
        return f'<LoginAttempt {self.email_or_username} at {self.attempt_time}>'


class AccountLock(db.Model):
    """Account lock records for brute force protection"""
    __tablename__ = 'account_locks'
    
    id = db.Column(db.Integer, primary_key=True)
    email_or_username = db.Column(db.String(120), nullable=False, unique=True, index=True)
    lock_reason = db.Column(db.String(100), default='too_many_failed_attempts')
    failed_attempts = db.Column(db.Integer, default=0)
    locked_at = db.Column(db.DateTime)
    lock_expires_at = db.Column(db.DateTime)
    is_permanently_locked = db.Column(db.Boolean, default=False)
    last_attempt_ip = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_currently_locked(self):
        """Check if account is currently locked"""
        if self.is_permanently_locked:
            return True
        if self.locked_at and self.lock_expires_at:
            return datetime.utcnow() < self.lock_expires_at
        return False
    
    @property
    def minutes_until_unlock(self):
        """Get minutes until lock expires"""
        if not self.is_currently_locked or self.is_permanently_locked:
            return 0
        remaining = self.lock_expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))
    
    def __repr__(self):
        return f'<AccountLock {self.email_or_username} locked={self.is_currently_locked}>'


class PasswordResetToken(db.Model):
    """Secure password reset tokens"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_token(token):
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @property
    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    @classmethod
    def create_token(cls, user_id, ip_address=None, expires_in_minutes=15):
        """Create a new password reset token"""
        raw_token = cls.generate_token()
        token_record = cls(
            user_id=user_id,
            token_hash=cls.hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            ip_address=ip_address
        )
        return raw_token, token_record
    
    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id} valid={self.is_valid}>'


class UserSession(db.Model):
    """User session tracking for 'Remember Me' and session management"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    device_type = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    is_remember_me = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    @staticmethod
    def generate_session_token():
        """Generate secure session token"""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def hash_token(token):
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @property
    def is_valid(self):
        """Check if session is valid"""
        return self.is_active and datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f'<UserSession user_id={self.user_id} active={self.is_active}>'


class LoginActivity(db.Model):
    """Detailed login activity log for admin monitoring"""
    __tablename__ = 'login_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    logout_time = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))
    device_type = db.Column(db.String(100))  # desktop, mobile, tablet
    browser = db.Column(db.String(100))
    os = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    location_country = db.Column(db.String(100))
    location_city = db.Column(db.String(100))
    login_method = db.Column(db.String(50))  # 'password', 'google', 'remember_me'
    is_suspicious = db.Column(db.Boolean, default=False)
    suspicious_reason = db.Column(db.String(200))
    
    # Relationship
    user = db.relationship('User', backref='login_activities')
    
    def __repr__(self):
        return f'<LoginActivity user_id={self.user_id} at {self.login_time}>'


class OAuthAccount(db.Model):
    """OAuth provider accounts (Google, etc.)"""
    __tablename__ = 'oauth_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'google', 'facebook', etc.
    provider_user_id = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    name = db.Column(db.String(200))
    profile_picture = db.Column(db.String(500))
    access_token = db.Column(db.Text)  # Encrypted storage recommended
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for provider + provider_user_id
    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='unique_oauth_account'),
    )
    
    # Relationship
    user = db.relationship('User', backref='oauth_accounts')
    
    def __repr__(self):
        return f'<OAuthAccount {self.provider} user_id={self.user_id}>'
