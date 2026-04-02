from dotenv import load_dotenv
load_dotenv()
from config import config
from app import create_app, db
from app.models.models import User

app = create_app('development')
with app.app_context():
    user = User.query.filter_by(username='rose').first()
    if user:
        print(f'User rose exists: YES')
        print(f'User role: {user.role}')
        print(f'User is_active: {user.is_active}')
    else:
        print('User rose does not exist')
