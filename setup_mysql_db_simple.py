#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MySQL Database Setup Script for Hospital Management System
Creates database, user, and initializes all tables
"""

import mysql.connector
import sys
import os

def get_root_credentials():
    """Get MySQL root credentials from user"""
    print("\n" + "="*80)
    print("MYSQL ROOT USER CREDENTIALS")
    print("="*80)
    root_user = input("Enter MySQL root username (default: root): ").strip() or "root"
    root_password = input("Enter MySQL root password: ").strip()
    return root_user, root_password

def create_mysql_user_and_database(root_user, root_password):
    """Create MySQL user and database"""
    try:
        # Connect as root
        print("\nConnecting to MySQL as root...")
        connection = mysql.connector.connect(
            host='localhost',
            port=3307,
            user=root_user,
            password=root_password
        )
        cursor = connection.cursor()
        
        print("[OK] Connected successfully!")
        
        # Create database
        print("\n[*] Creating database 'hospital_db'...")
        cursor.execute("DROP DATABASE IF EXISTS hospital_db")
        cursor.execute("""
            CREATE DATABASE hospital_db 
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_unicode_ci
        """)
        print("[OK] Database 'hospital_db' created!")
        
        # Create MySQL user
        print("\n[*] Creating MySQL user 'hospital_user'...")
        cursor.execute("DROP USER IF EXISTS 'hospital_user'@'localhost'")
        cursor.execute("""
            CREATE USER 'hospital_user'@'localhost' 
            IDENTIFIED BY 'Mysql'
        """)
        print("[OK] User 'hospital_user' created!")
        
        # Grant privileges
        print("\n[*] Granting privileges...")
        cursor.execute("""
            GRANT ALL PRIVILEGES ON hospital_db.* 
            TO 'hospital_user'@'localhost'
        """)
        cursor.execute("FLUSH PRIVILEGES")
        print("[OK] Privileges granted!")
        
        # Read and execute SQL file
        print("\n[*] Creating tables...")
        sql_file = r'c:\Users\harip\OneDrive\Desktop\hospital\mysql_database_setup.sql'
        
        if not os.path.exists(sql_file):
            print("[ERROR] SQL file not found: " + sql_file)
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split and execute SQL statements
        statements = sql_content.split(';')
        count = 0
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    count += 1
                except mysql.connector.Error as e:
                    if 'already exists' not in str(e).lower():
                        print("[WARNING] Error executing statement: " + str(e)[:100])
        
        connection.commit()
        print("[OK] All tables created successfully! (" + str(count) + " statements executed)")
        
        cursor.close()
        connection.close()
        
        return True
        
    except mysql.connector.Error as e:
        print("[ERROR] MySQL Error: " + str(e))
        return False
    except Exception as e:
        print("[ERROR] Error: " + str(e))
        return False

def main():
    print("\n" + "="*80)
    print("HOSPITAL MANAGEMENT SYSTEM - MySQL Database Setup")
    print("="*80)
    print("\nThis script will:")
    print("  1. Create 'hospital_db' database")
    print("  2. Create 'hospital_user' with password 'Mysql'")
    print("  3. Create all required tables")
    print("\nNote: You need MySQL root credentials to proceed.")
    
    root_user, root_password = get_root_credentials()
    
    success = create_mysql_user_and_database(root_user, root_password)
    
    if success:
        print("\n" + "="*80)
        print("SUCCESS - DATABASE SETUP COMPLETE!")
        print("="*80)
        print("\nDatabase Details:")
        print("  Database Name: hospital_db")
        print("  Username: hospital_user")
        print("  Password: Mysql")
        print("  Host: localhost")
        print("  Port: 3307")
        print("\nYou can now run: python run_server_stable.py")
    else:
        print("\n" + "="*80)
        print("FAILED - DATABASE SETUP FAILED!")
        print("="*80)
        print("\nPlease check:")
        print("  1. MySQL is installed and running")
        print("  2. Root credentials are correct")
        print("  3. You have necessary permissions")
        sys.exit(1)

if __name__ == '__main__':
    main()
