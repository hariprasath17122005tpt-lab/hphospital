#!/usr/bin/env python
"""
Test all Flask routes to identify which ones throw 500 errors
"""
import os
import sys
from app import create_app

def test_routes():
    """Test all registered routes"""
    app = create_app('development')
    
    print("\n" + "="*80)
    print("TESTING ALL REGISTERED ROUTES")
    print("="*80 + "\n")
    
    with app.test_client() as client:
        routes_to_test = [
            ('GET', '/'),
            ('GET', '/login'),
            ('GET', '/about'),
            ('GET', '/features'),
            ('GET', '/contact'),
            ('GET', '/health'),
            ('GET', '/walkin/register'),
            ('GET', '/walkin/select'),
        ]
        
        passed = 0
        failed = 0
        errors = []
        
        for method, path in routes_to_test:
            try:
                if method == 'GET':
                    response = client.get(path)
                else:
                    response = client.post(path)
                
                status = "✅ OK" if response.status_code < 500 else "❌ ERROR"
                print(f"{status} {method:6} {path:40} -> {response.status_code}")
                
                if response.status_code >= 500:
                    failed += 1
                    errors.append((path, response.status_code, response.data.decode()[:200]))
                else:
                    passed += 1
                    
            except Exception as e:
                print(f"❌ CRASH {method:6} {path:40} -> {str(e)[:100]}")
                failed += 1
                errors.append((path, "EXCEPTION", str(e)))
        
        print("\n" + "="*80)
        print(f"RESULTS: {passed} Passed, {failed} Failed")
        print("="*80)
        
        if errors:
            print("\n❌ ERRORS FOUND:\n")
            for path, status, error in errors:
                print(f"{path} ({status}):")
                print(f"  {error}\n")
        else:
            print("\n✅ ALL ROUTES WORKING!")
        
        return failed == 0

if __name__ == '__main__':
    success = test_routes()
    sys.exit(0 if success else 1)
