#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app import create_app
import sys

app = create_app()

with app.test_client() as client:
    response = client.get('/')
    html = response.get_data(as_text=True)
    
    # Check specific CSS rules are rendered
    critical_checks = [
        ('.topbar{background:linear-gradient(90deg,#0a1628,#0f172a)', 'Topbar gradient'),
        ('rgba(255,255,255,.95)', 'Top bar link contrast'),
        ('.doc-card-img{', 'Doctor card image class'),
        ('.doc-card .experience{', 'Experience badge class'),
        ('.doc-card .badge{', 'Doctor badge class'),
        ('@keyframes shimmer', 'Shimmer animation'),
        ('0 20px 60px rgba(37,99,235,.15)', 'Enhanced hover shadow'),
        ('transform:translateY(-12px)', 'Premium card hover lift'),
    ]
    
    print("DETAILED RENDERING CHECK")
    print("=" * 60)
    
    all_found = True
    for css_check, description in critical_checks:
        found = css_check in html
        status = '✓' if found else '✗'
        print(f"{status} {description}")
        if not found:
            all_found = False
    
    print("=" * 60)
    
    if all_found:
        print("✓ ALL CSS IMPROVEMENTS RENDERING IN HTML")
        print("✓ TASK COMPLETE - UI FIXES FULLY DEPLOYED")
        sys.exit(0)
    else:
        print("✗ Some CSS not found in rendered output")
        sys.exit(1)
