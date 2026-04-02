
import ast

def check_name_errors(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    defined_names = set()
    used_names = set()

    # Add builtins
    import builtins
    defined_names.update(dir(builtins))

    # Add some common Flask/SQLAlchemy names that might be injected
    defined_names.update(['db', 'current_user', 'login_required', 'flash', 'redirect', 'url_for', 'render_template', 'request', 'jsonify', 'Blueprint'])

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                defined_names.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)

    undefined = used_names - defined_names
    print(f"Potentially undefined names in {filepath}:")
    for name in sorted(undefined):
        print(f"  - {name}")

if __name__ == "__main__":
    check_name_errors(r'c:\Users\harip\OneDrive\Desktop\hospital\app\routes\patient.py')
