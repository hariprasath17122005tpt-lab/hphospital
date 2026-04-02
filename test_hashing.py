
from werkzeug.security import generate_password_hash, check_password_hash

passwords = ['27959irah', 'hosthospital', '55044hospital']

for p in passwords:
    h = generate_password_hash(p)
    if check_password_hash(h, p):
        print(f"✅ Hash check passed for '{p}'")
    else:
        print(f"❌ Hash check FAILED for '{p}'")
