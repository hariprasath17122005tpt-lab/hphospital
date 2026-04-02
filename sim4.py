from app import create_app, db
from app.models.models import User
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"User: {u.username}, Role: {u.role.value if hasattr(u.role, 'value') else u.role}")
