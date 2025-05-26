#!/usr/bin/env python3
"""
Simple MySQL root password finder and recovery guide
"""
import subprocess
import sys

def check_mysql_service():
    """Check if MySQL is running"""
    try:
        result = subprocess.run(['powershell', 'Get-Service', 'MySQL80'], 
                              capture_output=True, text=True)
        if 'Running' in result.stdout:
            print("✅ MySQL80 service is running")
            return True
        else:
            print("❌ MySQL80 service is not running")
            return False
    except Exception as e:
        print(f"❌ Could not check MySQL service: {e}")
        return False

def suggest_solutions():
    """Provide step-by-step solutions"""
    print("\n🔧 SOLUTIONS FOR LOCAL MYSQL ACCESS")
    print("=" * 50)
    
    print("\n📋 OPTION 1: Find/Reset MySQL Root Password")
    print("1. Try these common MySQL root passwords:")
    print("   - (empty password)")
    print("   - root")
    print("   - password") 
    print("   - admin")
    print("   - mysql")
    print("   - AppUser123!")
    
    print("\n2. If none work, reset the root password:")
    print("   a) Stop MySQL: net stop MySQL80")
    print("   b) Start in safe mode: mysqld --skip-grant-tables --skip-networking")
    print("   c) In new terminal: mysql -u root")
    print("   d) Run: USE mysql;")
    print("   e) Run: UPDATE user SET authentication_string=PASSWORD('newpass') WHERE User='root';")
    print("   f) Run: FLUSH PRIVILEGES;")
    print("   g) Restart MySQL normally")
    
    print("\n📋 OPTION 2: Use MySQL Workbench (Recommended)")
    print("1. Download MySQL Workbench from mysql.com")
    print("2. Connect as root (it may remember the password)")
    print("3. Create appuser with password AppUser123!")
    print("4. Grant all privileges on cricket_auth database")
    
    print("\n📋 OPTION 3: Work on Production Server")
    print("Since your production server MySQL is working:")
    print("1. Test admin dashboard directly on production")
    print("2. Make changes on production server") 
    print("3. Use production server for development")
    
    print("\n📋 OPTION 4: Use Different Local Database")
    print("1. Install PostgreSQL or SQLite instead")
    print("2. Modify app.py to use different database connector")
    print("3. Update .env file with new database credentials")

def create_quick_test():
    """Create a quick test script with manual password input"""
    test_script = '''#!/usr/bin/env python3
"""
Quick MySQL root password tester
"""
import mysql.connector
from mysql.connector import Error
import getpass

def test_mysql_with_password():
    password = getpass.getpass("Enter MySQL root password to test: ")
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=password
        )
        
        if connection.is_connected():
            print("✅ SUCCESS! Root password works!")
            print(f"Password is: {password}")
            
            # Now create appuser
            cursor = connection.cursor()
            
            print("Creating cricket_auth database...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS cricket_auth")
            
            print("Creating appuser...")
            cursor.execute("DROP USER IF EXISTS 'appuser'@'localhost'")
            cursor.execute("CREATE USER 'appuser'@'localhost' IDENTIFIED BY 'AppUser123!'")
            cursor.execute("GRANT ALL PRIVILEGES ON cricket_auth.* TO 'appuser'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
            
            print("✅ Setup complete! Your .env file should work now.")
            
            cursor.close()
            connection.close()
            return True
            
    except Error as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_mysql_with_password()
'''
    
    with open('test_mysql_password.py', 'w') as f:
        f.write(test_script)
    
    print("\n✅ Created test_mysql_password.py")
    print("Run it with: python test_mysql_password.py")

def main():
    print("🔍 MySQL Local Setup Diagnostic")
    print("=" * 40)
    
    # Check if MySQL is running
    if not check_mysql_service():
        print("❌ MySQL is not running. Start it first with:")
        print("   net start MySQL80")
        return
    
    # Provide solutions
    suggest_solutions()
    
    # Create quick test script
    create_quick_test()
    
    print("\n🎯 RECOMMENDED NEXT STEPS:")
    print("1. Try: python test_mysql_password.py")
    print("2. Or install MySQL Workbench for GUI access")
    print("3. Or work directly on your production server")

if __name__ == "__main__":
    main()
