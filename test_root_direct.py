#!/usr/bin/env python3
"""
Direct test with root credentials
"""
import mysql.connector
from mysql.connector import Error

print("🚀 Testing with ROOT credentials directly")
print("=" * 50)

def test_direct_root():
    """Test with hardcoded root credentials"""
    try:
        # Direct connection with root credentials
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='AppUser123!',
            database='cricket_auth'
        )
        
        if connection.is_connected():
            print("✅ ROOT CONNECTION SUCCESSFUL!")
            
            cursor = connection.cursor(dictionary=True)
            
            # Test admin queries
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
            print(f"📈 Total users in database: {total_users}")
            
            if total_users > 0:
                # Get sample users
                cursor.execute("""
                    SELECT id, email, is_premium, created_at
                    FROM users 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                users = cursor.fetchall()
                
                print(f"\n👥 Sample users:")
                for user in users:
                    print(f"   - {user['email']} (Premium: {bool(user['is_premium'])})")
                
                print(f"\n🎉 ADMIN DASHBOARD SHOULD WORK!")
                print(f"   The database has {total_users} users ready to display")
                
            else:
                print(f"⚠️  Database is empty - no users found")
                print(f"   You may need to register some test users first")
            
            cursor.close()
            connection.close()
            return True
            
    except Error as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_direct_root()
