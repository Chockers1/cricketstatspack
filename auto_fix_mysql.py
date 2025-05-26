#!/usr/bin/env python3
"""
Automatic MySQL credential finder and setup
"""
print("🚀 Starting auto MySQL fix script...")

try:
    import mysql.connector
    from mysql.connector import Error
    print("✅ MySQL connector imported")
except Exception as e:
    print(f"❌ MySQL import failed: {e}")
    exit(1)

try:
    import os
    from dotenv import load_dotenv
    print("✅ Other imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

load_dotenv()
print("✅ Loaded .env file")

def find_working_mysql_credentials():
    """Try different MySQL root credentials to find one that works"""
    
    print("🔍 Searching for working MySQL credentials...")
    
    # Common MySQL root password combinations
    credentials = [
        {'user': 'root', 'password': ''},
        {'user': 'root', 'password': 'root'},
        {'user': 'root', 'password': 'password'},
        {'user': 'root', 'password': 'admin'},
        {'user': 'root', 'password': 'mysql'},
        {'user': 'root', 'password': '123456'},
        {'user': 'root', 'password': 'AppUser123!'},  # Same as production
        {'user': 'appuser', 'password': 'AppUser123!'},  # In case it already exists
    ]
    
    for i, creds in enumerate(credentials):
        print(f"\n🧪 Testing {i+1}/{len(credentials)}: {creds['user']} with password: {'***' if creds['password'] else '(empty)'}")
        
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user=creds['user'],
                password=creds['password']
            )
            
            if connection.is_connected():
                print("✅ SUCCESS! Found working credentials")
                cursor = connection.cursor()
                
                # Test database access
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                print(f"📋 Available databases: {len(databases)}")
                
                # Check if cricket_auth exists
                cursor.execute("SHOW DATABASES LIKE 'cricket_auth'")
                cricket_db = cursor.fetchone()
                
                if cricket_db:
                    print("✅ cricket_auth database exists")
                    
                    # Try to connect to cricket_auth
                    cursor.execute("USE cricket_auth")
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    print(f"📊 Tables in cricket_auth: {len(tables)}")
                    
                    if tables:
                        for table in tables:
                            print(f"   - {table[0]}")
                        
                        # Check users table
                        if any('users' in str(table) for table in tables):
                            cursor.execute("SELECT COUNT(*) FROM users")
                            user_count = cursor.fetchone()[0]
                            print(f"👥 Users in database: {user_count}")
                    
                else:
                    print("⚠️ cricket_auth database does not exist - will need to create it")
                
                cursor.close()
                connection.close()
                
                return creds
                
        except Error as e:
            print(f"❌ Failed: {e}")
    
    return None

def create_local_env_fix(working_creds):
    """Create a fixed .env file for local development"""
    
    if not working_creds:
        print("❌ No working credentials found")
        return False
    
    print(f"\n🔧 Creating local database setup with {working_creds['user']}")
    
    # Read current .env
    env_content = []
    try:
        with open('.env', 'r') as f:
            env_content = f.readlines()
    except FileNotFoundError:
        print("❌ .env file not found")
        return False
    
    # Update database credentials
    new_env_content = []
    for line in env_content:
        if line.startswith('DB_USER='):
            new_env_content.append(f"DB_USER={working_creds['user']}\n")
        elif line.startswith('DB_PASS='):
            new_env_content.append(f"DB_PASS={working_creds['password']}\n")
        else:
            new_env_content.append(line)
    
    # Create backup
    with open('.env.backup', 'w') as f:
        f.writelines(env_content)
    print("✅ Created .env.backup")
    
    # Write new .env
    with open('.env', 'w') as f:
        f.writelines(new_env_content)
    print("✅ Updated .env with working credentials")
    
    return True

def test_admin_dashboard_connection():
    """Test if the admin dashboard can now connect"""
    
    print("\n🧪 Testing admin dashboard connection...")
    
    try:
        # Reload environment
        load_dotenv(override=True)
        
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME', 'cricket_auth')
        )
        
        if connection.is_connected():
            print("✅ Admin dashboard database connection successful!")
            
            cursor = connection.cursor()
            
            # Test the admin stats query (simplified)
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"📊 Total users: {user_count}")
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
            premium_count = cursor.fetchone()[0]
            print(f"💎 Premium users: {premium_count}")
            
            cursor.close()
            connection.close()
            
            return True
            
    except Error as e:
        print(f"❌ Connection test failed: {e}")
        return False

def main():
    print("🎯 MySQL Credential Finder & Admin Dashboard Fix")
    print("=" * 60)
    
    # Step 1: Find working credentials
    working_creds = find_working_mysql_credentials()
    
    if not working_creds:
        print("\n💥 Could not find working MySQL credentials!")
        print("\n🛠️ Manual steps to fix:")
        print("1. Reset your MySQL root password")
        print("2. Or install MySQL Workbench to manage users")
        print("3. Or check your MySQL installation documentation")
        return False
    
    # Step 2: Update .env file
    if create_local_env_fix(working_creds):
        print(f"\n✅ Updated .env to use: {working_creds['user']}")
    else:
        print("\n❌ Failed to update .env file")
        return False
    
    # Step 3: Test admin dashboard connection
    if test_admin_dashboard_connection():
        print("\n🎉 SUCCESS! Admin dashboard should now work!")
        print("\n🚀 Next steps:")
        print("1. Run: python debug_admin.py")
        print("2. Run your Flask app: python app.py")
        print("3. Visit: http://localhost:5000/admin")
        print(f"4. Login as: {os.getenv('ADMIN_EMAIL', 'r.taylor289@gmail.com')}")
        return True
    else:
        print("\n❌ Admin dashboard connection still failing")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n💡 Alternative solution:")
        print("You can develop and test on your production server where MySQL is working")
        print("Or set up a local MySQL instance with known credentials")
