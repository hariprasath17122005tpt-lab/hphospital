#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app import create_app
from flask.testing import FlaskClient
import sys

app = create_app()

# Test the homepage
with app.test_client() as client:
    response = client.get('/')
    
    if response.status_code == 200:
        print("✓ Homepage loads (HTTP 200)")
    else:
        print(f"✗ Homepage error (HTTP {response.status_code})")
        sys.exit(1)
    
    html = response.get_data(as_text=True)
    
    checks = {
        'Top bar visible': 'topbar' in html,
        'Doctor grid rendered': 'doc-grid' in html,
        'Top bar gradient': 'linear-gradient(90deg,#0a1628,#0f172a)' in html,
        'Enhanced contrast': 'rgba(255,255,255,.95)' in html,
        'Doctor card styling': 'doc-card-img' in html,
        'Experience badge': 'experience' in html,
        'Doctor badge': '.badge' in html,
    }
    
    all_pass = True
    for check, result in checks.items():
        status = '✓' if result else '✗'
        print(f"{status} {check}")
        if not result:
            all_pass = False
    
    if all_pass:
        print("\n✓ HOMEPAGE RENDERING WITH ALL UI IMPROVEMENTS")
        sys.exit(0)
    else:
        print("\n✗ SOME ELEMENTS NOT RENDERING")
        sys.exit(1)
