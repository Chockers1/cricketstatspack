#!/usr/bin/env python3
"""
Test admin dashboard with correct root credentials
"""
print("🚀 Starting admin dashboard test...")

try:
    import os
    print("✅ os imported")
    import mysql.connector
    print("✅ mysql.connector imported")
    from mysql.connector import Error
    print("✅ Error imported")
    from dotenv import load_dotenv
    print("✅ dotenv imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Load environment variables
load_dotenv()
print("✅ Environment variables loaded")

print("🚀 Testing Admin Dashboard Database Connection")
print("=" * 50)

def test_admin_connection():
    """Test database connection and admin stats"""
    try:
        # Connect using current .env settings
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASS', 'AppUser123!'),
            database=os.getenv('DB_NAME', 'cricket_auth')
        )
        
        if connection.is_connected():
            print("✅ Database connection successful!")
            
            cursor = connection.cursor(dictionary=True)
            
            # Test basic stats queries
            print("\n📊 Testing admin stats queries...")
            
            # Check users table
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
            print(f"📈 Total users: {total_users}")
            
            # Check premium users
            cursor.execute("SELECT COUNT(*) as premium_users FROM users WHERE is_premium = 1")
            premium_users = cursor.fetchone()['premium_users']
            print(f"💎 Premium users: {premium_users}")
            
            # Check recent signups (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) as recent_signups 
                FROM users 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            recent_signups = cursor.fetchone()['recent_signups']
            print(f"📅 Recent signups (30 days): {recent_signups}")
            
            # Get sample users for admin dashboard
            cursor.execute("""
                SELECT id, email, is_premium, subscription_type, created_at, is_banned, is_disabled
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            sample_users = cursor.fetchall()
            
            print(f"\n👥 Sample users for admin dashboard:")
            for i, user in enumerate(sample_users, 1):
                print(f"   {i}. {user['email']} - Premium: {bool(user['is_premium'])} - Created: {user['created_at']}")
            
            # Test get_admin_stats function simulation
            stats = {
                'total_users': total_users,
                'premium_users': premium_users,
                'free_users': total_users - premium_users,
                'recent_signups': recent_signups,
                'active_sessions': 0,  # Would calculate from session_logs if exists
                'monthly_revenue': premium_users * 9.99  # Simplified calculation
            }
            
            print(f"\n🔧 Admin stats that would be returned:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            cursor.close()
            connection.close()
            
            print(f"\n✅ Admin dashboard should now work correctly!")
            print(f"💡 The get_admin_stats() function should return {total_users} users")
            
            return True
            
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_admin_connection()
    if success:
        print(f"\n🎉 SUCCESS! Your admin dashboard should now display users correctly.")
        print(f"📋 Next steps:")
        print(f"   1. Start your FastAPI app: python app.py")
        print(f"   2. Login as admin: r.taylor289@gmail.com")
        print(f"   3. Visit: http://localhost:8000/admin")
    else:
        print(f"\n💥 There are still database connection issues that need to be resolved.")
