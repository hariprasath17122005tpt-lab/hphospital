
from app import create_app, db
import sqlalchemy

app = create_app()

with app.app_context():
    inspector = sqlalchemy.inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('health_data')]
    print(f"Columns in health_data: {columns}")
    if 'temperature' in columns:
        print("✅ 'temperature' column exists!")
    else:
        print("❌ 'temperature' column MISSING!")
