import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Debug: confirm environment variables loaded correctly
# print("DB user:", os.getenv("DB_USER"))
# print("DB pass:", os.getenv("DB_PASS"))
# print("DB name:", os.getenv("DB_NAME"))

# Predefined security questions
SECURITY_QUESTIONS = [
    "What was your first pet's name?",
    "What is your mother's maiden name?",
    "What was the name of your elementary school?",
    "In what city were you born?",
    "What is your favorite book?",
]

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
        print("🔎 User from DB:", user)

        cursor.close()
        conn.close()

        if not user:
            print("❌ No user found with that username")
            return False

        stored_hash = user['password_hash']
        print(f"🔐 Entered password (raw): {password}")
        print(f"🔐 Stored hash: {stored_hash}")
        print("🔐 bcrypt.checkpw result:", bcrypt.checkpw(password.encode(), stored_hash.encode()))

        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            print("✅ Password verified")
            return True

        print("❌ bcrypt check failed")
        return False

    except Exception as e:
        print("🔥 Login error:", e)
        return False

# Updated function signature to include security questions and answers
def create_user(username: str, email: str, password: str, q1: str, a1: str, q2: str, a2: str) -> bool:
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

        # Check if username or email already exists
        cursor.execute("SELECT username, email FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        if existing_user:
            if existing_user[0] == username:
                print(f"Username '{username}' already exists.")
            if existing_user[1] == email:
                 print(f"Email '{email}' already exists.")
            return False  # Already exists

        # Hash the password
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Hash the security answers
        hashed_a1 = bcrypt.hashpw(a1.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        hashed_a2 = bcrypt.hashpw(a2.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert new user with security questions and hashed answers
        query = """
            INSERT INTO users (
                username, password_hash, email, is_premium,
                security_question_1, security_answer_1_hash,
                security_question_2, security_answer_2_hash,
                reset_attempts  -- Initialize reset_attempts
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            query,
            (
                username, hashed_pw, email, 0, # Set is_premium to 0
                q1, hashed_a1, q2, hashed_a2,
                0 # Initialize reset_attempts to 0
            )
        )
        conn.commit()
        print(f"User '{username}' created successfully with security questions.")
        # print("✅ Hashed password stored:", hashed_pw) # Optional debug line
        return True

    except mysql.connector.Error as err:
        print(f"⚠️ Error in create_user: {err}") # Updated error message
        return False
    except Exception as e:
        print(f"⚠️ Error in create_user: {e}") # Updated error message
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
