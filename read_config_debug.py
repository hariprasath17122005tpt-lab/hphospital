try:
    with open('config.py', 'r', encoding='utf-8') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading config.py: {e}")
