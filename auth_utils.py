import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Debug: confirm environment variables loaded correctly
# print("DB user:", os.getenv("DB_USER"))
# print("DB pass:", os.getenv("DB_PASS"))
# print("DB name:", os.getenv("DB_NAME"))

def verify_user(username: str, password: str) -> bool:
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        print("🔎 User from DB:", user)  # Debug output

        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            print("✅ Password verified")
            return True

        print("❌ Invalid credentials")  # Debug output
        return False

    except Exception as e:
        print("Login error:", e)
        return False

def create_user(username: str, email: str, password: str) -> bool:
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            print(f"Username '{username}' already exists.")
            return False

        # Check if email already exists
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            print(f"Email '{email}' already exists.")
            return False

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert the new user with email and default is_premium
        # Ensure column names (username, email, password_hash, is_premium) match your DB schema
        query = "INSERT INTO users (username, email, password_hash, is_premium) VALUES (%s, %s, %s, %s)"
        cursor.execute(
            query,
            (username, email, hashed_password.decode('utf-8'), 0) # Add email and default is_premium=0
        )
        conn.commit()
        print(f"User '{username}' created successfully.")
        return True

    except mysql.connector.Error as err:
        print(f"Database error during user creation: {err}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during user creation: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
