#!/usr/bin/env python
"""Debug lab dashboard error"""
import os
import sys
from app import create_app
from app.models.models import User, UserRole

# Create app
app = create_app('development')

# Simulate lab staff user login
with app.test_client() as client:
    with app.app_context():
        # Try to access dashboard
        print("Testing /lab/dashboard access...")
        
        # Get the login page first
        resp = client.get('/staff/login')
        print(f"Login page: {resp.status_code}")
        
        # Try to POST lab login credentials
        print("\nAttempting lab staff login...")
        resp = client.post('/staff/login', data={
            'username': 'lab123',
            'password': 'labopen',
            'staff_role': 'LAB_STAFF'
        }, follow_redirects=True)
        
        print(f"Login response: {resp.status_code}")
        
        # Now try to access dashboard
        print("\nAccessing /lab/dashboard...")
        try:
            resp = client.get('/lab/dashboard')
            print(f"Dashboard response: {resp.status_code}")
            
            if resp.status_code == 500:
                print("\n❌ ERROR 500 FOUND!")
                print("Response data:")
                print(resp.data.decode()[:500])
            elif resp.status_code == 302:
                print("Redirected (expected for login-protected)")
                print(f"Redirect location: {resp.location}")
            else:
                print("✅ SUCCESS!")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
