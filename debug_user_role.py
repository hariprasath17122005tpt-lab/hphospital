
from app import create_app, db
from app.models.models import User, UserRole

app = create_app()

with app.app_context():
    users = User.query.all()
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f"User: {u.username}, Role: {u.role}, Type: {type(u.role)}")
        if isinstance(u.role, UserRole):
            print(f"  Is Enum: Yes, Value: {u.role.value}")
        else:
            print(f"  Is Enum: No, Value: {u.role}")

