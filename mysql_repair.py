#!/usr/bin/env python3
"""
MySQL setup and repair script
"""
print("🔧 MySQL Setup and Repair Script")
print("=" * 40)

# Try common Windows MySQL configurations
import mysql.connector
from mysql.connector import Error

def test_mysql_configs():
    """Test common MySQL configurations on Windows"""
    
    # Common Windows MySQL configurations
    configs = [
        {'host': 'localhost', 'user': 'root', 'password': ''},
        {'host': 'localhost', 'user': 'root', 'password': 'root'},
        {'host': 'localhost', 'user': 'root', 'password': 'password'},
        {'host': 'localhost', 'user': 'root', 'password': 'admin'},
        {'host': 'localhost', 'user': 'root', 'password': 'mysql'},
        {'host': '127.0.0.1', 'user': 'root', 'password': ''},
        {'host': '127.0.0.1', 'user': 'root', 'password': 'root'},
    ]
    
    for i, config in enumerate(configs):
        print(f"\n🔍 Testing config {i+1}: {config['user']}@{config['host']} with password: {'***' if config['password'] else '(empty)'}")
        
        try:
            connection = mysql.connector.connect(**config)
            if connection.is_connected():
                print("✅ CONNECTION SUCCESSFUL!")
                
                cursor = connection.cursor()
                
                # Check MySQL version
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"📋 MySQL version: {version[0]}")
                
                # List databases
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                print("📂 Available databases:")
                for db in databases:
                    print(f"   - {db[0]}")
                
                # Check if cricket_auth database exists
                cursor.execute("SHOW DATABASES LIKE 'cricket_auth'")
                result = cursor.fetchone()
                if result:
                    print("✅ cricket_auth database exists")
                    
                    # Connect to the cricket_auth database
                    cursor.execute("USE cricket_auth")
                    
                    # Check tables
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    print("📊 Tables in cricket_auth:")
                    for table in tables:
                        print(f"   - {table[0]}")
                    
                    # Check users table
                    if ('users',) in tables:
                        cursor.execute("SELECT COUNT(*) FROM users")
                        user_count = cursor.fetchone()
                        print(f"👥 Users in database: {user_count[0]}")
                        
                        if user_count[0] > 0:
                            cursor.execute("SELECT id, email, created_at FROM users LIMIT 5")
                            users = cursor.fetchall()
                            print("📝 Sample users:")
                            for user in users:
                                print(f"   - ID: {user[0]}, Email: {user[1]}, Created: {user[2]}")
                    
                    # Check for appuser
                    cursor.execute("SELECT User, Host FROM mysql.user WHERE User = 'appuser'")
                    appuser = cursor.fetchall()
                    if appuser:
                        print("✅ appuser exists in MySQL")
                        for user in appuser:
                            print(f"   - {user[0]}@{user[1]}")
                    else:
                        print("❌ appuser does not exist in MySQL")
                        print("💡 You may need to create the appuser account")
                
                else:
                    print("❌ cricket_auth database does not exist")
                    print("💡 You may need to create the database and import data")
                
                cursor.close()
                connection.close()
                return config
                
        except Error as e:
            print(f"❌ Failed: {e}")
    
    return None

def suggest_fix(working_config):
    """Suggest how to fix the configuration"""
    if working_config:
        print(f"\n🎉 SUCCESS! Working configuration found:")
        print(f"   Host: {working_config['host']}")
        print(f"   User: {working_config['user']}")
        print(f"   Password: {'***' if working_config['password'] else '(empty)'}")
        
        print(f"\n🔧 To fix your .env file, update these values:")
        print(f"   DB_HOST={working_config['host']}")
        print(f"   DB_USER={working_config['user']}")
        print(f"   DB_PASS={working_config['password']}")
        print(f"   DB_NAME=cricket_auth")
        
    else:
        print(f"\n💀 No working configuration found.")
        print(f"\n🛠️ Troubleshooting steps:")
        print(f"1. Check if MySQL is running: Get-Service MySQL80")
        print(f"2. Try connecting with MySQL Workbench")
        print(f"3. Reset MySQL root password")
        print(f"4. Check MySQL configuration file")

if __name__ == "__main__":
    working_config = test_mysql_configs()
    suggest_fix(working_config)
