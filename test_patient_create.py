import urllib.request
import json
import traceback

try:
    req = urllib.request.Request(
        'http://127.0.0.1:5000/patients/create',
        data=json.dumps({"name": "Test", "age": 30, "gender": "Male"}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Body:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTPError Status:", e.code)
    print("HTTPError Body:", e.read().decode('utf-8'))
except Exception as e:
    print("Exception:")
    traceback.print_exc()
