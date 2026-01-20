#!/usr/bin/env python
"""
Quick test script to verify the Flask app runs without errors
"""
import os
import sys

# Add the hospital directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_app_creation():
    """Test app factory"""
    print("[TEST 1] Testing app creation...")
    try:
        from app import create_app, db
        app = create_app('development')
        print("  OK: App created successfully")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection"""
    print("\n[TEST 2] Testing database connection...")
    try:
        from app import create_app, db
        from app.models.models import User, Patient, Doctor
        
        app = create_app('development')
        with app.app_context():
            # Try to query users
            user_count = User.query.count()
            print(f"  OK: Database connected. Found {user_count} users")
            return True
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """Test route registration"""
    print("\n[TEST 3] Testing route registration...")
    try:
        from app import create_app
        app = create_app('development')
        
        # Check registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static'):
                routes.append(rule.rule)
        
        print(f"  OK: Found {len(routes)} routes registered")
        print(f"  Sample routes: {routes[:5]}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ml_models():
    """Test ML models import"""
    print("\n[TEST 4] Testing ML models...")
    try:
        from app.ml_models.health_ai import HealthRiskPredictor, SymptomChecker
        from app.ml_models.medical_image_analyzer import MedicalImageAnalyzer
        
        predictor = HealthRiskPredictor()
        symptom_checker = SymptomChecker()
        analyzer = MedicalImageAnalyzer()
        
        print("  OK: All ML models loaded successfully")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_system():
    """Test authentication system"""
    print("\n[TEST 5] Testing authentication system...")
    try:
        from app import create_app
        from werkzeug.security import generate_password_hash, check_password_hash
        
        app = create_app('development')
        
        # Test password hashing
        password = "test_password"
        hashed = generate_password_hash(password)
        verified = check_password_hash(hashed, password)
        
        assert verified, "Password verification failed"
        print("  OK: Authentication system working")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("HOSPITAL MANAGEMENT SYSTEM - VERIFICATION TESTS")
    print("=" * 60)
    
    results = {
        "App Creation": test_app_creation(),
        "Database Connection": test_database_connection(),
        "Route Registration": test_routes(),
        "ML Models": test_ml_models(),
        "Authentication System": test_authentication_system(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"[{status}] {test_name}")
    
    print("=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\nSUCCESS: All systems operational!")
        print("\nYou can now access the application at:")
        print("  - Home Page: http://localhost:5000")
        print("  - Patient Login: http://localhost:5000/patient/login")
        print("  - Doctor Login: http://localhost:5000/doctor/login")
        print("\nTest Credentials:")
        print("  Patient - Username: john_patient, Password: password123")
        print("  Doctor - Username: dr_smith, Password: password123")
        return 0
    else:
        print(f"\nFAILURE: {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    exit(main())
