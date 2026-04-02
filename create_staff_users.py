#!/usr/bin/env python
"""
Create the pharmacy123 and reception123 staff users if they don't exist.
"""
from app import create_app, db
from app.models.models import User, UserRole, Hospital
from werkzeug.security import generate_password_hash

app = create_app('development')

STAFF_ACCOUNTS = [
    {
        'username': 'lab123',
        'password': 'labopen',
        'role': UserRole.LAB_STAFF,
        'email': 'lab123@staff.system'
    },
    {
        'username': 'pharmacy123',
        'password': 'pharmacyopen',
        'role': UserRole.PHARMACIST,
        'email': 'pharmacy123@staff.system'
    },
    {
        'username': 'reception123',
        'password': 'receptionopen',
        'role': UserRole.RECEPTIONIST,
        'email': 'reception123@staff.system'
    },
]

with app.app_context():
    # Get default hospital
    default_hospital = Hospital.query.first()
    if not default_hospital:
        print("❌ ERROR: No hospital found in database!")
        exit(1)

    hospital_id = default_hospital.id

    for account in STAFF_ACCOUNTS:
        username = account['username']
        # Check if user exists
        user = User.query.filter(db.func.lower(User.username) == username).first()

        if user:
            print(f"✓ User '{username}' already exists with role {user.role}")
            # Update the password and role to match master keys
            user.password_hash = generate_password_hash(account['password'])
            user.role = account['role']
            user.is_active = True
            db.session.commit()
            print(f"  Updated password and role")
        else:
            # Create new user
            new_user = User(
                username=username,
                email=account['email'],
                password_hash=generate_password_hash(account['password']),
                role=account['role'],
                hospital_id=hospital_id,
                is_active=True
            )
            db.session.add(new_user)
            print(f"📝 Created new user: {username}")

    db.session.commit()
    print("\n✅ All staff users are ready!")

    # Verify all staff users exist
    print("\n=== VERIFICATION ===")
    for account in STAFF_ACCOUNTS:
        user = User.query.filter(db.func.lower(User.username) == account['username']).first()
        if user:
            print(f"✓ {user.username}: role={user.role.value}, active={user.is_active}")
        else:
            print(f"✗ {account['username']}: NOT FOUND")
