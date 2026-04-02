
from app import create_app
from app.models.models import db, User, UserRole
from werkzeug.security import check_password_hash

app = create_app()

def check_login(username, password):
    with app.app_context():
        print(f"Checking login for: {username}")
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ User '{username}' not found in database.")
            return

        print(f"Found user: {user.username}")
        print(f"Role in DB: {user.role} (Type: {type(user.role)})")
        print(f"Expected Role: {UserRole.HOST}")
        
        # Check Role
        if user.role != UserRole.HOST:
            print(f"❌ Role mismatch! User has {user.role}, expected {UserRole.HOST}")
        else:
            print("✅ Role matches UserRole.HOST")

        # Check Password
        if check_password_hash(user.password_hash, password):
            print("✅ Password verified successfully.")
        else:
            print("❌ Password verification FAILED.")

if __name__ == "__main__":
    check_login('hari95972', '27959irah')
    check_login('hospitalhost', 'hosthospital')
    check_login('hospital44055', '55044hospital')
    check_login('qwas', 'anypass') # Check what user typed
