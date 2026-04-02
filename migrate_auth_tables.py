"""
Database Migration Script for Advanced Authentication System
Adds new tables for login tracking, account locking, password reset, and OAuth

Run this script once to add the new authentication tables:
    python migrate_auth_tables.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.models import db

def migrate_auth_tables():
    """Create new authentication tables"""
    print("=" * 60)
    print("Advanced Authentication System - Database Migration")
    print("=" * 60)
    
    app = create_app('development')
    
    with app.app_context():
        # Import auth models to register them with SQLAlchemy
        try:
            from app.models.auth_models import (
                LoginAttempt, AccountLock, PasswordResetToken,
                UserSession, LoginActivity, OAuthAccount
            )
            print("\n✓ Auth models imported successfully")
        except ImportError as e:
            print(f"\n✗ Error importing auth models: {e}")
            return False
        
        # Create all tables
        print("\nCreating database tables...")
        db.create_all()
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        auth_tables = [
            'login_attempts',
            'account_locks', 
            'password_reset_tokens',
            'user_sessions',
            'login_activity',
            'oauth_accounts'
        ]
        
        print("\nVerifying new tables:")
        all_created = True
        for table in auth_tables:
            if table in tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (not found)")
                all_created = False
        
        if all_created:
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("  All authentication tables have been created.")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("⚠ Migration partially completed.")
            print("  Some tables may not have been created.")
            print("=" * 60)
            return False


if __name__ == '__main__':
    success = migrate_auth_tables()
    sys.exit(0 if success else 1)
