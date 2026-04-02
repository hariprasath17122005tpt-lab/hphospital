from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models.models import User
from werkzeug.security import check_password_hash

app = create_app('development')
with app.app_context():
    fake_user = User.query.filter_by(username='fake').first()
    
    if fake_user:
        print('fake user found')
        print(f'Password hash: {fake_user.password_hash[:50]}...')
        
        # Test if password 'fake' matches
        is_valid = check_password_hash(fake_user.password_hash, 'fake')
        print(f'Password fake matches: {is_valid}')
    else:
        print('fake user not found')
