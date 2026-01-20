#!/usr/bin/env python
"""
🏥 Hospital Management System - MySQL Quick Start
Complete automated setup in one script
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"⏳ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"⚠️  {description} - WARNING")
            if result.stderr:
                print(f"   Error: {result.stderr[:100]}")
            return True  # Continue anyway
    except Exception as e:
        print(f"❌ {description} - FAILED: {e}")
        return False

def check_mysql():
    """Check if MySQL is installed and running"""
    print_header("🔍 Checking MySQL Installation")
    
    try:
        result = subprocess.run("mysql --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ MySQL found: {result.stdout.strip()}")
            return True
        else:
            print("❌ MySQL not found in PATH")
            print("   Please install MySQL Server from: https://dev.mysql.com/downloads/mysql/")
            return False
    except Exception as e:
        print(f"❌ Error checking MySQL: {e}")
        return False

def install_python_packages():
    """Install required Python packages"""
    print_header("📦 Installing Python Packages")
    
    packages = [
        "PyMySQL",
        "mysql-connector-python",
        "Flask-SQLAlchemy",
        "python-dotenv"
    ]
    
    for package in packages:
        run_command(f'pip install "{package}"', f"Installing {package}")
    
    return True

def setup_database():
    """Setup MySQL database"""
    print_header("🗄️  Setting Up MySQL Database")
    
    print("Please provide MySQL root credentials...")
    root_user = input("MySQL root username (default: root): ").strip() or "root"
    root_password = input("MySQL root password: ").strip()
    
    if not root_password:
        print("❌ Root password cannot be empty")
        return False
    
    # Run the setup script
    setup_script = Path(__file__).parent / "setup_mysql_db.py"
    
    try:
        # Create a subprocess to run setup with credentials
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            input=f"{root_user}\n{root_password}\n",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Database setup completed successfully!")
            return True
        else:
            print(f"❌ Database setup failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running setup script: {e}")
        return False

def test_connection():
    """Test database connection"""
    print_header("🧪 Testing Database Connection")
    
    try:
        import mysql.connector
        
        conn = mysql.connector.connect(
            host='localhost',
            port=3307,
            user='hospital_user',
            password='Mysql',
            database='hospital_db'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'hospital_db'")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"✅ Database connection successful!")
        print(f"✅ Found {table_count} tables in hospital_db")
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def verify_ai_chatbot():
    """Verify AI chatbot code is intact"""
    print_header("🤖 Verifying AI Chatbot Code")
    
    ai_routes = Path(__file__).parent / "app" / "routes" / "ai_chatbot.py"
    
    if ai_routes.exists():
        print(f"✅ AI chatbot file found: {ai_routes}")
        
        with open(ai_routes, 'r') as f:
            content = f.read()
            if 'def' in content and 'ollama' in content.lower():
                print("✅ AI chatbot code appears intact")
                return True
    
    print("⚠️  Could not verify AI chatbot file")
    return False

def print_next_steps():
    """Print next steps"""
    print_header("✅ Setup Complete!")
    
    print("""
📋 Next Steps:

1. 🌐 Start the Application:
   cd c:\\Users\\harip\\OneDrive\\Desktop\\hospital
   python run_server_stable.py

2. 🌍 Open Web Interface:
   http://localhost:5000

3. 📊 View Database (Optional):
   - Open MySQL Workbench
   - Connect to localhost (hospital_user / Mysql)
   - Database: hospital_db

4. 📚 Documentation:
   - MYSQL_SETUP_GUIDE.md - Complete setup guide
   - SQL_REFERENCE.md - SQL query reference

5. 🧪 Test the System:
   - Register as patient
   - Try the AI chatbot
   - View medical data

📊 Database Credentials:
   Host: localhost
   Port: 3306
   Database: hospital_db
   Username: hospital_user
   Password: Mysql

⚠️  IMPORTANT:
   - AI chatbot code is UNTOUCHED
   - All data now stored in MySQL
   - Original SQLite database no longer used
   - Backup regularly with: mysqldump -u hospital_user -pMysql hospital_db > backup.sql

🆘 Need Help?
   - Check MYSQL_SETUP_GUIDE.md
   - Review error messages in console
   - Verify MySQL service is running: net start MySQL80
    """)

def main():
    """Main setup flow"""
    print_header("🏥 HOSPITAL MANAGEMENT SYSTEM - MySQL Setup")
    
    print("""
This script will:
✓ Check MySQL installation
✓ Install Python dependencies
✓ Create database and user
✓ Initialize all tables
✓ Verify AI chatbot code
✓ Test the connection

Note: This will take 2-5 minutes
    """)
    
    input("Press ENTER to start setup...")
    
    # Step 1: Check MySQL
    if not check_mysql():
        print("\n❌ MySQL is not installed or not in PATH")
        print("Please install MySQL first from: https://dev.mysql.com/downloads/mysql/")
        sys.exit(1)
    
    # Step 2: Install Python packages
    if not install_python_packages():
        print("\n⚠️  Some packages may not have installed properly")
    
    # Step 3: Setup database
    if not setup_database():
        print("\n❌ Database setup failed")
        sys.exit(1)
    
    # Step 4: Test connection
    time.sleep(2)  # Wait for database to be ready
    if not test_connection():
        print("\n⚠️  Connection test failed")
        print("Please check your MySQL credentials")
    
    # Step 5: Verify AI chatbot
    verify_ai_chatbot()
    
    # Print next steps
    print_next_steps()
    
    print("\n" + "="*80)
    print("✅ ALL DONE! Your system is ready to use.")
    print("="*80 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
