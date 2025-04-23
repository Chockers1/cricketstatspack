import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Debug: confirm environment variables loaded correctly
print("DB user:", os.getenv("DB_USER"))
print("DB pass:", os.getenv("DB_PASS"))
print("DB name:", os.getenv("DB_NAME"))

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
