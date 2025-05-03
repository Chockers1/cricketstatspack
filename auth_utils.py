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

# Updated function signature to use email
def verify_user(email: str, password: str) -> bool:
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )

        cursor = conn.cursor(dictionary=True)
        # Updated query to use email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        print("🔎 User from DB (by email):", user) # Updated print statement

        cursor.close()
        conn.close()

        if not user:
            # Updated print statement
            print(f"❌ No user found with email: {email}")
            return False

        stored_hash = user['password_hash']
        # Keep password logging as is, or update context if desired
        print(f"🔐 Entered password (raw) for email {email}: {password}")
        print(f"🔐 Stored hash: {stored_hash}")
        print("🔐 bcrypt.checkpw result:", bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))) # Ensure encoding

        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')): # Ensure encoding
            print(f"✅ Password verified for email: {email}") # Updated print statement
            return True

        print(f"❌ bcrypt check failed for email: {email}") # Updated print statement
        return False

    except Exception as e:
        # Updated print statement
        print(f"🔥 Login error for email {email}: {e}")
        return False

# Updated function signature to remove username
def create_user(email: str, password: str, q1: str, a1: str, q2: str, a2: str) -> bool:
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True) # Use dictionary cursor for fetchone

        # Check if email already exists
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            print(f"Email '{email}' already exists.")
            return False  # Already exists

        # Hash the password
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Hash the security answers
        hashed_a1 = bcrypt.hashpw(a1.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        hashed_a2 = bcrypt.hashpw(a2.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert new user - removed username column
        # Assuming 'username' column is removed or allows NULL if kept for other reasons.
        # If 'username' MUST be unique and non-null, you might need to generate one or use email.
        # For now, assuming it's removed from the INSERT. Adjust if schema differs.
        query = """
            INSERT INTO users (
                password_hash, email, is_premium,
                security_question_1, security_answer_1_hash,
                security_question_2, security_answer_2_hash,
                reset_attempts
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Execute without username
        cursor.execute(
            query,
            (
                hashed_pw, email, 0, # Set is_premium to 0
                q1, hashed_a1, q2, hashed_a2,
                0 # Initialize reset_attempts to 0
            )
        )
        conn.commit()
        print(f"User with email '{email}' created successfully with security questions.")
        return True

    except mysql.connector.Error as err:
        print(f"⚠️ Error in create_user: {err}")
        return False
    except Exception as e:
        print(f"⚠️ Error in create_user: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
