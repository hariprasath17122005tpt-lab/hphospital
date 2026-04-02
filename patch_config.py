import re
import os

file_path = 'config.py'
print(f"Reading {file_path}...")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    print("Warning: utf-8 decode failed, trying latin-1")
    with open(file_path, 'r', encoding='latin-1') as f:
        content = f.read()

# Check if already patched to avoid double patching
if "os.environ.get('DATABASE_URL')" in content:
    print("config.py is already patched.")
    exit(0)

# Pattern to find the URI definition
# We look for SQLALCHEMY_DATABASE_URI = 'string' or "string"
pattern = r"(SQLALCHEMY_DATABASE_URI\s*=\s*)(['\"].*?['\"])"
match = re.search(pattern, content)

if match:
    print(f"Found match: {match.group(0)}")
    new_content = re.sub(
        pattern,
        r"\1os.environ.get('DATABASE_URL') or \2",
        content
    )
    
    # Ensure import os is present
    if "import os" not in new_content:
        new_content = "import os\n" + new_content
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patched config.py successfully.")
else:
    print("Could not find SQLALCHEMY_DATABASE_URI pattern to patch.")
    # Fallback: Just append it to DevelopmentConfig if possible
    if "class DevelopmentConfig" in content:
        # This is riskier, better to just warn
        print("Manual intervention might be needed for config.py")
