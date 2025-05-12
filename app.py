import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException
# Add JSONResponse import
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
# Add BaseHTTPMiddleware import
from starlette.middleware.base import BaseHTTPMiddleware
# Add timedelta for lockout calculation
from datetime import datetime, timedelta
import mysql.connector
import bcrypt # Ensure bcrypt is imported
from typing import Optional # Import Optional for optional form fields
import csv
from io import StringIO
# Add slowapi imports
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# Import limiter decorator specifically if needed (or use app.state.limiter)
# from slowapi.decorator import limiter # Not strictly needed if using app.state.limiter

# Import stripe
import stripe
import traceback # Add this import

# Import the new admin function, status update function, and reset function
# Add log_action to the imports
from auth_utils import verify_user, create_user, get_admin_stats, update_user_status, admin_reset_password, log_action
from stripe_payments import router as stripe_payments_router # Add this import
from stripe_webhook import router as stripe_webhook_router # Add this import

print("🔥 FASTAPI LOADED 🔥")

load_dotenv()  # loads .env into os.environ


# Define PageViewLoggerMiddleware
class PageViewLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Process the request first to get the response
        response = await call_next(request)

        # Log page view after the request is processed
        try:
            path = request.url.path
            ip = request.client.host if request.client else "unknown" # Handle cases where client might be None
            session = request.session
            # Use 'user_id' as the session key for email, consistent with the rest of the app
            email = session.get("user_id")

            # Avoid logging static file requests or webhook requests if desired
            if path.startswith("/static") or path == "/api/webhook":
                 return response

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
                    "INSERT INTO page_views (email, path, ip_address, timestamp) VALUES (%s, %s, %s, %s)",
                    # Add timestamp
                    (email, path, ip, datetime.now())
                )
                conn.commit()
            except mysql.connector.Error as db_err:
                 print(f"⚠️ DB Error logging page view: {db_err}")
            except Exception as inner_e:
                 print(f"⚠️ Inner Exception logging page view: {inner_e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

        except Exception as e:
            # Catch potential errors accessing request/session attributes
            print(f"⚠️ Failed to log page view (Outer Exception): {e}")

        return response

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
# Attach Limiter to App State
app.state.limiter = limiter

# Add Rate Limit Exceeded Exception Handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"} # Include detail from exception
    )

# SECRET_KEY = os.getenv("SECRET_KEY", "replace-this-with-a-real-secret") # Remove this line

# Add Session Middleware:
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY) # Remove this line

# load your SECRET_KEY from the env
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("You must set SECRET_KEY in your .env before starting")

# install the middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Add Page View Logger Middleware (after SessionMiddleware to access session)
app.add_middleware(PageViewLoggerMiddleware)

# Include the Stripe payments router
app.include_router(stripe_payments_router) # Add this line
app.include_router(stripe_webhook_router) # Add this line

# your existing mounts & templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Stripe API key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Add datetimeformat filter for Jinja2
def datetimeformat(value):
    # Handles cases where value might be None or not a valid timestamp
    if value is None:
        return "N/A"
    try:
        return datetime.utcfromtimestamp(int(value)).strftime('%Y-%m-%d')
    except (TypeError, ValueError):
        return "Invalid Date"

templates.env.filters['datetimeformat'] = datetimeformat

# Copilot: add require_login dependency (Keep for potential future use, but remove from /dashboard)
def require_login(request: Request):
  # This function now might check request.session instead if needed elsewhere
  if not request.session.get("user_id"): # Example: Update to check session if used
      raise HTTPException(status_code=401, detail="Not authenticated")

# Home page (Updated as requested)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Simply render the public index
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

# ✅ Single, correct POST route for login (Updated for session and email)
@app.post("/login")
@limiter.limit("5/minute") # Apply rate limiting
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)): # Changed username to email
    print("🚨 Login POST received")

    conn = None
    cursor = None
    user_lock_data = None
    lockout_threshold = 5
    lockout_duration_minutes = 15

    try:
        # --- 1. Check for existing lock BEFORE verifying password ---
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email, failed_logins, lock_until FROM users WHERE email = %s", (email,))
        user_lock_data = cursor.fetchone()

        if user_lock_data:
            lock_until = user_lock_data.get("lock_until")
            # Check if account is locked
            if lock_until and datetime.now() < lock_until: # Use datetime.now() for comparison
                lock_remaining = lock_until - datetime.now()
                minutes_remaining = int(lock_remaining.total_seconds() / 60) + 1 # Round up minutes
                error_message = f"Account temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minute(s)."
                print(f"🔒 Login attempt failed for {email}: Account locked until {lock_until}")
                log_action(email, "LOGIN_FAILURE", "Account locked")
                return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=403) # Use 403 status

        # --- 2. Verify Password (if not locked) ---
        # verify_user handles password check, banned/disabled status, and Stripe fallback
        is_valid_user = verify_user(email, password)

        if is_valid_user:
            # --- 3. Login Success: Reset failures and proceed ---
            print(f"✅ Login success for {email} — redirecting to dashboard")
            log_action(email, "login", "User logged in successfully") # Already logging success

            # Reset failures and lock_until in DB
            if user_lock_data and user_lock_data.get("failed_logins", 0) > 0: # Only update if there were previous failures
                cursor.execute("UPDATE users SET failed_logins = 0, lock_until = NULL WHERE email = %s", (email,))
                conn.commit()
                print(f"🔄 Reset failed login attempts for {email}.")

            # Store session info
            request.session["user_id"] = email
            request.session["login_time"] = datetime.utcnow().isoformat() # Use UTCNow for consistency
            response = RedirectResponse(url="/dashboard", status_code=302)
            return response
        else:
            # --- 4. Login Failure: Increment failures, check for lockout ---
            print(f"❌ Login failed — invalid credentials or status for {email}")

            if user_lock_data: # User exists, password failed or user is banned/disabled
                current_failures = user_lock_data.get("failed_logins", 0)
                new_failures = current_failures + 1
                lock_until_update = user_lock_data.get("lock_until") # Keep existing lock if already set

                error_message = "Invalid login" # Default error

                if new_failures >= lockout_threshold:
                    # Lock the account if threshold reached
                    lock_until_update = datetime.now() + timedelta(minutes=lockout_duration_minutes)
                    error_message = f"Account locked due to too many failed attempts. Try again in {lockout_duration_minutes} minutes."
                    print(f"🚫 Account for {email} locked until {lock_until_update}")
                    log_action(email, "ACCOUNT_LOCKED", f"Locked after {new_failures} failed attempts")
                else:
                    # Log failed attempt without locking yet
                    log_action(email, "LOGIN_FAILURE", f"Invalid credentials/status ({new_failures} attempts)")

                # Update DB with new failure count and potential lock time
                cursor.execute(
                    "UPDATE users SET failed_logins = %s, lock_until = %s WHERE email = %s",
                    (new_failures, lock_until_update, email)
                )
                conn.commit()
                print(f"📈 Updated failed login attempts for {email} to {new_failures}.")
                # Return appropriate error message (locked or generic invalid)
                return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=401 if lock_until_update else 401) # Use 401 for invalid creds

            else: # User not found in DB at all
                log_action(email, "LOGIN_FAILURE", "User not found")
                return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"}, status_code=401)

    except mysql.connector.Error as db_err:
        print(f"🔥 DB Error during login for {email}: {db_err}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Database error during login."}, status_code=500)
    except Exception as e:
        print(f"🔥 Unexpected error during login for {email}: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "An unexpected error occurred."}, status_code=500)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# Registration page
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

# Registration submission (Updated for auto-login)
@app.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    security_question_1: str = Form(...),
    security_answer_1: str = Form(...),
    security_question_2: str = Form(...),
    security_answer_2: str = Form(...)
):
    # Try to create user
    success = create_user(
        email,
        password,
        security_question_1,
        security_answer_1,
        security_question_2,
        security_answer_2
    )

    if not success:
        print(f"❌ Registration failed for email '{email}' — email might already exist")
        log_action(email, "REGISTER_FAILURE", "Email already exists") # Log failure
        return templates.TemplateResponse("register.html", {
            "request": request,
            # Keep the specific error message
            "error": "An account with this email already exists."
        })

    # ✅ Auto-login the user after successful registration
    conn = None
    cursor = None
    try:
        print(f"✅ User with email '{email}' created successfully. Attempting auto-login...")
        log_action(email, "REGISTER_SUCCESS") # Log success
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        # Fetch necessary details for session (email, is_premium)
        cursor.execute("SELECT email, is_premium FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # Set session variables - Use 'user_id' for email as used elsewhere
            request.session["user_id"] = user["email"]
            # Initialize is_premium in session (will be refreshed by dashboard)
            request.session["is_premium"] = bool(user.get("is_premium", False))
            # Log auto-login after registration
            log_action(user["email"], "login", "User logged in successfully (auto-login after registration)")
            print(f"✅ Session set for auto-login: {user['email']}, Premium: {request.session['is_premium']}")
            # Redirect to dashboard after setting session
            return RedirectResponse("/dashboard", status_code=302)
        else:
            # Should not happen if create_user succeeded, but handle defensively
            print(f"⚠️ Auto-login failed: Could not fetch user '{email}' after creation.")
            # Redirect to login page as a fallback
            return RedirectResponse("/login", status_code=302)

    except mysql.connector.Error as err:
        print(f"🔥 DB Error during auto-login for {email}: {err}")
        # Redirect to login page on DB error
        return RedirectResponse("/login", status_code=302)
    except Exception as e:
        print(f"🔥 Unexpected Error during auto-login for {email}: {e}")
        # Redirect to login page on other errors
        return RedirectResponse("/login", status_code=302)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# Add the new subscribe route here
@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")
    # Pass Price IDs to the template context
    return templates.TemplateResponse("subscribe.html", {
        "request": request,
        "monthly_price_id": os.getenv("STRIPE_PRICE_ID_MONTHLY"),
        "annual_price_id": os.getenv("STRIPE_PRICE_ID_ANNUAL"),
    })


# Updated dashboard route to always check DB and update session using email
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("user_id"): # user_id now stores email
        return RedirectResponse("/login")

    email = request.session["user_id"] # Get email from session

    # 🔄 ALWAYS check DB for latest premium status using email
    import mysql.connector # Import locally as requested
    conn = None
    cursor = None
    user = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        # Query by email
        cursor.execute("SELECT is_premium FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # 🔁 Refresh premium status in session, ensuring it's a boolean
            request.session["is_premium"] = bool(user.get("is_premium"))
        else:
            # If user somehow not found in DB (though they are logged in), set premium to False
            print(f"⚠️ User with email {email} found in session but not in DB during dashboard load.")
            request.session["is_premium"] = False

    except mysql.connector.Error as err: # Catch specific DB errors
        print(f"🔥 Dashboard DB check failed for {email}: {err}")
        request.session["is_premium"] = request.session.get("is_premium", False)
    except Exception as e: # Catch other potential errors
        print(f"🔥 Dashboard DB check failed unexpectedly for {email}: {e}")
        request.session["is_premium"] = request.session.get("is_premium", False)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Render the dashboard template, which will now use the updated session value
    return templates.TemplateResponse("dashboard.html", {"request": request})


# Copilot: add logout endpoint (Updated for session)
@app.get("/logout")
async def logout(request: Request):
    # --- Add Session Duration Logging ---
    email = request.session.get("user_id") # Use 'user_id' key
    login_time_str = request.session.get("login_time")

    if email: # Log logout action if email exists in session
        # Update log_action call as requested and remove duplicate
        log_action(email, "logout", "User logged out")
        # log_action(email, "LOGOUT") # Remove duplicate

    if email and login_time_str:
        try:
            login_dt = datetime.fromisoformat(login_time_str)
            logout_dt = datetime.utcnow()
            duration = int((logout_dt - login_dt).total_seconds())

            # Log to database
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
                    "INSERT INTO session_logs (email, login_time, logout_time, duration_seconds) VALUES (%s, %s, %s, %s)",
                    (email, login_dt, logout_dt, duration)
                )
                conn.commit()
                print(f"✅ Logged session duration for {email}: {duration} seconds.")
            except mysql.connector.Error as db_err:
                print(f"❌ DB Error logging session duration for {email}: {db_err}")
            except Exception as log_e:
                print(f"❌ Failed to log session duration for {email}: {log_e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

        except ValueError:
            print(f"⚠️ Could not parse login_time '{login_time_str}' for user {email}.")
        except Exception as outer_e:
             print(f"❌ Unexpected error during session duration calculation for {email}: {outer_e}")
    else:
        print("ℹ️ Logout initiated but no email or login_time found in session to log duration.")
    # --- End Session Duration Logging ---

    # Clear the session
    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    # response.delete_cookie(key="logged_in") # Remove cookie deletion
    print("✅ Logout successful — redirecting to home")
    return response

@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

# --- Remove Forgot Password Routes ---
# The entire /forgot-password GET and POST routes are removed.
# --- End Remove Forgot Password Routes ---

# --- Security Question Verification Routes (Updated for Two-Step and Email) ---

@app.get("/verify-security", response_class=HTMLResponse)
async def verify_security_form(request: Request):
    # Renders the initial form asking for email only
    return templates.TemplateResponse("verify_security.html", {
        "request": request,
        "questions": None,
        "error": None,
        "email": None # Changed from username
    })

@app.post("/verify-security")
async def verify_security_submit(
    request: Request,
    email: str = Form(...), # Changed username to email
    answer1: Optional[str] = Form(None),
    answer2: Optional[str] = Form(None)
):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)

        # Fetch user data using email
        cursor.execute(
            "SELECT id, security_question_1, security_answer_1_hash, "
            "security_question_2, security_answer_2_hash, reset_attempts "
            "FROM users WHERE email = %s", (email,) # Query by email
        )
        user = cursor.fetchone()

        # Generic error for user not found or missing questions/hashes later
        generic_error = "Invalid email or answers." # Updated generic error

        if not user:
            print(f"Security verification step 1 failed: User not found - {email}")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "User not found") # Log failure
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email, # Pass email back
                "error": "User not found."
            }, status_code=404)

        # Check reset attempts *before* proceeding
        if user.get('reset_attempts', 0) >= 3:
            print(f"Security verification blocked for user {email} due to too many attempts.")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "Too many attempts") # Log failure
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email,
                "error": "Too many failed attempts. Please contact support."
            }, status_code=403)

        # Check if security questions/hashes exist in the user record
        q1 = user.get('security_question_1')
        sa1_hash = user.get('security_answer_1_hash')
        q2 = user.get('security_question_2')
        sa2_hash = user.get('security_answer_2_hash')

        if not q1 or not sa1_hash or not q2 or not sa2_hash:
            print(f"Security questions/hashes missing for user {email}.")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "Security questions not set up") # Log failure
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email,
                "error": "Security questions not set up for this account. Please contact support."
            }, status_code=400)

        # --- Logic based on whether answers were submitted ---

        if answer1 is None or answer2 is None:
            # Step 1 completed (email submitted), now show questions
            print(f"Security verification step 1 successful for {email}. Showing questions.")
            log_action(email, "RESET_PASSWORD_VERIFY_STEP1_SUCCESS") # Log step 1 success
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": [q1, q2],
                "email": email, # Pass email to keep it in the form (readonly)
                "error": None
            })
        else:
            # Step 2: Answers submitted, verify them
            correct1 = bcrypt.checkpw(answer1.encode('utf-8'), sa1_hash.encode('utf-8'))
            correct2 = bcrypt.checkpw(answer2.encode('utf-8'), sa2_hash.encode('utf-8'))

            if correct1 and correct2:
                print(f"Security verification step 2 successful for user: {email}")
                log_action(email, "RESET_PASSWORD_VERIFY_STEP2_SUCCESS") # Log step 2 success
                cursor.execute("UPDATE users SET reset_attempts = 0 WHERE id = %s", (user['id'],))
                conn.commit()

                # Store email in session for the reset step
                request.session['reset_user'] = email # Store email
                return RedirectResponse("/reset-password", status_code=302)
            else:
                print(f"Security verification step 2 failed for user: {email}")
                log_action(email, "RESET_PASSWORD_VERIFY_STEP2_FAILURE", "Incorrect answers") # Log step 2 failure
                cursor.execute("UPDATE users SET reset_attempts = reset_attempts + 1 WHERE id = %s", (user['id'],))
                conn.commit()
                return templates.TemplateResponse("verify_security.html", {
                    "request": request,
                    "questions": [q1, q2],
                    "email": email,
                    "error": "Incorrect answers. Please try again."
                }, status_code=400)

    except mysql.connector.Error as err:
        print(f"Database error during security verification for {email}: {err}")
        show_questions = [user.get('security_question_1'), user.get('security_question_2')] if user and answer1 is not None else None
        return templates.TemplateResponse("verify_security.html", {
            "request": request, "questions": show_questions, "email": email, "error": "A database error occurred."
        }, status_code=500)
    except Exception as e:
        print(f"Unexpected error during security verification for {email}: {e}")
        show_questions = [user.get('security_question_1'), user.get('security_question_2')] if user and answer1 is not None else None
        return templates.TemplateResponse("verify_security.html", {
            "request": request, "questions": show_questions, "email": email, "error": "An unexpected error occurred."
        }, status_code=500)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# --- End Security Question Verification Routes ---


# --- Form-Based Reset Password Routes (Updated for Session Verification and Email) ---

# GET /reset-password
@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request):
    # Check if user email has passed security verification via session
    if 'reset_user' not in request.session: # reset_user now stores email
        print("Access denied to /reset-password GET: No 'reset_user' (email) in session.")
        return RedirectResponse("/verify-security", status_code=303)

    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None})

# POST /reset-password
@app.post("/reset-password")
async def reset_password_submit(request: Request, new_password: str = Form(...), confirm_password: str = Form(...)):
    # Double-check session key existence on POST
    if 'reset_user' not in request.session:
        print("Access denied to /reset-password POST: No 'reset_user' (email) in session.")
        # No email to log here reliably
        return RedirectResponse("/verify-security", status_code=303)

    email = request.session['reset_user'] # Get email from session

    # 1. Check if passwords match
    if new_password != confirm_password:
        print(f"Password mismatch for user {email} during reset attempt.")
        log_action(email, "RESET_PASSWORD_FAILURE", "Passwords do not match") # Log failure
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "Passwords do not match."
        }, status_code=400)

    # Optional: Basic password validation
    if len(new_password) < 8:
         print(f"Password too short for user {email} during reset attempt.")
         log_action(email, "RESET_PASSWORD_FAILURE", "Password too short") # Log failure
         return templates.TemplateResponse("reset_password.html", {
             "request": request, "error": "Password must be at least 8 characters long."
         }, status_code=400)

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # 2. Hash the new password
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 3. Update password_hash in the database using email from session
        update_query = "UPDATE users SET password_hash = %s WHERE email = %s" # Update by email
        cursor.execute(update_query, (hashed_pw, email))
        conn.commit()

        # Check if the update was successful
        if cursor.rowcount == 1:
            print(f"Password successfully reset for email: {email}")
            # Update log_action call as requested
            log_action(email, "password_reset", "User successfully reset their password")
            request.session.pop('reset_user', None)
            return RedirectResponse("/reset-password-success", status_code=302)
        else:
            # This case is unlikely if the session key was valid, but handle it.
            print(f"Password reset failed for email: {email}. User might no longer exist.")
            log_action(email, "RESET_PASSWORD_FAILURE", "User not found during update") # Keep failure log
            request.session.pop('reset_user', None)
            return templates.TemplateResponse("reset_password.html", {
                "request": request, "error": "Could not update password. User may not exist.",
            }, status_code=404)

    except mysql.connector.Error as err:
        print(f"Database error during password reset for email {email}: {err}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "A database error occurred. Please try again.",
        }, status_code=500)
    except Exception as e:
        print(f"Unexpected error during password reset for email {email}: {e}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "An unexpected error occurred. Please try again.",
        }, status_code=500)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# --- End Reset Password Routes ---

# --- Reset Password Success Route ---

@app.get("/reset-password-success", response_class=HTMLResponse)
async def reset_password_success(request: Request):
    # Renders a simple success page after password reset
    return templates.TemplateResponse("reset_password_success.html", {"request": request})

# --- End Reset Password Success Route ---


# --- Change Password Routes (Updated for Email) ---

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_form(request: Request):
    # Check if user is logged in (session user_id is email)
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    # Render the change password form
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})


@app.post("/change-password")
async def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    # Check if user is logged in
    if not request.session.get("user_id"): # user_id is email
        # No email to log here reliably
        return RedirectResponse("/login", status_code=303)

    email = request.session["user_id"] # Get email from session

    # 1. Verify current password using email
    if not verify_user(email, current_password):
        print(f"Change password failed for {email}: Incorrect current password.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "Incorrect current password") # Log failure
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "Current password is incorrect.", "success": None
        }, status_code=400)

    # 2. Check if new passwords match
    if new_password != confirm_password:
        print(f"Change password failed for {email}: New passwords do not match.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "New passwords do not match") # Log failure
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "New passwords do not match.", "success": None
        }, status_code=400)

    # 3. Optional: Basic password validation
    if len(new_password) < 8:
         print(f"Change password failed for {email}: New password too short.")
         log_action(email, "CHANGE_PASSWORD_FAILURE", "New password too short") # Log failure
         return templates.TemplateResponse("change_password.html", {
             "request": request, "error": "New password must be at least 8 characters long.", "success": None
         }, status_code=400)

    # 4. Optional: Check if new password is the same as the old one
    if current_password == new_password:
        print(f"Change password failed for {email}: New password is the same as the current one.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "New password same as current") # Log failure
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "New password cannot be the same as the current password.", "success": None
        }, status_code=400)


    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # 5. Hash the new password
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 6. Update password_hash in the database using email
        update_query = "UPDATE users SET password_hash = %s WHERE email = %s" # Update by email
        cursor.execute(update_query, (hashed_pw, email))
        conn.commit()

        # Check if the update was successful
        if cursor.rowcount == 1:
            print(f"Password successfully changed for email: {email}")
            log_action(email, "CHANGE_PASSWORD_SUCCESS") # Log success
            return templates.TemplateResponse("change_password.html", {
                "request": request, "error": None, "success": "Password changed successfully!"
            })
        else:
            # This case is unlikely after verification, but handle it.
            print(f"Password change failed unexpectedly for email: {email} after verification.")
            log_action(email, "CHANGE_PASSWORD_FAILURE", "Unexpected update error") # Log failure
            return templates.TemplateResponse("change_password.html", {
                "request": request, "error": "An unexpected error occurred during password update.", "success": None
            }, status_code=500)

    except mysql.connector.Error as err:
        print(f"Database error during password change for email {email}: {err}")
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "A database error occurred. Please try again.", "success": None
        }, status_code=500)
    except Exception as e:
        print(f"Unexpected error during password change for email {email}: {e}")
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "An unexpected error occurred. Please try again.", "success": None
        }, status_code=500)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# --- End Change Password Routes ---

# --- REMOVE Forgot Username Routes ---

# @app.get("/forgot-username", response_class=HTMLResponse)
# async def forgot_username_form(request: Request):
#     # Renders the form asking for the user's email
#     return templates.TemplateResponse("forgot_username.html", {"request": request})
#
#
# @app.post("/forgot-username") # Removed response_class=HTMLResponse, uses TemplateResponse
# async def forgot_username_submit(request: Request, email: str = Form(...)):
#     # ... (implementation removed) ...
#     return templates.TemplateResponse("forgot_username_result.html", {
#         "request": request
#     })

# --- End Forgot Username Routes ---


# --- Admin Dashboard Route ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Check session for user_id (which holds the email)
    user_email = request.session.get("user_id")
    # Simple check against a hardcoded admin email
    if user_email != "r.taylor289@gmail.com": # Consider using os.getenv("ADMIN_EMAIL") here too
        print(f"🚨 Unauthorized access attempt to /admin by: {user_email or 'Not logged in'}")
        raise HTTPException(status_code=403, detail="Access denied")

    print(f"✅ Admin access granted to: {user_email}")
    # Fetch stats and user data (get_admin_stats now includes session stats)
    stats, users = get_admin_stats()

    # Render the admin template, passing the entire stats dictionary
    # The 'stats' dictionary already contains total_sessions, avg_duration, and most_active_users
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "stats": stats, # This dictionary includes the new session stats
        "users": users
    })

# --- End Admin Dashboard Route ---


# --- Admin Action Routes ---

# Helper function for admin check (to avoid repetition)
def verify_admin(request: Request):
    user_email = request.session.get("user_id")
    admin_email_env = os.getenv("ADMIN_EMAIL", "r.taylor289@gmail.com") # Use env var or default
    if user_email != admin_email_env:
        print(f"🚨 Unauthorized access attempt to admin action by: {user_email or 'Not logged in'}")
        # Log unauthorized attempt if possible (might not have email if not logged in)
        log_action(user_email or "UNKNOWN", "ADMIN_ACTION_UNAUTHORIZED", f"Attempted action on path: {request.url.path}")
        raise HTTPException(status_code=403, detail="Access denied")
    print(f"✅ Admin action authorized for: {user_email}")
    return user_email # Return email if verified

@app.post("/admin/ban")
async def ban_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request) # Check if admin and get admin email
    target_email = email # Use the form email as target_email
    if update_user_status(email, "is_banned", True):
        print(f"✅ User '{email}' banned successfully by {admin_email}.")
        # Update log_action call as requested
        log_action(admin_email, "ban_user", f"Banned user: {target_email}")
    else:
        print(f"⚠️ Failed to ban user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_BAN_USER_FAILURE", f"Target: {target_email}") # Keep failure log
    return RedirectResponse("/admin", status_code=302)

@app.post("/admin/disable")
async def disable_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request) # Check if admin and get admin email
    if update_user_status(email, "is_disabled", True):
         print(f"✅ User '{email}' disabled successfully by {admin_email}.")
         log_action(admin_email, "ADMIN_DISABLE_USER", f"Target: {email}") # Log action
         # Also ensure banned status is not conflicting if needed (e.g., disable implies not banned)
         # update_user_status(email, "is_banned", False) # Optional: Ensure ban is removed if disabling
    else:
         print(f"⚠️ Failed to disable user '{email}' by {admin_email}.")
         log_action(admin_email, "ADMIN_DISABLE_USER_FAILURE", f"Target: {email}") # Log failure
    return RedirectResponse("/admin", status_code=302)

@app.post("/admin/enable")
async def enable_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request) # Check if admin and get admin email
    # This correctly enables the user by setting is_disabled to False (0 in DB)
    if update_user_status(email, "is_disabled", False):
        print(f"✅ User '{email}' enabled successfully by {admin_email}.")
        log_action(admin_email, "ADMIN_ENABLE_USER", f"Target: {email}") # Log action
    else:
        print(f"⚠️ Failed to enable user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_ENABLE_USER_FAILURE", f"Target: {email}") # Log failure
    return RedirectResponse("/admin", status_code=302)

# Add the unban route
@app.post("/admin/unban")
async def unban_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request) # Check if admin and get admin email
    target_email = email # Use the form email as target_email
    # This correctly unbans the user by setting is_banned to False (0 in DB)
    if update_user_status(email, "is_banned", False):
        print(f"✅ User '{email}' unbanned successfully by {admin_email}.")
        # Update log_action call as requested
        log_action(admin_email, "unban_user", f"Unbanned user: {target_email}")
        # Optionally, ensure user is also enabled if unbanning implies enabling
        # update_user_status(email, "is_disabled", False)
    else:
        print(f"⚠️ Failed to unban user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_UNBAN_USER_FAILURE", f"Target: {target_email}") # Keep failure log
    return RedirectResponse("/admin", status_code=302)

# Replace the previous handle_admin_reset_password route
@app.post("/admin/reset-password")
async def reset_user_password(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...)
):
    # --- Start: Code adapted from user prompt ---
    # Ensure admin is logged in and get admin email
    admin_email = verify_admin(request)

    # Basic validation (optional but recommended)
    if len(new_password) < 8:
        print(f"⚠️ Admin password reset failed for '{email}': Password too short.")
        log_action(admin_email, "ADMIN_RESET_PASSWORD_FAILURE", f"Target: {email}, Reason: Password too short") # Log failure
        # Consider adding user feedback here (e.g., flash message or query param)
        return RedirectResponse("/admin", status_code=302) # Use 302 for redirect after POST

    conn = None
    cursor = None
    success = False # Flag to track success for logging
    try:
        # Hash the new password (bcrypt is imported globally)
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Connect to DB (using pattern from elsewhere in the file)
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        # Update password_hash and reset attempts
        cursor.execute("UPDATE users SET password_hash = %s, reset_attempts = 0 WHERE email = %s", (hashed_pw, email))
        conn.commit()

        if cursor.rowcount > 0:
             print(f"🔐 Admin reset password for {email}")
             success = True
        else:
             print(f"⚠️ Admin password reset: User {email} not found or DB error.")
             # Consider adding user feedback here

    except mysql.connector.Error as err:
        print(f"🔥 DB Error during admin password reset for {email}: {err}")
        # Consider adding user feedback here
    except Exception as e:
        print(f"🔥 Unexpected error during admin password reset for {email}: {e}")
        # Consider adding user feedback here
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Log action based on success flag
    if success:
        log_action(admin_email, "ADMIN_RESET_PASSWORD_SUCCESS", f"Target: {email}")
    else:
        # Log failure if not already logged for specific validation errors
        if len(new_password) >= 8: # Avoid double logging validation error
            log_action(admin_email, "ADMIN_RESET_PASSWORD_FAILURE", f"Target: {email}, Reason: DB error or user not found")

    # Redirect back to admin page (use 302 for redirect after POST)
    return RedirectResponse("/admin", status_code=302)
    # --- End: Code adapted from user prompt ---

# --- End Admin Action Routes ---

# --- Admin User Detail Route (Updated) ---
@app.get("/admin/user/{email}")
async def view_user_details(email: str, request: Request):
    verify_admin(request) # Use the helper function for auth

    user_details = None # To store user data from 'users' table
    audit_logs = [] # Changed from sessions to audit_logs
    reset_activity_count = 0 # Keep this as it queries audit_logs too
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)

        # Fetch user details from 'users' table (Keep this)
        cursor.execute("""
            SELECT email, created_at, is_premium, subscription_type, subscription_status,
                   current_period_end, stripe_customer_id, is_banned, is_disabled, reset_attempts,
                   failed_logins, lock_until
            FROM users
            WHERE email=%s
        """, (email,))
        user_details = cursor.fetchone()

        if not user_details:
             raise HTTPException(status_code=404, detail="User not found")

        # Format dates for user details (Keep this)
        if user_details.get('created_at'):
            user_details['created_at_formatted'] = user_details['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC')
        if user_details.get('current_period_end'):
            user_details['current_period_end_formatted'] = user_details['current_period_end'].strftime('%Y-%m-%d')
        else:
            user_details['current_period_end_formatted'] = 'N/A'
        if user_details.get('lock_until'):
            user_details['lock_until_formatted'] = user_details['lock_until'].strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
             user_details['lock_until_formatted'] = 'N/A'


        # Fetch recent audit logs for this user
        cursor.execute("""
            SELECT timestamp, action, details
            FROM audit_logs
            WHERE email=%s
            ORDER BY timestamp DESC
            LIMIT 50
        """, (email,))
        audit_logs = cursor.fetchall()
        # Format timestamp for display
        for log in audit_logs:
            if log.get('timestamp'):
                log['timestamp_formatted'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')


        # Fetch password reset related activity count from audit logs (Keep this)
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM audit_logs
            WHERE email=%s AND action LIKE '%RESET_PASSWORD%'
        """, (email,))
        result = cursor.fetchone()
        reset_activity_count = result['count'] if result else 0

    except mysql.connector.Error as err:
        print(f"🔥 DB Error fetching user details for {email}: {err}")
        # Handle error appropriately, maybe show an error message in the template
        raise HTTPException(status_code=500, detail="Database error fetching user details.")
    except Exception as e:
        print(f"🔥 Unexpected error fetching user details for {email}: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error fetching user details.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Pass user_details and audit_logs to the template
    return templates.TemplateResponse("user_details.html", {
        "request": request,
        "user": user_details, # Pass the full user details dict
        "email": email, # Keep email for title consistency if needed
        "logs": audit_logs, # Pass audit logs instead of sessions
        "reset_activity_count": reset_activity_count
    })
# --- End Admin User Detail Route ---

# --- New Admin Churn Report Route ---
@app.get("/admin/churn")
async def churn_report(request: Request):
    verify_admin(request) # Use the helper function for auth

    churned_users = []
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        # Fetch 'churn' actions from audit logs
        cursor.execute("""
            SELECT email, timestamp, details
            FROM audit_logs
            WHERE action='churn'
            ORDER BY timestamp DESC
        """)
        churned_users = cursor.fetchall()
        # Format dates
        for user in churned_users:
            if user.get('timestamp'):
                user['timestamp_formatted'] = user['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')

    except mysql.connector.Error as err:
        print(f"🔥 DB Error fetching churn report: {err}")
        raise HTTPException(status_code=500, detail="Database error fetching churn report.")
    except Exception as e:
        print(f"🔥 Unexpected error fetching churn report: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error fetching churn report.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return templates.TemplateResponse("churn_report.html", {
        "request": request,
        "churned": churned_users
    })
# --- End Admin Churn Report Route ---


# --- Export Users Route (Replacing previous implementation) ---

@app.get("/admin/export-users", response_class=StreamingResponse) # Keep response_class
async def export_users(request: Request): # Keep async and request parameter
    # Security: only allow admin (using existing verify_admin helper)
    admin_email = verify_admin(request)
    log_action(admin_email, "ADMIN_EXPORT_USERS") # Log export action

    conn = None
    cursor = None
    rows = []
    headers = []

    try:
        # Connect to DB (using pattern from elsewhere in the file)
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        # Use standard cursor to match csv.writer which expects tuples/lists
        cursor = conn.cursor()

        # Fetch relevant data for ALL users - Adjusted fields
        cursor.execute("""
            SELECT email, created_at, is_premium, subscription_type, subscription_status,
                   current_period_end, stripe_customer_id, is_banned, is_disabled, reset_attempts
            FROM users
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        headers = [i[0] for i in cursor.description] # Get headers from cursor description
        print(f"📊 Found {len(rows)} users for export.")

    except mysql.connector.Error as err:
        print(f"🔥 DB Error during user export: {err}")
        raise HTTPException(status_code=500, detail="Database error during export.")
    except Exception as e:
        print(f"🔥 Unexpected error during user export: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during user export.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Create CSV in memory using io.StringIO and csv.writer
    output = StringIO() # Use StringIO from io module
    writer = csv.writer(output)
    writer.writerow(headers) # Write headers first

    # Format and write rows
    for row_tuple in rows:
        formatted_row = list(row_tuple) # Convert tuple to list for modification
        # Find indices of columns to format (adjust if query changes)
        try:
            created_at_idx = headers.index('created_at')
            period_end_idx = headers.index('current_period_end')
            is_premium_idx = headers.index('is_premium')
            is_banned_idx = headers.index('is_banned')
            is_disabled_idx = headers.index('is_disabled')

            # Format datetime objects
            if isinstance(formatted_row[created_at_idx], datetime):
                formatted_row[created_at_idx] = formatted_row[created_at_idx].strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(formatted_row[period_end_idx], datetime):
                 formatted_row[period_end_idx] = formatted_row[period_end_idx].strftime('%Y-%m-%d %H:%M:%S')

            # Format boolean/tinyint fields
            formatted_row[is_premium_idx] = 'Yes' if formatted_row[is_premium_idx] else 'No'
            formatted_row[is_banned_idx] = 'Yes' if formatted_row[is_banned_idx] else 'No'
            formatted_row[is_disabled_idx] = 'Yes' if formatted_row[is_disabled_idx] else 'No'

            # Handle None values -> empty strings
            formatted_row = ["" if item is None else item for item in formatted_row]

        except ValueError as ve:
            print(f"⚠️ Error finding column index during CSV formatting: {ve}")
            # Handle error - maybe skip formatting for this row or log more details
            formatted_row = ["" if item is None else item for item in formatted_row] # Basic None handling

        writer.writerow(formatted_row)

    output.seek(0)
    # Return StreamingResponse with the new filename
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=all_users.csv" # Updated filename
    })

# --- End Export Users Route ---

# --- Profile Page Route ---
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    try: # Top-level try for the entire function
        user_email = request.session.get("user_id")
        if not user_email:
            return RedirectResponse("/login", status_code=303)

        subscription_details = None
        user_db_data = None
        conn = None
        cursor = None
        live_stripe_sub_found_and_updated_db = False # Flag to track if self-heal happened

        # 1. Fetch comprehensive user data from DB
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                database=os.getenv("DB_NAME")
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT email, is_premium, stripe_customer_id, subscription_type, 
                          subscription_status, current_period_end 
                   FROM users WHERE email = %s""", (user_email,)
            )
            user_db_data = cursor.fetchone()
            if user_db_data:
                print(f"[DEBUG /profile] Fetched user_db_data: {user_db_data}")
            else:
                print(f"⚠️ [ERROR /profile] User {user_email} not found in DB for profile page.")
        except mysql.connector.Error as db_err:
            print(f"⚠️ DB Error fetching user data for profile {user_email}: {db_err}")
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()

        # 2. If DB indicates active premium subscription, use that primarily
        if user_db_data and user_db_data.get("is_premium") and \
           user_db_data.get("subscription_status") in ['active', 'trialing']:
            
            print(f"[INFO /profile] DB indicates active/trialing premium subscription for {user_email}. Using DB data for display.")
            renewal_timestamp = None
            # Try to get upcoming invoice for more accurate renewal if customer_id exists
            customer_id_for_upcoming_inv = user_db_data.get("stripe_customer_id")
            
            if customer_id_for_upcoming_inv and user_db_data.get("subscription_status") == 'active': # Only for active subs
                try:
                    print(f"[DEBUG /profile] Attempting to fetch upcoming invoice for customer {customer_id_for_upcoming_inv} (from DB data path)")
                    # Corrected Stripe API call
                    inv = stripe.Invoice.retrieve_upcoming(customer=customer_id_for_upcoming_inv)
                    renewal_timestamp = inv.next_payment_attempt or inv.period_end
                    print(f"[DEBUG /profile] Upcoming invoice renewal: {renewal_timestamp}")
                except stripe.error.InvalidRequestError:
                    print(f"[INFO /profile] No upcoming invoice found for customer {customer_id_for_upcoming_inv} (DB data path). Using current_period_end.")
                    # Fallback to current_period_end from DB
                    if user_db_data.get("current_period_end"):
                        if isinstance(user_db_data["current_period_end"], datetime):
                            renewal_timestamp = int(user_db_data["current_period_end"].timestamp())
                        else: 
                            try: renewal_timestamp = int(user_db_data["current_period_end"])
                            except (ValueError, TypeError): pass # Keep None if conversion fails
                except stripe.error.StripeError as se:
                    print(f"⚠️ Stripe error fetching upcoming invoice (DB data path): {se}. Falling back to current_period_end.")
                    if user_db_data.get("current_period_end"): # Fallback
                        if isinstance(user_db_data["current_period_end"], datetime):
                            renewal_timestamp = int(user_db_data["current_period_end"].timestamp())
                        else: 
                            try: renewal_timestamp = int(user_db_data["current_period_end"])
                            except (ValueError, TypeError): pass
            
            if renewal_timestamp is None and user_db_data.get("current_period_end"): # If upcoming invoice failed or not applicable
                if isinstance(user_db_data["current_period_end"], datetime):
                    renewal_timestamp = int(user_db_data["current_period_end"].timestamp())
                else: 
                    try:
                        renewal_timestamp = int(user_db_data["current_period_end"])
                    except (ValueError, TypeError):
                        print(f"⚠️ Could not convert current_period_end from DB to timestamp: {user_db_data['current_period_end']}")
                        renewal_timestamp = None # Explicitly set to None on failure
            
            subscription_details = {
                "plan": user_db_data.get("subscription_type", "N/A"),
                "status": user_db_data.get("subscription_status"),
                "renewal": renewal_timestamp,
            }
            print(f"[DEBUG /profile] Initial subscription_details from DB (potentially with upcoming invoice date): {subscription_details}")

        # 3. If DB does NOT indicate active premium, or data is incomplete, then try full live Stripe check & self-heal
        else:
            print(f"[INFO /profile] DB does not indicate active/trialing subscription for {user_email} (is_premium: {user_db_data.get('is_premium') if user_db_data else 'N/A'}, status: {user_db_data.get('subscription_status') if user_db_data else 'N/A'}). Attempting live Stripe check and potential self-heal.")
            
            stripe_customer_id_to_try = user_db_data.get("stripe_customer_id") if user_db_data else None
            live_sub_object = None 

            if stripe_customer_id_to_try:
                print(f"[DEBUG /profile] Live Check (Attempt A): Using customer_id from DB: {stripe_customer_id_to_try}")
                try:
                    subs_response = stripe.Subscription.list(customer=stripe_customer_id_to_try, status='all', limit=5, expand=['data.items.data.price'])
                    for sub_item in subs_response.data: 
                        if sub_item.status in ['active', 'trialing']:
                            live_sub_object = sub_item
                            break
                    if live_sub_object:
                        print(f"[DEBUG /profile] Live Check (Attempt A): Found '{live_sub_object.status}' subscription with DB customer_id.")
                    else:
                        print(f"[DEBUG /profile] Live Check (Attempt A): No 'active' or 'trialing' subscription found using DB customer_id: {stripe_customer_id_to_try}")
                except stripe.error.StripeError as e_stripe_a:
                    print(f"⚠️ Stripe API Error (Live Check Attempt A with DB customer_id {stripe_customer_id_to_try}): {e_stripe_a}")
                except Exception as e_generic_a:
                    print(f"⚠️ Unexpected Error (Live Check Attempt A with DB customer_id {stripe_customer_id_to_try}): {e_generic_a}")
            
            if not live_sub_object:
                print(f"[DEBUG /profile] Live Check (Attempt B): No subscription from DB ID or DB ID was null. Trying email lookup: {user_email}")
                try:
                    custs_response = stripe.Customer.list(email=user_email, limit=1)
                    if custs_response and custs_response.data:
                        customer_id_from_email = custs_response.data[0].id
                        print(f"[DEBUG /profile] Live Check (Attempt B): Found Stripe customer_id via email: {customer_id_from_email}")
                        
                        subs_response_b = stripe.Subscription.list(customer=customer_id_from_email, status='all', limit=5, expand=['data.items.data.price'])
                        for sub_item_b in subs_response_b.data: 
                            if sub_item_b.status in ['active', 'trialing']:
                                live_sub_object = sub_item_b
                                stripe_customer_id_to_try = customer_id_from_email # Update the ID we might use for self-heal
                                break
                        if live_sub_object:
                            print(f"[DEBUG /profile] Live Check (Attempt B): Found '{sub_item_b.status}' subscription with email-looked-up customer_id.")
                        else:
                            print(f"[DEBUG /profile] Live Check (Attempt B): No 'active' or 'trialing' subscription found using email-looked-up customer_id: {customer_id_from_email}")
                    else:
                        print(f"[DEBUG /profile] Live Check (Attempt B): No Stripe customer found by email: {user_email}")
                except stripe.error.StripeError as e_stripe_b:
                    print(f"⚠️ Stripe API Error (Live Check Attempt B with email lookup for {user_email}): {e_stripe_b}")
                except Exception as e_generic_b:
                    print(f"⚠️ Unexpected Error (Live Check Attempt B with email lookup for {user_email}): {e_generic_b}")

            if live_sub_object:
                sub = live_sub_object 
                current_plan_nickname = "N/A" 
                stripe_customer_id_from_sub = sub.customer if hasattr(sub, 'customer') else None


                if sub.items and sub.items.data and len(sub.items.data) > 0: 
                    if sub.items.data[0] and sub.items.data[0].price:
                        price_obj = sub.items.data[0].price
                        current_plan_nickname = price_obj.nickname if price_obj.nickname else price_obj.id
                    else:
                        print(f"⚠️ [WARNING /profile] Live subscription (ID: {sub.id}) item has no price object or first item is null.")
                else:
                    print(f"⚠️ [WARNING /profile] Live subscription (ID: {sub.id}) has no items or items.data is empty.")

                # Initial renewal date from subscription object's current_period_end
                renewal_date_for_details = sub.current_period_end

                # Try to get a more accurate “next billing date” from upcoming invoice
                # Use stripe_customer_id_from_sub which is directly from the live subscription object
                if stripe_customer_id_from_sub and sub.status == 'active': # Only for active subscriptions
                    try:
                        print(f"[DEBUG /profile] Attempting to fetch upcoming invoice for customer {stripe_customer_id_from_sub} (from live sub path)")
                        # Corrected Stripe API call
                        inv = stripe.Invoice.upcoming(customer=stripe_customer_id_from_sub)
                        renewal_date_for_details = inv.next_payment_attempt or inv.period_end
                        print(f"[DEBUG /profile] Upcoming invoice renewal (live sub path): {renewal_date_for_details}")
                    except stripe.error.InvalidRequestError:
                        # No upcoming invoice (maybe canceled or trialing without payment method yet), leave renewal as sub.current_period_end
                        print(f"[INFO /profile] No upcoming invoice found for customer {stripe_customer_id_from_sub} (live sub path). Using subscription's current_period_end.")
                    except stripe.error.StripeError as se:
                        print(f"⚠️ Stripe error fetching upcoming invoice (live sub path): {se}. Falling back to subscription's current_period_end.")
                        # Fallback to sub.current_period_end already assigned to renewal_date_for_details

                subscription_details = {
                    "plan": current_plan_nickname,
                    "status": sub.status,
                    "renewal": renewal_date_for_details # Use the potentially updated renewal date
                }
                print(f"[INFO /profile] Live check successful. Populated subscription_details: {subscription_details}")

                db_is_premium_val = user_db_data.get("is_premium") if user_db_data else False
                db_status_val = user_db_data.get("subscription_status") if user_db_data else None
                db_stripe_id_val = user_db_data.get("stripe_customer_id") if user_db_data else None
                db_plan_val = user_db_data.get("subscription_type") if user_db_data else None
                db_renewal_val_ts = None
                if user_db_data and user_db_data.get("current_period_end"):
                    if isinstance(user_db_data["current_period_end"], datetime):
                        db_renewal_val_ts = int(user_db_data["current_period_end"].timestamp())
                    else:
                        try: db_renewal_val_ts = int(user_db_data["current_period_end"])
                        except: pass
                
                needs_db_update = False
                # stripe_customer_id_from_sub is already defined above

                if not db_is_premium_val or db_status_val != sub.status or \
                   (stripe_customer_id_from_sub and db_stripe_id_val != stripe_customer_id_from_sub) or \
                   db_plan_val != current_plan_nickname or \
                   db_renewal_val_ts != sub.current_period_end: # Compare DB with sub.current_period_end for self-heal
                    needs_db_update = True

                if needs_db_update:
                    print(f"[INFO /profile] Self-heal: DB is out of sync or was missing user data. Updating records for {user_email}.")
                    update_conn_db_heal, update_cursor_db_heal = None, None
                    try:
                        update_conn_db_heal = mysql.connector.connect(host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME"))
                        update_cursor_db_heal = update_conn_db_heal.cursor()
                        
                        update_query_sql = """
                            UPDATE users 
                            SET stripe_customer_id = %s, is_premium = %s, subscription_status = %s,
                                subscription_type = %s, current_period_end = FROM_UNIXTIME(%s)
                            WHERE email = %s
                        """
                        # For DB update, always use sub.current_period_end from the subscription object itself
                        update_values = (stripe_customer_id_from_sub, True, sub.status, current_plan_nickname, sub.current_period_end, user_email)
                        
                        update_cursor_db_heal.execute(update_query_sql, update_values)
                        update_conn_db_heal.commit()
                        
                        if update_cursor_db_heal.rowcount > 0:
                            live_stripe_sub_found_and_updated_db = True
                            print(f"[INFO /profile] DB self-heal successful for {user_email}.")
                            if request.session.get("is_premium") != True:
                                request.session["is_premium"] = True 
                                print(f"[INFO /profile] Updated session 'is_premium' to True due to self-heal.")
                        else:
                            print(f"⚠️ [WARNING /profile] Self-heal UPDATE affected 0 rows for {user_email}. User might not exist in DB or DB data was already correct (unlikely if needs_db_update was true).")

                    except mysql.connector.Error as db_update_err_heal:
                        print(f"⚠️ DB Error during self-heal update for {user_email}: {db_update_err_heal}")
                    finally:
                        if update_cursor_db_heal: update_cursor_db_heal.close()
                        if update_conn_db_heal and update_conn_db_heal.is_connected(): update_conn_db_heal.close()
            else:
                 print(f"[INFO /profile] Live check (after all attempts) did not find an active/trialing subscription for {user_email}.")

        session_is_premium = request.session.get("is_premium", False)
        final_db_is_premium = False
        if live_stripe_sub_found_and_updated_db: 
            final_db_is_premium = True
        elif user_db_data: 
            final_db_is_premium = user_db_data.get("is_premium", False)

        if not subscription_details and (session_is_premium or final_db_is_premium):
            print(f"🚨 [INCONSISTENCY /profile] User {user_email}: Session (is_premium={session_is_premium}), DB (is_premium={final_db_is_premium}) indicate premium, but profile page will show no active subscription. Live Stripe check also failed to find one or self-heal was incomplete.")

        return templates.TemplateResponse("profile.html", {
            "request": request,
            "email": user_email,
            "subscription": subscription_details
        })
    except Exception as e:
        user_email_for_log = request.session.get("user_id", "Unknown user")
        print(f"🔥🔥🔥 UNHANDLED EXCEPTION IN /profile ROUTE for user {user_email_for_log} 🔥🔥🔥")
        print(f"Error Type: {type(e)}")
        print(f"Error Message: {str(e)}")
        print("Traceback:")
        traceback.print_exc() 
        # Raise HTTPException to return a 500 error to the client
        # The detailed error is logged on the server.
        raise HTTPException(status_code=500, detail="An internal server error occurred while loading the profile page. Please try again later or contact support if the issue persists.")

# --- End Profile Page Route ---
