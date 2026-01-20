#!/usr/bin/env python
"""
Quick server verification script
"""
import time
import sys

try:
    import requests
except ImportError:
    print("Installing requests library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

def verify_server():
    """Verify Flask server is running"""
    
    print("\n" + "="*60)
    print("FLASK SERVER VERIFICATION")
    print("="*60 + "\n")
    
    urls = [
        "http://127.0.0.1:5000/",
        "http://localhost:5000/",
    ]
    
    for url in urls:
        try:
            print(f"Testing: {url}", end=" ... ")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("✅ RUNNING!")
                print(f"  Status Code: {response.status_code}")
                print(f"  Content Length: {len(response.text)} bytes")
                
                # Check if it's the home page
                if "<title>" in response.text:
                    print("  ✅ Home page content found")
                
                print("\n" + "="*60)
                print("✅ SERVER IS OPERATIONAL!")
                print("="*60)
                print("\n📍 Access the application at:")
                print(f"   {url}\n")
                return True
                
        except Exception as e:
            print(f"✗ {str(e)}")
    
    print("\n" + "="*60)
    print("❌ Server is not responding")
    print("="*60)
    print("\n⚠️  TROUBLESHOOTING:")
    print("1. Is the server running? (check terminal output)")
    print("2. Run: python run.py")
    print("3. Wait 2-3 seconds for startup")
    print("4. Try again\n")
    
    return False

if __name__ == "__main__":
    success = verify_server()
    sys.exit(0 if success else 1)
