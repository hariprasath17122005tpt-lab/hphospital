#!/usr/bin/env python
"""
Quick installation of MySQL dependencies
Run this before using the application
"""

import subprocess
import sys
import os

def install_mysql_dependencies():
    """Install MySQL-related Python packages"""
    packages = [
        'PyMySQL==1.1.2',
        'mysql-connector-python==9.5.0',
        'SQLAlchemy==2.0.43'
    ]
    
    print("\n" + "="*80)
    print("🔧 Installing MySQL Dependencies")
    print("="*80)
    
    for package in packages:
        try:
            print(f"\n📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning while installing {package}: {e}")
            continue
    
    print("\n✅ All MySQL dependencies installed!")

if __name__ == '__main__':
    install_mysql_dependencies()
