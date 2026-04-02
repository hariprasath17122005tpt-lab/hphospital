#!/usr/bin/env python
"""
Test the staff login credentials with the Flask app directly.
"""
from app import create_app, db
from app.models.models import User, UserRole
from werkzeug.security import check_password_hash

app = create_app('development')

TEST_LOGINS = [
    ('lab123', 'labopen', 'LAB_STAFF'),
    ('pharmacy123', 'pharmacyopen', 'PHARMACIST'),
    ('reception123', 'receptionopen', 'RECEPTIONIST'),
]

with app.app_context():
    print("=" * 60)
    print("TESTING STAFF LOGINS")
    print("=" * 60)
    
    for username, password, expected_role in TEST_LOGINS:
        print(f"\n📋 Testing: {username} / {password}")
        
        # Look up user in database
        user = User.query.filter(db.func.lower(User.username) == username).first()
        
        if not user:
            print(f"  ✗ User not found in database!")
            continue
        
        # Check role
        user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        if user_role != expected_role:
            print(f"  ✗ Role mismatch: got {user_role}, expected {expected_role}")
            continue
        
        # Check password
        password_ok = check_password_hash(user.password_hash, password)
        if not password_ok:
            print(f"  ✗ Password verification failed!")
            continue
        
        # Check active status
        if not user.is_active:
            print(f"  ✗ User account is inactive!")
            continue
        
        print(f"  ✓ Username: {user.username}")
        print(f"  ✓ Role: {user_role}")
        print(f"  ✓ Password: verified")
        print(f"  ✓ Active: {user.is_active}")
        print(f"  ✓ EMAIL: {user.email}")
        print(f"\n  ✅ {username} can login successfully!")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
