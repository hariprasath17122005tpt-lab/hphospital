
from app import create_app
from app.models.models import db, User, UserRole, Hospital, Doctor
from werkzeug.security import generate_password_hash

app = create_app()

def create_hosts():
    with app.app_context():
        # Define the hosts to create
        hosts = [
            {'username': 'hari95972', 'password': '27959irah', 'email': 'hari95972@host.system'},
            {'username': 'hospitalhost', 'password': 'hosthospital', 'email': 'hospitalhost@host.system'},
            {'username': 'hospital44055', 'password': '55044hospital', 'email': 'hospital44055@host.system'}
        ]

        # Get a default hospital for the relationship (required by User model usually due to foreign key, though nullable in model? let's check)
        # Model says: hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
        # So it is nullable. But usually good to assign to default hospital if one exists.
        default_hospital = Hospital.query.first()
        hospital_id = default_hospital.id if default_hospital else None

        print(f"Using Hospital ID: {hospital_id}")

        for h in hosts:
            # Check if user exists
            user = User.query.filter_by(username=h['username']).first()
            if user:
                print(f"User {h['username']} already exists. Updating password and role...")
                user.password_hash = generate_password_hash(h['password'])
                user.role = UserRole.HOST
                user.is_active = True
                # Ensure they don't have conflicting roles in other tables? 
                # The User model links to Patient/Doctor. We assume these are pure host accounts.
            else:
                print(f"Creating new host user {h['username']}...")
                user = User(
                    username=h['username'],
                    email=h['email'],
                    password_hash=generate_password_hash(h['password']),
                    role=UserRole.HOST,
                    hospital_id=hospital_id,
                    is_active=True
                )
                db.session.add(user)
            
            # Ensure email uniqueness doesn't crash us if we reused an email (unlikely with these custom ones)
            # If email matches another user but username defaults, we might have issue. 
            # Check email collision
            email_user = User.query.filter_by(email=h['email']).first()
            if email_user and email_user.id != user.id:
                print(f"WARNING: Email {h['email']} is taken by user {email_user.username}. Skipping or you might get integrity error.")
            
        try:
            db.session.commit()
            print("Host users created/updated successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating host users: {e}")

if __name__ == "__main__":
    create_hosts()
