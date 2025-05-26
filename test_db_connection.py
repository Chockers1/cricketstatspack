#!/usr/bin/env python3
"""
Simple database connection test script
"""
print("🚀 Starting database connection test...")

try:
    import mysql.connector
    from mysql.connector import Error
    print("✅ mysql.connector imported successfully")
except ImportError as e:
    print(f"❌ Failed to import mysql.connector: {e}")
    exit(1)

try:
    import os
    from dotenv import load_dotenv
    print("✅ Other imports successful")
except ImportError as e:
    print(f"❌ Failed to import other modules: {e}")
    exit(1)

# Load environment variables
load_dotenv()

def test_connection_methods():
    """Test different database connection methods"""
    
    # Method 1: Using .env credentials
    print("🔧 Method 1: Testing with .env credentials...")
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'appuser'),
            password=os.getenv('DB_PASS', 'AppUser123!'),
            database=os.getenv('DB_NAME', 'cricket_auth')
        )
        if connection.is_connected():
            print("✅ Connection successful with .env credentials")
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            result = cursor.fetchone()
            print(f"📊 Users count: {result[0]}")
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ .env credentials failed: {e}")
    
    # Method 2: Try root user
    print("\n🔧 Method 2: Testing with root user...")
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',  # Often empty for local development
            database='cricket_auth'
        )
        if connection.is_connected():
            print("✅ Connection successful with root (no password)")
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            result = cursor.fetchone()
            print(f"📊 Users count: {result[0]}")
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ Root (no password) failed: {e}")
    
    # Method 3: Try root with a common password
    print("\n🔧 Method 3: Testing with root and common password...")
    for password in ['root', 'password', 'admin', '']:
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password=password,
                database='cricket_auth'
            )
            if connection.is_connected():
                print(f"✅ Connection successful with root:'{password}'")
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                print(f"📊 Users count: {result[0]}")
                cursor.close()
                connection.close()
                return True
        except Error as e:
            print(f"❌ Root with password '{password}' failed: {e}")
    
    # Method 4: Check if database exists
    print("\n🔧 Method 4: Testing connection without specifying database...")
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        if connection.is_connected():
            print("✅ Connected to MySQL server")
            cursor = connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print("📋 Available databases:")
            for db in databases:
                print(f"   - {db[0]}")
            
            # Check if our database exists
            cursor.execute("SHOW DATABASES LIKE 'cricket_auth'")
            result = cursor.fetchone()
            if result:
                print("✅ cricket_auth database exists")
            else:
                print("❌ cricket_auth database does not exist")
            
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ Server connection failed: {e}")
    
    return False

if __name__ == "__main__":
    print("🔍 Database Connection Diagnostic")
    print("=" * 40)
    
    success = test_connection_methods()
    
    if not success:
        print("\n💡 Troubleshooting suggestions:")
        print("1. Ensure MySQL service is running")
        print("2. Check if cricket_auth database exists")
        print("3. Verify user 'appuser' exists and has permissions")
        print("4. Try connecting with MySQL Workbench or command line")
        print("5. Check firewall settings")
    
    print("\n✅ Diagnostic complete!")
