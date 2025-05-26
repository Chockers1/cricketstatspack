#!/usr/bin/env python3
"""
Setup script to create MySQL user and database for local development
"""
print("🚀 Starting MySQL setup script...")

try:
    import mysql.connector
    from mysql.connector import Error
    print("✅ mysql.connector imported")
except ImportError as e:
    print(f"❌ Failed to import mysql.connector: {e}")
    print("💡 Install with: pip install mysql-connector-python")
    exit(1)

try:
    import os
    from dotenv import load_dotenv
    print("✅ Other imports successful")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    exit(1)

# Load environment variables
load_dotenv()
print("✅ Environment variables loaded")

def setup_local_mysql():
    """Set up MySQL user and database for local development"""
    
    print("🔧 Setting up local MySQL for Cricket Stats Pack")
    print("=" * 50)
    
    # Get root password from user
    root_password = input("Enter your MySQL root password (or press Enter if no password): ")
    
    try:
        # Connect as root
        print("🔗 Connecting to MySQL as root...")
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=root_password
        )
        
        if connection.is_connected():
            print("✅ Connected to MySQL successfully!")
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            print("🗄️ Creating cricket_auth database...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS cricket_auth")
            print("✅ Database cricket_auth created/verified")
            
            # Create appuser if it doesn't exist
            print("👤 Creating appuser account...")
            try:
                cursor.execute("DROP USER IF EXISTS 'appuser'@'localhost'")
                cursor.execute("CREATE USER 'appuser'@'localhost' IDENTIFIED BY 'AppUser123!'")
                cursor.execute("GRANT ALL PRIVILEGES ON cricket_auth.* TO 'appuser'@'localhost'")
                cursor.execute("FLUSH PRIVILEGES")
                print("✅ User 'appuser' created with full privileges on cricket_auth")
            except Error as user_err:
                print(f"⚠️ User creation warning: {user_err}")
            
            # Test appuser connection
            print("🧪 Testing appuser connection...")
            cursor.close()
            connection.close()
            
            # Test new user
            test_connection = mysql.connector.connect(
                host='localhost',
                user='appuser',
                password='AppUser123!',
                database='cricket_auth'
            )
            
            if test_connection.is_connected():
                print("✅ appuser connection test successful!")
                
                # Create basic tables if they don't exist
                print("📋 Creating basic table structure...")
                test_cursor = test_connection.cursor()
                
                # Create users table
                users_table_sql = """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255) DEFAULT NULL,
                    security_question_1 VARCHAR(500),
                    security_answer_1_hash VARCHAR(255),
                    security_question_2 VARCHAR(500),
                    security_answer_2_hash VARCHAR(255),
                    is_premium TINYINT(1) DEFAULT 0,
                    is_disabled TINYINT(1) DEFAULT 0,
                    is_banned TINYINT(1) DEFAULT 0,
                    subscription_type VARCHAR(50) DEFAULT NULL,
                    subscription_status VARCHAR(50) DEFAULT NULL,
                    stripe_customer_id VARCHAR(255) DEFAULT NULL,
                    current_period_end DATETIME DEFAULT NULL,
                    notify_newsletter TINYINT(1) DEFAULT 0,
                    reset_attempts INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
                test_cursor.execute(users_table_sql)
                
                # Create audit_logs table
                audit_table_sql = """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_email VARCHAR(255),
                    action VARCHAR(100),
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                test_cursor.execute(audit_table_sql)
                
                # Create session_logs table (optional for analytics)
                session_table_sql = """
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_email VARCHAR(255),
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT
                )
                """
                test_cursor.execute(session_table_sql)
                
                test_connection.commit()
                print("✅ Basic table structure created")
                
                # Add sample admin user if it doesn't exist
                admin_email = os.getenv("ADMIN_EMAIL", "r.taylor289@gmail.com")
                test_cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (admin_email,))
                admin_exists = test_cursor.fetchone()[0]
                
                if admin_exists == 0:
                    print(f"👨‍💼 Creating admin user: {admin_email}")
                    import bcrypt
                    
                    # Use a default password - you should change this
                    default_password = "admin123"
                    hashed_pw = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    insert_admin_sql = """
                    INSERT INTO users (email, password_hash, display_name, security_question_1, 
                                     security_answer_1_hash, security_question_2, security_answer_2_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    # Simple security questions for testing
                    sq1_hash = bcrypt.hashpw("blue".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    sq2_hash = bcrypt.hashpw("rover".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    test_cursor.execute(insert_admin_sql, (
                        admin_email, hashed_pw, "Admin User",
                        "What is your favorite color?", sq1_hash,
                        "What was your first pet's name?", sq2_hash
                    ))
                    test_connection.commit()
                    print(f"✅ Admin user created with password: {default_password}")
                    print("⚠️  IMPORTANT: Change this password after first login!")
                else:
                    print(f"ℹ️  Admin user {admin_email} already exists")
                
                # Add some sample users for testing
                test_cursor.execute("SELECT COUNT(*) FROM users")
                user_count = test_cursor.fetchone()[0]
                print(f"📊 Current user count: {user_count}")
                
                test_cursor.close()
                test_connection.close()
                
                print("\n🎉 LOCAL MYSQL SETUP COMPLETE!")
                print("=" * 50)
                print(f"✅ Database: cricket_auth")
                print(f"✅ User: appuser")
                print(f"✅ Password: AppUser123!")
                print(f"✅ Admin email: {admin_email}")
                print(f"✅ Admin password: admin123 (CHANGE THIS!)")
                print("\n🚀 You can now run your Flask app locally!")
                
                return True
                
            else:
                print("❌ appuser connection test failed")
                return False
                
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        
        if "Access denied" in str(e):
            print("\n💡 Troubleshooting suggestions:")
            print("1. Make sure you entered the correct root password")
            print("2. If you don't know the root password, try resetting it:")
            print("   - Stop MySQL service: net stop MySQL80")
            print("   - Start with skip-grant-tables: mysqld --skip-grant-tables")
            print("   - Connect and reset: ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword';")
            print("3. Check if MySQL is running: Get-Service MySQL80")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = setup_local_mysql()
    
    if success:
        print("\n🔧 Next steps:")
        print("1. Test the admin dashboard: python debug_admin.py")
        print("2. Run your Flask app: python app.py")
        print("3. Visit http://localhost:5000/admin")
        print("4. Login with your admin email and password: admin123")
    else:
        print("\n💥 Setup failed. Please check the error messages above.")
