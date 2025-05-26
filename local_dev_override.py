#!/usr/bin/env python3
"""
Local development database override for testing admin dashboard
This file provides mock data when local MySQL connection fails
"""

import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta

def get_mock_admin_data():
    """
    Return mock admin data for local development when database is unavailable
    """
    mock_stats = {
        'total_users': 25,
        'premium_users': 8,
        'free_users': 17,
        'recent_signups': 5,
        'active_sessions': 12,
        'monthly_revenue': 79.92
    }
    
    mock_users = [
        {
            'id': 1,
            'email': 'r.taylor289@gmail.com',
            'display_name': 'Rob Taylor',
            'is_premium': 1,
            'subscription_type': 'annual',
            'subscription_status': 'active',
            'created_at': datetime.now() - timedelta(days=30),
            'is_banned': 0,
            'is_disabled': 0,
            'failed_logins': 0,
            'current_period_end': datetime.now() + timedelta(days=335)
        },
        {
            'id': 2,
            'email': 'user1@example.com',
            'display_name': 'Test User 1',
            'is_premium': 1,
            'subscription_type': 'monthly',
            'subscription_status': 'active',
            'created_at': datetime.now() - timedelta(days=15),
            'is_banned': 0,
            'is_disabled': 0,
            'failed_logins': 0,
            'current_period_end': datetime.now() + timedelta(days=15)
        },
        {
            'id': 3,
            'email': 'user2@example.com',
            'display_name': 'Test User 2',
            'is_premium': 0,
            'subscription_type': None,
            'subscription_status': None,
            'created_at': datetime.now() - timedelta(days=5),
            'is_banned': 0,
            'is_disabled': 0,
            'failed_logins': 2,
            'current_period_end': None
        },
        {
            'id': 4,
            'email': 'banned@example.com',
            'display_name': 'Banned User',
            'is_premium': 0,
            'subscription_type': None,
            'subscription_status': None,
            'created_at': datetime.now() - timedelta(days=60),
            'is_banned': 1,
            'is_disabled': 0,
            'failed_logins': 5,
            'current_period_end': None
        },
        {
            'id': 5,
            'email': 'disabled@example.com',
            'display_name': 'Disabled User',
            'is_premium': 0,
            'subscription_type': None,
            'subscription_status': None,
            'created_at': datetime.now() - timedelta(days=45),
            'is_banned': 0,
            'is_disabled': 1,
            'failed_logins': 3,
            'current_period_end': None
        }
    ]
    
    return mock_stats, mock_users

def test_local_connection():
    """
    Test if local MySQL connection works, return True if successful
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASS', 'AppUser123!'),
            database=os.getenv('DB_NAME', 'cricket_auth')
        )
        if connection.is_connected():
            connection.close()
            return True
    except Error:
        return False
    except Exception:
        return False
    
    return False

def get_local_admin_stats():
    """
    Get admin stats - use real database if available, otherwise use mock data
    """
    if test_local_connection():
        print("🔗 Using real database connection for admin stats")
        # Import the real function from auth_utils
        try:
            from auth_utils import get_admin_stats
            return get_admin_stats()
        except Exception as e:
            print(f"⚠️  Error calling real get_admin_stats: {e}")
            print("🔄 Falling back to mock data")
            return get_mock_admin_data()
    else:
        print("🧪 Using mock data for local development (MySQL connection failed)")
        return get_mock_admin_data()

if __name__ == "__main__":
    print("🔍 Testing local development admin data...")
    try:
        stats, users = get_local_admin_stats()
        print(f"📊 Stats: {stats}")
        print(f"👥 Users: {len(users)} users loaded")
        for user in users[:3]:
            print(f"   - {user['email']} (Premium: {bool(user['is_premium'])})")
        print("✅ Local development override working successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
