#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

with open('app/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = {
    'Top bar gradient background': 'linear-gradient(90deg,#0a1628,#0f172a)' in content,
    'Top bar text contrast improved': 'rgba(255,255,255,.95)' in content,
    'Doctor card image container': '.doc-card-img' in content,
    'Doctor shimmer animation': '@keyframes shimmer' in content,
    'Experience badge styling': '.doc-card .experience' in content,
    'Doctor badge element': '.doc-card .badge' in content,
    'Enhanced hover shadow': '0 20px 60px' in content,
    'Premium cubic bezier transition': '.5s cubic-bezier(.34,1.56,.64,1)' in content,
}

print("UI FIX VERIFICATION")
print("=" * 50)

all_pass = True
for check_name, result in checks.items():
    status = '✓' if result else '✗'
    print(f"{status} {check_name}")
    if not result:
        all_pass = False

print("=" * 50)
if all_pass:
    print("✓ ALL UI FIXES VERIFIED AND APPLIED")
    sys.exit(0)
else:
    print("✗ SOME UPDATES MISSING")
    sys.exit(1)
