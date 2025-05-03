import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv
import stripe # Import stripe

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
    conn = None # Define conn and cursor outside try for broader scope if needed later
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )

        cursor = conn.cursor(dictionary=True)
        # Updated query to use email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,)) # Fetch all columns including stripe_customer_id and is_premium
        user = cursor.fetchone()
        print("🔎 User from DB (by email):", user) # Updated print statement

        # Close initial DB connection here as it's no longer needed for the primary check
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

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

            # --- Add Stripe Fallback Check ---
            try:
                stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

                # Lookup user subscription by customer ID
                customer_id = user.get("stripe_customer_id") # Assumes 'stripe_customer_id' column exists

                if customer_id:
                    print(f"ℹ️ Found Stripe Customer ID: {customer_id} for email {email}. Checking active subscriptions...")
                    subscriptions = stripe.Subscription.list(customer=customer_id, status="active", limit=1) # Limit 1 is enough

                    is_premium_stripe = len(subscriptions.data) > 0
                    is_premium_db = bool(user.get("is_premium")) # Ensure DB value is boolean

                    print(f"🔁 Stripe check: email {email} premium = {is_premium_stripe} (DB was {is_premium_db})")

                    if is_premium_stripe != is_premium_db:
                        print(f"⚠️ Discrepancy found! Updating DB for {email} to is_premium={is_premium_stripe}")
                        # Update DB if status changed - requires new connection
                        update_conn = None
                        update_cursor = None
                        try:
                            update_conn = mysql.connector.connect(
                                host=os.getenv("DB_HOST"),
                                user=os.getenv("DB_USER"),
                                password=os.getenv("DB_PASS"),
                                database=os.getenv("DB_NAME")
                            )
                            update_cursor = update_conn.cursor()
                            # Use email from the 'user' dict which is confirmed to exist
                            update_cursor.execute("UPDATE users SET is_premium = %s WHERE email = %s", (int(is_premium_stripe), user["email"]))
                            update_conn.commit()
                            print(f"✅ DB updated successfully for {email}.")
                        except mysql.connector.Error as db_err:
                            print(f"🔥 DB Update Error during Stripe fallback check for {email}: {db_err}")
                        finally:
                            if update_cursor: update_cursor.close()
                            if update_conn and update_conn.is_connected(): update_conn.close()
                else:
                    print(f"ℹ️ No Stripe Customer ID found for email {email}. Skipping Stripe status check.")

            except stripe.error.StripeError as stripe_err:
                 print(f"🔥 Stripe API Error during fallback check for {email}: {stripe_err}")
            except Exception as fallback_err:
                 print(f"🔥 Unexpected Error during Stripe fallback check for {email}: {fallback_err}")
            # --- End Stripe Fallback Check ---

            return True # Return True since password was verified

        print(f"❌ bcrypt check failed for email: {email}") # Updated print statement
        return False

    except mysql.connector.Error as initial_db_err: # Catch initial DB connection/query errors
        print(f"🔥 Initial DB connection/query error for email {email}: {initial_db_err}")
        return False
    except Exception as e:
        # Updated print statement
        print(f"🔥 Login error for email {email}: {e}")
        return False
    finally:
        # Ensure initial connection is closed if it was opened and not closed earlier
        if cursor and not cursor.is_closed():
             cursor.close()
        if conn and conn.is_connected():
             conn.close()

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
            print(f"Email '{email}' already exists.") # Already correct
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
        print(f"User with email '{email}' created successfully with security questions.") # Already correct
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
