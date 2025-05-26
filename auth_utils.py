import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv
import stripe # Import stripe
from datetime import datetime # Add datetime import for log_action

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

        # --- Add Banned/Disabled Check ---
        if user.get("is_banned"):
            print(f"⛔ Login failed for {email}: User is banned.")
            return False
        if user.get("is_disabled"):
            print(f"⚠️ Login failed for {email}: User is disabled.")
            return False
        # --- End Banned/Disabled Check ---

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
        # Ensure initial connection is closed using the updated conditions
        if cursor: # Changed condition
             cursor.close()
        if conn and conn.is_connected(): # Changed condition
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

# --- Admin Functions ---

def get_admin_stats():
    """Fetches statistics and user details for the admin dashboard."""
    stats = {
        "total_users": 0,
        "premium_users": 0,
        "active_sessions": 0,
        "monthly_revenue": 0,
        "missing_stripe_id": 0,
        "monthly_subs": 0,
        "annual_subs": 0,
        # Add keys for new session stats
        "total_sessions": 0,
        "avg_duration": 0,
        "most_active_users": [],
    }
    users = []
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True) # Keep dictionary=True for user list        # --- Existing User Stats ---
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        if result: 
            stats["total_users"] = result["count"]

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_premium = 1")
        result = cursor.fetchone()
        if result: 
            stats["premium_users"] = result["count"]

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE stripe_customer_id IS NULL OR stripe_customer_id = ''")
        result = cursor.fetchone()
        if result: 
            stats["missing_stripe_id"] = result["count"]

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE subscription_type = 'monthly'")
        result = cursor.fetchone()
        if result: 
            stats["monthly_subs"] = result["count"]

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE subscription_type = 'annual'")
        result = cursor.fetchone()
        if result: 
            stats["annual_subs"] = result["count"]        # Calculate monthly revenue using correct GBP pricing
        # Monthly: £5.00 GBP per month, Annual: £49.99 GBP per year (convert to monthly equivalent)
        monthly_revenue = (stats["monthly_subs"] * 5.00) + (stats["annual_subs"] * (49.99 / 12))
        stats["monthly_revenue"] = round(monthly_revenue, 2)# For active_sessions, let's count unique users from session_logs in last 30 days
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT email) as count 
                FROM session_logs 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND email IS NOT NULL
            """)
            result = cursor.fetchone()
            if result: 
                stats["active_sessions"] = result["count"]
            else:
                stats["active_sessions"] = 0
        except mysql.connector.Error:
            # session_logs table might not exist
            stats["active_sessions"] = 0

        # --- New Session Stats ---
        # Use a standard cursor (or fetch specific columns) for session stats if dictionary=True causes issues
        # Re-creating cursor without dictionary=True for session stats
        if cursor: cursor.close()
        cursor = conn.cursor() # Standard cursor for session stats

        try:
            cursor.execute("SELECT COUNT(*) FROM session_logs")
            result = cursor.fetchone()
            stats["total_sessions"] = result[0] if result else 0

            cursor.execute("SELECT AVG(duration_seconds) FROM session_logs")
            result = cursor.fetchone()
            # Handle potential None if table is empty, round the average
            stats["avg_duration"] = round(result[0] or 0)

            # Fetch most active users (returns list of tuples: (email, count))
            cursor.execute("""
                SELECT email, COUNT(*) AS count
                FROM session_logs
                WHERE email IS NOT NULL  /* Exclude null emails if necessary */
                GROUP BY email
                ORDER BY count DESC
                LIMIT 5
            """)
            # Convert list of tuples to list of dicts for easier template access
            most_active_raw = cursor.fetchall()
            stats["most_active_users"] = [{"email": email, "count": count} for email, count in most_active_raw]
        except mysql.connector.Error:
            # session_logs table might not exist
            stats["total_sessions"] = 0
            stats["avg_duration"] = 0
            stats["most_active_users"] = []

        # Re-create dictionary cursor for fetching user details
        if cursor: cursor.close()
        cursor = conn.cursor(dictionary=True)

        # --- Get User Details (Existing) ---
        cursor.execute("""
            SELECT email, created_at, is_premium, stripe_customer_id, reset_attempts,
                   subscription_type, subscription_status, current_period_end,
                   is_disabled, is_banned
            FROM users
            ORDER BY created_at DESC
        """)
        users = cursor.fetchall()

        # Format dates (Existing)
        for user in users:
            # ... existing date formatting ...
            if user.get('created_at'):
                 user['created_at_formatted'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
            if user.get('current_period_end'):
                 user['current_period_end_formatted'] = user['current_period_end'].strftime('%Y-%m-%d')
            else:
                 user['current_period_end_formatted'] = 'N/A'


    except mysql.connector.Error as err:
        print(f"🔥 Admin Stats DB Error: {err}")
        # Return empty/default stats on error
        stats = {k: 'Error' for k in stats}
        users = []
    except Exception as e:
        print(f"🔥 Admin Stats Unexpected Error: {e}")
        stats = {k: 'Error' for k in stats}
        users = []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Return updated stats dictionary and users list
    return stats, users

# --- End Admin Functions ---

# --- User Status Update Function ---

def update_user_status(email: str, status_field: str, value: bool):
    """Updates a user's status field (is_banned or is_disabled) in the database."""
    if status_field not in ["is_banned", "is_disabled"]:
        print(f"⚠️ Invalid status field provided: {status_field}")
        return False # Or raise an error

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

        # Construct the query safely - DO NOT use f-strings directly with SQL field names if they came from user input
        # Since status_field is validated against a known list, this is safe here.
        query = f"UPDATE users SET {status_field} = %s WHERE email = %s"
        params = (int(value), email) # Convert boolean to integer for DB

        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ User '{email}' status updated: {status_field} set to {value}")
            return True
        else:
            print(f"⚠️ User '{email}' not found or status already set.")
            return False # Indicate user not found or no change needed

    except mysql.connector.Error as err:
        print(f"🔥 DB Error updating status for {email}: {err}")
        return False
    except Exception as e:
        print(f"🔥 Unexpected error updating status for {email}: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End User Status Update Function ---

# --- Admin Password Reset Function ---

def admin_reset_password(email: str, new_password: str) -> bool: # Add new_password parameter
    """Hashes the provided new password and updates the user's record."""
    conn = None
    cursor = None
    try:
        # Remove password generation
        # alphabet = string.ascii_letters + string.digits + string.punctuation
        # temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        # print(f"ℹ️ Generated temporary password for {email} (length {len(temp_password)}) - Not logging the password itself.")

        # Hash the provided new password
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # Update password_hash and reset attempts
        query = "UPDATE users SET password_hash = %s, reset_attempts = 0 WHERE email = %s"
        params = (hashed_pw, email)

        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ Password hash updated successfully by admin for user '{email}'.")
            return True
        else:
            print(f"⚠️ User '{email}' not found for admin password reset.")
            return False

    except mysql.connector.Error as err:
        print(f"🔥 DB Error during admin password reset for {email}: {err}")
        return False
    except Exception as e:
        print(f"🔥 Unexpected error during admin password reset for {email}: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Admin Password Reset Function ---

# --- Add Audit Log Helper ---
def log_action(email: str, action: str, details: str = ""):
    """Logs an action to the audit_logs table."""
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
        cursor.execute(
            "INSERT INTO audit_logs (email, action, details, timestamp) VALUES (%s, %s, %s, %s)",
            (email, action, details, datetime.now()) # Add timestamp
        )
        conn.commit()
    except mysql.connector.Error as db_err:
        print(f"❌ Audit log DB error: {db_err}")
    except Exception as e:
        print(f"❌ Audit log failed: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
# --- End Audit Log Helper ---
