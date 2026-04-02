import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    rows = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='lab_reports' ORDER BY ordinal_position"
    )).fetchall()
    print("lab_reports columns:")
    for r in rows:
        print(f"  - {r[0]}")
