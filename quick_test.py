#!/usr/bin/env python3
"""
Quick test with root credentials
"""
import mysql.connector
from mysql.connector import Error

print("🔍 Testing MySQL connection with root credentials...")

try:
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='AppUser123!',
        database='cricket_auth'
    )
    
    if connection.is_connected():
        print("✅ SUCCESS! Connected to MySQL with root credentials")
        
        cursor = connection.cursor()
        
        # Check if cricket_auth database exists and has users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()
        print(f"👥 Users in database: {user_count[0]}")
        
        if user_count[0] > 0:
            cursor.execute("SELECT id, email, is_premium, created_at FROM users LIMIT 5")
            users = cursor.fetchall()
            print("📝 Sample users:")
            for user in users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Premium: {user[2]}, Created: {user[3]}")
        
        cursor.close()
        connection.close()
        
        print("\n🎉 Database connection working! The admin dashboard should work now.")
        
except Error as e:
    print(f"❌ Connection failed: {e}")
    
    if "cricket_auth" in str(e):
        print("💡 The cricket_auth database doesn't exist. You may need to create it.")
    elif "Access denied" in str(e):
        print("💡 The password might be incorrect. Please verify the root password.")
    else:
        print("💡 Check if MySQL service is running and try again.")

print("✅ Test complete!")
