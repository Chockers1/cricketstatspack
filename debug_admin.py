#!/usr/bin/env python3
"""
Debug script for admin dashboard issues
"""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def test_db_connection():
    """Test database connection and basic queries"""
    print("🔍 Testing database connection...")
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        print("✅ Database connection successful!")
        
        cursor = conn.cursor(dictionary=True)
        
        # Test basic user count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        total_users = result["count"] if result else 0
        print(f"📊 Total users in database: {total_users}")
        
        # Test premium users
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_premium = 1")
        result = cursor.fetchone()
        premium_users = result["count"] if result else 0
        print(f"💎 Premium users: {premium_users}")
        
        # Test recent users
        cursor.execute("SELECT email, created_at, is_premium FROM users ORDER BY created_at DESC LIMIT 5")
        recent_users = cursor.fetchall()
        print(f"📋 Recent users:")
        for user in recent_users:
            print(f"  - {user['email']} (Premium: {user['is_premium']}) - {user['created_at']}")
        
        # Test session_logs table
        cursor.execute("SHOW TABLES LIKE 'session_logs'")
        session_table_exists = cursor.fetchone() is not None
        print(f"📝 Session logs table exists: {session_table_exists}")
        
        if session_table_exists:
            cursor.execute("SELECT COUNT(*) as count FROM session_logs")
            result = cursor.fetchone()
            session_count = result["count"] if result else 0
            print(f"📈 Total sessions logged: {session_count}")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def test_admin_stats():
    """Test the get_admin_stats function specifically"""
    print("\n🔍 Testing get_admin_stats function...")
    
    try:
        from auth_utils import get_admin_stats
        stats, users = get_admin_stats()
        
        print(f"📊 Stats returned: {stats}")
        print(f"👥 Users count: {len(users)}")
        
        if users:
            print("📋 First few users:")
            for i, user in enumerate(users[:3]):
                print(f"  {i+1}. {user.get('email', 'No email')} - Premium: {user.get('is_premium', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Error testing get_admin_stats: {e}")

if __name__ == "__main__":
    print("🚀 Admin Dashboard Debug Script")
    print("=" * 40)
    
    # Test database connection
    if test_db_connection():
        # Test admin stats function
        test_admin_stats()
    
    print("\n✅ Debug complete!")
