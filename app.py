import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import mysql.connector
import bcrypt
from typing import Optional
import csv
from io import StringIO
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import stripe
from auth_utils import verify_user, create_user, get_admin_stats, update_user_status, admin_reset_password, log_action
from stripe_payments import router as stripe_payments_router
from stripe_webhook import router as stripe_webhook_router

# load your Stripe secret key from .env
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# for creating customer portal sessions
STRIPE_PORTAL_RETURN_URL = os.getenv("STRIPE_PORTAL_RETURN_URL", "https://cricketstatspack.com/billing")

# Determine log level from environment variable or default to DEBUG
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
numeric_level = getattr(logging, LOG_LEVEL, logging.DEBUG)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler()
    ]
)
# Get a logger for this module
logger = logging.getLogger(__name__)

print("ðŸ”¥ FASTAPI LOADED ðŸ”¥")

load_dotenv()  # loads .env into os.environ


# Define PageViewLoggerMiddleware
class PageViewLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Process the request first to get the response
        response = await call_next(request)

        # Log page view after the request is processed
        try:
            path = request.url.path
            ip = request.client.host if request.client else "unknown"
            session = request.session
            email = session.get("user_id")

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
                    (email, path, ip, datetime.now())
                )
                conn.commit()
            except mysql.connector.Error as db_err:
                 print(f"âš ï¸ DB Error logging page view: {db_err}")
            except Exception as inner_e:
                 print(f"âš ï¸ Inner Exception logging page view: {inner_e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

        except Exception as e:
            print(f"âš ï¸ Failed to log page view (Outer Exception): {e}")

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
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("You must set SECRET_KEY in your .env before starting")

# install the middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Add Page View Logger Middleware (after SessionMiddleware to access session)
app.add_middleware(PageViewLoggerMiddleware)

# Include the Stripe payments router
app.include_router(stripe_payments_router)
app.include_router(stripe_webhook_router)

# your existing mounts & templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Copilot: add require_login dependency (Keep for potential future use, but remove from /dashboard)
def require_login(request: Request):
  if not request.session.get("user_id"):
      raise HTTPException(status_code=401, detail="Not authenticated")

# Home page (Updated as requested)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.info("Root path ('/') accessed.")
    try:
        if request.session:
            # Corrected session logging to avoid NameError
            session_data_summary = {k: type(v).__name__ for k, v in request.session.items()}
            logger.debug(f"Session data on root access: {session_data_summary}")
        else:
            logger.debug("No session data on root access.")
        
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error processing root path ('/'): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

# âœ… Single, correct POST route for login (Updated for session and email)
@app.post("/login")
@limiter.limit("5/minute")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    print("ðŸš¨ Login POST received")

    conn = None
    cursor = None
    user_lock_data = None
    lockout_threshold = 5
    lockout_duration_minutes = 15

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email, failed_logins, lock_until FROM users WHERE email = %s", (email,))
        user_lock_data = cursor.fetchone()

        if user_lock_data:
            lock_until = user_lock_data.get("lock_until")
            if lock_until and datetime.now() < lock_until:
                lock_remaining = lock_until - datetime.now()
                minutes_remaining = int(lock_remaining.total_seconds() / 60) + 1
                error_message = f"Account temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minute(s)."
                print(f"ðŸ”’ Login attempt failed for {email}: Account locked until {lock_until}")
                log_action(email, "LOGIN_FAILURE", "Account locked")
                return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=403)

        is_valid_user = verify_user(email, password)

        if is_valid_user:
            print(f"âœ… Login success for {email} â€” redirecting to dashboard")
            log_action(email, "login", "User logged in successfully")

            if user_lock_data and user_lock_data.get("failed_logins", 0) > 0:
                cursor.execute("UPDATE users SET failed_logins = 0, lock_until = NULL WHERE email = %s", (email,))
                conn.commit()
                print(f"ðŸ”„ Reset failed login attempts for {email}.")

            request.session["user_id"] = email
            request.session["login_time"] = datetime.utcnow().isoformat()
            response = RedirectResponse(url="/dashboard", status_code=302)
            return response
        else:
            print(f"âŒ Login failed â€” invalid credentials or status for {email}")

            if user_lock_data:
                current_failures = user_lock_data.get("failed_logins", 0)
                new_failures = current_failures + 1
                lock_until_update = user_lock_data.get("lock_until")

                error_message = "Invalid login"

                if new_failures >= lockout_threshold:
                    lock_until_update = datetime.now() + timedelta(minutes=lockout_duration_minutes)
                    error_message = f"Account locked due to too many failed attempts. Try again in {lockout_duration_minutes} minutes."
                    print(f"ðŸš« Account for {email} locked until {lock_until_update}")
                    log_action(email, "ACCOUNT_LOCKED", f"Locked after {new_failures} failed attempts")
                else:
                    log_action(email, "LOGIN_FAILURE", f"Invalid credentials/status ({new_failures} attempts)")

                cursor.execute(
                    "UPDATE users SET failed_logins = %s, lock_until = %s WHERE email = %s",
                    (new_failures, lock_until_update, email)
                )
                conn.commit()
                print(f"ðŸ“ˆ Updated failed login attempts for {email} to {new_failures}.")
                return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=401 if lock_until_update else 401)

            else:
                log_action(email, "LOGIN_FAILURE", "User not found")
                return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"}, status_code=401)

    except mysql.connector.Error as db_err:
        print(f"ðŸ”¥ DB Error during login for {email}: {db_err}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Database error during login."}, status_code=500)
    except Exception as e:
        print(f"ðŸ”¥ Unexpected error during login for {email}: {e}")
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
    logger.info(f"Registration attempt for email: {email}")
    success = create_user(
        email,
        password,
        security_question_1,
        security_answer_1,
        security_question_2,
        security_answer_2
    )

    if not success:
        print(f"âŒ Registration failed for email '{email}' â€” email might already exist")
        log_action(email, "REGISTER_FAILURE", "Email already exists")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "An account with this email already exists."
        })

    conn = None
    cursor = None
    try:
        print(f"âœ… User with email '{email}' created successfully. Attempting auto-login...")
        log_action(email, "REGISTER_SUCCESS")
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email, is_premium FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            request.session["user_id"] = user["email"]
            request.session["is_premium"] = bool(user.get("is_premium", False))
            log_action(user["email"], "login", "User logged in successfully (auto-login after registration)")
            print(f"âœ… Session set for auto-login: {user['email']}, Premium: {request.session['is_premium']}")
            return RedirectResponse("/dashboard", status_code=302)
        else:
            print(f"âš ï¸ Auto-login failed: Could not fetch user '{email}' after creation.")
            return RedirectResponse("/login", status_code=302)

    except mysql.connector.Error as err:
        print(f"ðŸ”¥ DB Error during auto-login for {email}: {err}")
        return RedirectResponse("/login", status_code=302)
    except Exception as e:
        print(f"ðŸ”¥ Unexpected Error during auto-login for {email}: {e}")
        return RedirectResponse("/login", status_code=302)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# Add the new subscribe route here
@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("subscribe.html", {
        "request": request,
        "monthly_price_id": os.getenv("STRIPE_PRICE_ID_MONTHLY"),
        "annual_price_id": os.getenv("STRIPE_PRICE_ID_ANNUAL"),
    })


# Updated dashboard route to always check DB and update session using email
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_email = request.session.get("user_id")
    logger.info(f"Dashboard accessed by user: {user_email if user_email else 'Guest'}")
    
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT is_premium FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()

        if user:
            request.session["is_premium"] = bool(user.get("is_premium"))
        else:
            logger.warning(f"User with email {user_email} found in session but not in DB during dashboard load.")
            request.session["is_premium"] = False

    except mysql.connector.Error as err:
        logger.error(f"Dashboard DB check failed for {user_email}: {err}")
        request.session["is_premium"] = request.session.get("is_premium", False)
    except Exception as e:
        logger.error(f"Dashboard DB check failed unexpectedly for {user_email}: {e}")
        request.session["is_premium"] = request.session.get("is_premium", False)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return templates.TemplateResponse("dashboard.html", {"request": request})


# Copilot: add logout endpoint (Updated for session)
@app.get("/logout")
async def logout(request: Request):
    email = request.session.get("user_id")
    login_time_str = request.session.get("login_time")

    if email:
        log_action(email, "logout", "User logged out")

    if email and login_time_str:
        try:
            login_dt = datetime.fromisoformat(login_time_str)
            logout_dt = datetime.utcnow()
            duration = int((logout_dt - login_dt).total_seconds())

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
                print(f"âœ… Logged session duration for {email}: {duration} seconds.")
            except mysql.connector.Error as db_err:
                print(f"âŒ DB Error logging session duration for {email}: {db_err}")
            except Exception as log_e:
                print(f"âŒ Failed to log session duration for {email}: {log_e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

        except ValueError:
            print(f"âš ï¸ Could not parse login_time '{login_time_str}' for user {email}.")
        except Exception as outer_e:
             print(f"âŒ Unexpected error during session duration calculation for {email}: {outer_e}")
    else:
        print("â„¹ï¸ Logout initiated but no email or login_time found in session to log duration.")

    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    print("âœ… Logout successful â€” redirecting to home")
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
    return templates.TemplateResponse("verify_security.html", {
        "request": request,
        "questions": None,
        "error": None,
        "email": None
    })

@app.post("/verify-security")
async def verify_security_submit(
    request: Request,
    email: str = Form(...),
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

        cursor.execute(
            "SELECT id, security_question_1, security_answer_1_hash, "
            "security_question_2, security_answer_2_hash, reset_attempts "
            "FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()

        generic_error = "Invalid email or answers."

        if not user:
            print(f"Security verification step 1 failed: User not found - {email}")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "User not found")
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email,
                "error": "User not found."
            }, status_code=404)

        if user.get('reset_attempts', 0) >= 3:
            print(f"Security verification blocked for user {email} due to too many attempts.")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "Too many attempts")
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email,
                "error": "Too many failed attempts. Please contact support."
            }, status_code=403)

        q1 = user.get('security_question_1')
        sa1_hash = user.get('security_answer_1_hash')
        q2 = user.get('security_question_2')
        sa2_hash = user.get('security_answer_2_hash')

        if not q1 or not sa1_hash or not q2 or not sa2_hash:
            print(f"Security questions/hashes missing for user {email}.")
            log_action(email, "RESET_PASSWORD_VERIFY_FAILURE", "Security questions not set up")
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": None,
                "email": email,
                "error": "Security questions not set up for this account. Please contact support."
            }, status_code=400)

        if answer1 is None or answer2 is None:
            print(f"Security verification step 1 successful for {email}. Showing questions.")
            log_action(email, "RESET_PASSWORD_VERIFY_STEP1_SUCCESS")
            return templates.TemplateResponse("verify_security.html", {
                "request": request,
                "questions": [q1, q2],
                "email": email,
                "error": None
            })
        else:
            correct1 = bcrypt.checkpw(answer1.encode('utf-8'), sa1_hash.encode('utf-8'))
            correct2 = bcrypt.checkpw(answer2.encode('utf-8'), sa2_hash.encode('utf-8'))

            if correct1 and correct2:
                print(f"Security verification step 2 successful for user: {email}")
                log_action(email, "RESET_PASSWORD_VERIFY_STEP2_SUCCESS")
                cursor.execute("UPDATE users SET reset_attempts = 0 WHERE id = %s", (user['id'],))
                conn.commit()

                request.session['reset_user'] = email
                return RedirectResponse("/reset-password", status_code=302)
            else:
                print(f"Security verification step 2 failed for user: {email}")
                log_action(email, "RESET_PASSWORD_VERIFY_STEP2_FAILURE", "Incorrect answers")
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
    if 'reset_user' not in request.session:
        print("Access denied to /reset-password GET: No 'reset_user' (email) in session.")
        return RedirectResponse("/verify-security", status_code=303)

    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None})

# POST /reset-password
@app.post("/reset-password")
async def reset_password_submit(request: Request, new_password: str = Form(...), confirm_password: str = Form(...)):
    if 'reset_user' not in request.session:
        print("Access denied to /reset-password POST: No 'reset_user' (email) in session.")
        return RedirectResponse("/verify-security", status_code=303)

    email = request.session['reset_user']

    if new_password != confirm_password:
        print(f"Password mismatch for user {email} during reset attempt.")
        log_action(email, "RESET_PASSWORD_FAILURE", "Passwords do not match")
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "Passwords do not match."
        }, status_code=400)

    if len(new_password) < 8:
         print(f"Password too short for user {email} during reset attempt.")
         log_action(email, "RESET_PASSWORD_FAILURE", "Password too short")
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

        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        update_query = "UPDATE users SET password_hash = %s WHERE email = %s"
        cursor.execute(update_query, (hashed_pw, email))
        conn.commit()

        if cursor.rowcount == 1:
            print(f"Password successfully reset for email: {email}")
            log_action(email, "password_reset", "User successfully reset their password")
            request.session.pop('reset_user', None)
            return RedirectResponse("/reset-password-success", status_code=302)
        else:
            print(f"Password reset failed for email: {email}. User might no longer exist.")
            log_action(email, "RESET_PASSWORD_FAILURE", "User not found during update")
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
    return templates.TemplateResponse("reset_password_success.html", {"request": request})

# --- End Reset Password Success Route ---


# --- Change Password Routes (Updated for Email) ---

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_form(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})


@app.post("/change-password")
async def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)

    email = request.session["user_id"]

    if not verify_user(email, current_password):
        print(f"Change password failed for {email}: Incorrect current password.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "Incorrect current password")
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "Current password is incorrect.", "success": None
        }, status_code=400)

    if new_password != confirm_password:
        print(f"Change password failed for {email}: New passwords do not match.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "New passwords do not match")
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "New passwords do not match.", "success": None
        }, status_code=400)

    if len(new_password) < 8:
         print(f"Change password failed for {email}: New password too short.")
         log_action(email, "CHANGE_PASSWORD_FAILURE", "New password too short")
         return templates.TemplateResponse("change_password.html", {
             "request": request, "error": "New password must be at least 8 characters long.", "success": None
         }, status_code=400)

    if current_password == new_password:
        print(f"Change password failed for {email}: New password is the same as the current one.")
        log_action(email, "CHANGE_PASSWORD_FAILURE", "New password same as current")
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

        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        update_query = "UPDATE users SET password_hash = %s WHERE email = %s"
        cursor.execute(update_query, (hashed_pw, email))
        conn.commit()

        if cursor.rowcount == 1:
            print(f"Password successfully changed for email: {email}")
            log_action(email, "CHANGE_PASSWORD_SUCCESS")
            return templates.TemplateResponse("change_password.html", {
                "request": request, "error": None, "success": "Password changed successfully!"
            })
        else:
            print(f"Password change failed unexpectedly for email: {email} after verification.")
            log_action(email, "CHANGE_PASSWORD_FAILURE", "Unexpected update error")
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

# -- PROFILE VIEW & EDIT --

@app.get("/profile", response_class=HTMLResponse)
async def profile_view(request: Request):
    user_email = request.session.get("user_id")
    logger.info(f"Profile page accessed by user: {user_email if user_email else 'Guest'}")
    
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT email, display_name, notify_newsletter, security_question_1, security_question_2,
                   is_premium, subscription_type, subscription_status, created_at, current_period_end
              FROM users
             WHERE email = %s
        """, (user_email,))
        user = cursor.fetchone()
        logger.debug(f"Profile data retrieved for user: {user_email}")
    except mysql.connector.Error as err:
        logger.error(f"Database error retrieving profile data for {user_email}: {err}")
        user = None
    except Exception as e:
        logger.error(f"Unexpected error retrieving profile data for {user_email}: {e}")
        user = None
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user or {}
    })


@app.post("/profile")
async def profile_update(
    request: Request,
    display_name: str = Form(None),
    notify_newsletter: Optional[bool] = Form(False)
):
    user_email = request.session.get("user_id")
    logger.info(f"Profile update request for user: {user_email}")
    
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
               SET display_name      = %s,
                   notify_newsletter = %s
             WHERE email             = %s
        """, (display_name, int(bool(notify_newsletter)), user_email))
        conn.commit()
        
        logger.info(f"Profile updated successfully for user: {user_email}")
        logger.debug(f"Profile update details: name='{display_name}', newsletter={notify_newsletter}")
    except mysql.connector.Error as err:
        logger.error(f"Database error updating profile for {user_email}: {err}")
    except Exception as e:
        logger.error(f"Unexpected error updating profile for {user_email}: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()    # Log the action to audit_logs table
    log_action(user_email, "PROFILE_UPDATED",
               f"name='{display_name}', newsletter={notify_newsletter}")

    return RedirectResponse("/profile", status_code=303)

# -- BILLING HISTORY --

# Fixing the billing route to prevent Internal Server Error
@app.get("/billing", response_class=HTMLResponse)
async def billing(request: Request):
    """Redirect premium users to Stripe Customer Portal for billing management"""
    user_email = request.session.get("user_id")
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=302)
    
    # Check if user is premium and get Stripe customer ID
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT is_premium, stripe_customer_id FROM users WHERE email = %s", 
            (user_email,)
        )
        user_data = cursor.fetchone()
        
        if not user_data:
            logger.warning(f"User {user_email} not found in database")
            return RedirectResponse(url="/profile", status_code=302)
        
        is_premium = bool(user_data["is_premium"])
        stripe_customer_id = user_data["stripe_customer_id"]
        
        logger.debug(f"User {user_email} - Premium: {is_premium}, Stripe ID: {stripe_customer_id}")
        
    except Exception as e:
        logger.error(f"Error fetching user data for {user_email}: {e}")
        return RedirectResponse(url="/profile", status_code=302)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    # If user is not premium, redirect to profile
    if not is_premium:
        logger.info(f"Non-premium user {user_email} attempted to access billing")
        return RedirectResponse(url="/profile", status_code=302)    
    # For premium users, redirect to Stripe Customer Portal
    try:
        # Try with existing customer ID first
        if stripe_customer_id:
            logger.debug(f"Creating customer portal session for existing customer {stripe_customer_id}")
            portal_session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=STRIPE_PORTAL_RETURN_URL
            )
            logger.info(f"Redirecting premium user {user_email} to Stripe Customer Portal")
            return RedirectResponse(url=portal_session.url, status_code=302)
        
        # If no customer ID, search by email
        else:
            logger.debug(f"No stored customer ID, searching Stripe by email: {user_email}")
            customers = stripe.Customer.list(email=user_email, limit=1).data
            if customers:
                cust_id = customers[0].id
                logger.info(f"Found Stripe customer by email search: {cust_id}")
                
                # Update database with found customer ID
                try:
                    conn = mysql.connector.connect(
                        host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
                    )
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET stripe_customer_id = %s WHERE email = %s",
                        (cust_id, user_email)
                    )
                    conn.commit()
                    logger.debug(f"Updated database with customer ID {cust_id} for {user_email}")
                except Exception as db_err:
                    logger.error(f"Error updating customer ID for {user_email}: {db_err}")
                finally:
                    if cursor:
                        cursor.close()
                    if conn and conn.is_connected():
                        conn.close()
                
                # Create portal session
                portal_session = stripe.billing_portal.Session.create(
                    customer=cust_id,
                    return_url=STRIPE_PORTAL_RETURN_URL
                )
                logger.info(f"Redirecting premium user {user_email} to Stripe Customer Portal (found by email)")
                return RedirectResponse(url=portal_session.url, status_code=302)
            else:
                logger.warning(f"Premium user {user_email} has no Stripe customer ID and none found by email")
                # Redirect to subscribe page to set up billing
                return RedirectResponse(url="/subscribe", status_code=302)
                
    except stripe.error.StripeError as stripe_err:
        logger.error(f"Stripe API error for user {user_email}: {str(stripe_err)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "There was an error connecting to our billing system. Please try again later."
        })
    except Exception as e:
        logger.error(f"Error creating customer portal for {user_email}: {str(e)}", exc_info=True)
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error_message": "An unexpected error occurred. Please try again later."
        })

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
    user_email = request.session.get("user_id")
    logger.info(f"Admin dashboard access attempt by: {user_email or 'Not logged in'}")
    
    try:
        verify_admin(request) # This will raise HTTPException if not admin
        logger.info(f"Admin access GRANTED to: {user_email}")
        
        # Try to get admin stats, with fallback for local development
        try:
            stats, users = get_admin_stats()
            logger.debug(f"Admin stats fetched from database. Number of users: {len(users) if users else 0}")
        except Exception as db_error:
            logger.warning(f"Database error in admin dashboard: {db_error}")
            logger.info("Attempting local development fallback...")
            
            # Import local development override
            try:
                from local_dev_override import get_local_admin_stats
                stats, users = get_local_admin_stats()
                logger.info(f"Using local development data. Users: {len(users) if users else 0}")
            except Exception as fallback_error:
                logger.error(f"Local development fallback failed: {fallback_error}")
                # Provide minimal fallback data
                stats = {'total_users': 0, 'premium_users': 0, 'free_users': 0, 'recent_signups': 0, 'active_sessions': 0, 'monthly_revenue': 0}
                users = []
                logger.warning("Using empty fallback data for admin dashboard")
        
        logger.debug(f"Admin stats: {stats}, Users count: {len(users)}")

        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "stats": stats, 
            "users": users
        })
    except HTTPException as http_exc:
        logger.warning(f"Admin access DENIED for {user_email or 'Not logged in'}. Reason: {http_exc.detail}")
        raise # Re-raise the HTTPException from verify_admin
    except Exception as e:
        logger.error(f"Error loading admin dashboard for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error on admin dashboard")

# --- End Admin Dashboard Route ---


# --- Admin Action Routes ---

# Helper function for admin check (to avoid repetition)
def verify_admin(request: Request):
    user_email = request.session.get("user_id")
    admin_email_env = os.getenv("ADMIN_EMAIL", "r.taylor289@gmail.com")
    
    if user_email != admin_email_env:
        logger.warning(f"Unauthorized access attempt to admin action by: {user_email or 'Not logged in'}")
        log_action(user_email or "UNKNOWN", "ADMIN_ACTION_UNAUTHORIZED", f"Attempted action on path: {request.url.path}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    logger.info(f"Admin action authorized for: {user_email}")
    return user_email

@app.post("/admin/ban")
async def ban_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request)
    target_email = email
    logger.info(f"Admin ban action initiated by {admin_email} against {target_email}")
    
    if update_user_status(email, "is_banned", True):
        logger.info(f"User '{email}' banned successfully by {admin_email}.")
        log_action(admin_email, "ban_user", f"Banned user: {target_email}")
    else:
        logger.error(f"Failed to ban user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_BAN_USER_FAILURE", f"Target: {target_email}")
    
    return RedirectResponse("/admin", status_code=302)

@app.post("/admin/disable")
async def disable_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request)
    if update_user_status(email, "is_disabled", True):
         print(f"âœ… User '{email}' disabled successfully by {admin_email}.")
         log_action(admin_email, "ADMIN_DISABLE_USER", f"Target: {email}")
    else:
         print(f"âš ï¸ Failed to disable user '{email}' by {admin_email}.")
         log_action(admin_email, "ADMIN_DISABLE_USER_FAILURE", f"Target: {email}")
    return RedirectResponse("/admin", status_code=302)

@app.post("/admin/enable")
async def enable_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request)
    if update_user_status(email, "is_disabled", False):
        print(f"âœ… User '{email}' enabled successfully by {admin_email}.")
        log_action(admin_email, "ADMIN_ENABLE_USER", f"Target: {email}")
    else:
        print(f"âš ï¸ Failed to enable user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_ENABLE_USER_FAILURE", f"Target: {email}")
    return RedirectResponse("/admin", status_code=302)

# Add the unban route
@app.post("/admin/unban")
async def unban_user(request: Request, email: str = Form(...)):
    admin_email = verify_admin(request)
    target_email = email
    if update_user_status(email, "is_banned", False):
        print(f"âœ… User '{email}' unbanned successfully by {admin_email}.")
        log_action(admin_email, "unban_user", f"Unbanned user: {target_email}")
    else:
        print(f"âš ï¸ Failed to unban user '{email}' by {admin_email}.")
        log_action(admin_email, "ADMIN_UNBAN_USER_FAILURE", f"Target: {target_email}")
    return RedirectResponse("/admin", status_code=302)

# Replace the previous handle_admin_reset_password route
@app.post("/admin/reset-password")
async def reset_user_password(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...)
):
    admin_email = verify_admin(request)

    if len(new_password) < 8:
        print(f"âš ï¸ Admin password reset failed for '{email}': Password too short.")
        log_action(admin_email, "ADMIN_RESET_PASSWORD_FAILURE", f"Target: {email}, Reason: Password too short")
        return RedirectResponse("/admin", status_code=302)

    conn = None
    cursor = None
    success = False
    try:
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET password_hash = %s, reset_attempts = 0 WHERE email = %s", (hashed_pw, email))
        conn.commit()

        if cursor.rowcount > 0:
             print(f"ðŸ” Admin reset password for {email}")
             success = True
        else:
             print(f"âš ï¸ Admin password reset: User {email} not found or DB error.")

    except mysql.connector.Error as err:
        print(f"ðŸ”¥ DB Error during admin password reset for {email}: {err}")
    except Exception as e:
        print(f"ðŸ”¥ Unexpected error during admin password reset for {email}: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if success:
        log_action(admin_email, "ADMIN_RESET_PASSWORD_SUCCESS", f"Target: {email}")
    else:
        if len(new_password) >= 8:
            log_action(admin_email, "ADMIN_RESET_PASSWORD_FAILURE", f"Target: {email}, Reason: DB error or user not found")

    return RedirectResponse("/admin", status_code=302)

# --- End Admin Action Routes ---

# --- Admin User Detail Route (Updated) ---
@app.get("/admin/user/{email}")
async def view_user_details(email: str, request: Request):
    verify_admin(request)

    user_details = None
    audit_logs = []
    reset_activity_count = 0
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


        cursor.execute("""
            SELECT timestamp, action, details
            FROM audit_logs
            WHERE email=%s
            ORDER BY timestamp DESC
            LIMIT 50
        """, (email,))
        audit_logs = cursor.fetchall()
        for log in audit_logs:
            if log.get('timestamp'):
                log['timestamp_formatted'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')


        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM audit_logs
            WHERE email=%s AND action LIKE '%RESET_PASSWORD%'
        """, (email,))
        result = cursor.fetchone()
        reset_activity_count = result['count'] if result else 0

    except mysql.connector.Error as err:
        print(f"ðŸ”¥ DB Error fetching user details for {email}: {err}")
        raise HTTPException(status_code=500, detail="Database error fetching user details.")
    except Exception as e:
        print(f"ðŸ”¥ Unexpected error fetching user details for {email}: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error fetching user details.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return templates.TemplateResponse("user_details.html", {
        "request": request,
        "user": user_details,
        "email": email,
        "logs": audit_logs,
        "reset_activity_count": reset_activity_count
    })
# --- End Admin User Detail Route ---

# --- New Admin Churn Report Route ---
@app.get("/admin/churn")
async def churn_report(request: Request):
    verify_admin(request)

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
        cursor.execute("""
            SELECT email, timestamp, details
            FROM audit_logs
            WHERE action='churn'
            ORDER BY timestamp DESC
        """)
        churned_users = cursor.fetchall()
        for user in churned_users:
            if user.get('timestamp'):
                user['timestamp_formatted'] = user['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')

    except mysql.connector.Error as err:
        print(f"ðŸ”¥ DB Error fetching churn report: {err}")
        raise HTTPException(status_code=500, detail="Database error fetching churn report.")
    except Exception as e:
        print(f"ðŸ”¥ Unexpected error fetching churn report: {e}")
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

@app.get("/admin/export-users", response_class=StreamingResponse)
async def export_users(request: Request):
    admin_email = verify_admin(request)
    log_action(admin_email, "ADMIN_EXPORT_USERS")

    conn = None
    cursor = None
    rows = []
    headers = []

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT email, created_at, is_premium, subscription_type, subscription_status,
                   current_period_end, stripe_customer_id, is_banned, is_disabled, reset_attempts
            FROM users
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        headers = [i[0] for i in cursor.description]
        print(f"ðŸ“Š Found {len(rows)} users for export.")

    except mysql.connector.Error as err:
        print(f"ðŸ”¥ DB Error during user export: {err}")
        raise HTTPException(status_code=500, detail="Database error during export.")
    except Exception as e:
        print(f"ðŸ”¥ Unexpected error during user export: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during export.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for row_tuple in rows:
        formatted_row = list(row_tuple)
        try:
            created_at_idx = headers.index('created_at')
            period_end_idx = headers.index('current_period_end')
            is_premium_idx = headers.index('is_premium')
            is_banned_idx = headers.index('is_banned')
            is_disabled_idx = headers.index('is_disabled')

            if isinstance(formatted_row[created_at_idx], datetime):
                formatted_row[created_at_idx] = formatted_row[created_at_idx].strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(formatted_row[period_end_idx], datetime):
                 formatted_row[period_end_idx] = formatted_row[period_end_idx].strftime('%Y-%m-%d %H:%M:%S')

            formatted_row[is_premium_idx] = 'Yes' if formatted_row[is_premium_idx] else 'No'
            formatted_row[is_banned_idx] = 'Yes' if formatted_row[is_banned_idx] else 'No'
            formatted_row[is_disabled_idx] = 'Yes' if formatted_row[is_disabled_idx] else 'No'

            formatted_row = ["" if item is None else item for item in formatted_row]

        except ValueError as ve:
            print(f"âš ï¸ Error finding column index during CSV formatting: {ve}")
            formatted_row = ["" if item is None else item for item in formatted_row]

        writer.writerow(formatted_row)

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=all_users.csv"
    })

# --- End Export Users Route ---

# --- Stripe Webhook ---
@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None
    logger.info("Stripe webhook received.")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        logger.info(f"Stripe event constructed: id={event.id}, type={event.type}")
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}", exc_info=True)
        return HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}", exc_info=True)
        return HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error constructing Stripe event: {e}", exc_info=True)
        return HTTPException(status_code=500, detail="Could not process webhook event")

    # Handle the event
    try:
        logger.debug(f"Handling event type: {event.type}")
        if event.type == 'checkout.session.completed':
            session = event.data.object
            logger.info(f"Checkout session completed: {session.id} for customer {session.customer}")
            # ... logic to fulfill order, update database ...
            # e.g., update_user_subscription_status(session.customer, session.subscription, "active")
            # logger.info(f"Database updated for checkout session {session.id}")

        elif event.type == 'invoice.payment_succeeded':
            invoice = event.data.object
            logger.info(f"Invoice payment succeeded: {invoice.id} for customer {invoice.customer}")
            # ... logic for successful payment ...
            # e.g., update_subscription_period(invoice.customer, invoice.subscription)
            # logger.info(f"Subscription period updated for invoice {invoice.id}")
            
        elif event.type == 'invoice.payment_failed':
            invoice = event.data.object
            logger.warning(f"Invoice payment failed: {invoice.id} for customer {invoice.customer}. Billing reason: {invoice.billing_reason}")
            # ... logic for failed payment, notify user, update status ...
            # e.g., set_user_subscription_status(invoice.customer, "payment_failed")
            # logger.warning(f"Subscription status updated to payment_failed for invoice {invoice.id}")

        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            logger.info(f"Customer subscription deleted (churned): {subscription.id} for customer {subscription.customer}")
            # ... logic for churn, update database ...
            # e.g., mark_subscription_as_canceled(subscription.customer, subscription.id)
            # logger.info(f"Subscription {subscription.id} marked as canceled in DB.")
            
        # Add more event types as needed
        # elif event.type == 'customer.subscription.updated':
        #     subscription = event.data.object
        #     logger.info(f"Subscription {subscription.id} updated. Status: {subscription.status}, Current Period End: {datetime.fromtimestamp(subscription.current_period_end) if subscription.current_period_end else 'N/A'}")
        #     # ... logic to update subscription details in your DB ...

        else:
            logger.info(f"Received unhandled event type: {event.type}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error handling Stripe event type {event.type if event else 'UNKNOWN'}: {e}", exc_info=True)
        # Return 500 so Stripe retries, but be cautious about retry storms for non-recoverable errors.
        return HTTPException(status_code=500, detail="Error processing webhook event")


@app.get("/manage-subscription")
async def manage_subscription(request: Request):
    """Generate a Stripe portal session URL and redirect to it."""
    user_email = request.session.get("user_id")
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)
    
    logger.info(f"User {user_email} accessing subscription management")
    
    conn = None
    cursor = None
    try:
        # Fetch stripe_customer_id from the database
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT stripe_customer_id FROM users WHERE email=%s", (user_email,))
        row = cursor.fetchone()
        
        if not row or not row.get("stripe_customer_id"):
            logger.warning(f"No Stripe customer ID found for user {user_email}")
            # No customer ID means they aren't set up in Stripe, redirect to billing or subscribe
            is_premium = request.session.get("is_premium", False)
            if is_premium:
                logger.warning(f"Premium user {user_email} has no Stripe customer ID")
                return RedirectResponse("/billing", status_code=303)
            else:
                logger.info(f"Non-premium user {user_email} redirected to subscribe page")
                return RedirectResponse("/subscribe", status_code=303)
        
        cust_id = row["stripe_customer_id"]
          # Create Customer Portal session
        logger.debug(f"Creating customer portal session for {user_email}")
        portal_session = stripe.billing_portal.Session.create(
            customer=cust_id,
            return_url=STRIPE_PORTAL_RETURN_URL
        )
        
        logger.info(f"Redirecting user {user_email} to Stripe Customer Portal")
        return RedirectResponse(portal_session.url, status_code=303)
        
    except stripe.error.StripeError as stripe_err:
        logger.error(f"Stripe API error for user {user_email}: {str(stripe_err)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "There was an error connecting to our payment provider. Please try again later."
        })
    except Exception as e:
        logger.error(f"Error generating customer portal for {user_email}: {str(e)}", exc_info=True)
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error_message": "An unexpected error occurred. Please try again later."
        })
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.get("/cancel-subscription")
async def cancel_subscription(request: Request):
    """Cancel the user's subscription and redirect to the billing page."""
    user_email = request.session.get("user_id")
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)
    
    logger.info(f"User {user_email} attempting to cancel subscription")
    
    # Show confirmation page first
    if not request.query_params.get("confirm"):
        return templates.TemplateResponse("cancel_confirm.html", {
            "request": request,
            "email": user_email
        })
    
    conn = None
    cursor = None
    try:
        # Fetch stripe_customer_id and subscription_id from the database
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT stripe_customer_id, subscription_id 
            FROM users 
            WHERE email = %s
        """, (user_email,))
        row = cursor.fetchone()
        if not row or not row.get("stripe_customer_id") or not row.get("subscription_id"):
            logger.warning(f"No valid subscription information found for user {user_email}")
            return RedirectResponse("/billing?error=no_subscription", status_code=303)
        
        # Cancel the subscription via Stripe API
        try:
            # First check if the subscription exists and is active
            try:
                subscription = stripe.Subscription.retrieve(row["subscription_id"])
                if subscription.status not in ['active', 'trialing']:
                    logger.warning(f"Subscription {row['subscription_id']} for {user_email} is not active (status: {subscription.status})")
                    return RedirectResponse("/billing?error=no_subscription", status_code=303)
            except stripe.error.InvalidRequestError as e:
                logger.error(f"Invalid subscription ID {row['subscription_id']} for {user_email}: {e}")
                return RedirectResponse("/billing?error=no_subscription", status_code=303)
                
            # Proceed with cancellation
            stripe.Subscription.modify(
                row["subscription_id"],
                cancel_at_period_end=True
            )
            
            # Update the user record in the database
            cursor.execute("""
                UPDATE users 
                SET subscription_status = 'canceled' 
                WHERE email = %s
            """, (user_email,))
            conn.commit()
            
            logger.info(f"Subscription {row['subscription_id']} for {user_email} marked for cancellation at period end")
            
            # Subscription will remain active until the end of the period
            return RedirectResponse("/billing?message=cancellation_scheduled", status_code=303)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription for {user_email}: {e}")
            return RedirectResponse("/billing?error=stripe_error", status_code=303)
        
    except mysql.connector.Error as err:
        logger.error(f"Database error retrieving subscription information for {user_email}: {err}")
        return RedirectResponse("/billing?error=db_error", status_code=303)
    except Exception as e:
        logger.error(f"Unexpected error canceling subscription for {user_email}: {e}", exc_info=True)
        return RedirectResponse("/billing?error=unknown", status_code=303)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.get("/billing-debug", response_class=HTMLResponse)
async def billing_debug(request: Request):
    """A simplified version of the billing route for debugging"""
    user_email = request.session.get("user_id")
    if not user_email:
        return RedirectResponse("/login", status_code=303)

    # Check premium status
    is_premium = request.session.get("is_premium", False)
    subscription = None
    portal_url = None
    
    # Create a simple subscription object for any premium user
    if is_premium:
        subscription = {
            "plan_name": "Premium Plan (Debug)",
            "status": "active",
            "current_period_end": "Not available"
        }
        
        # Try to get a portal URL for the user
        try:
            # Search for a customer with the given email
            customers = stripe.Customer.list(email=user_email, limit=1).data
            if customers:
                cust_id = customers[0].id
                logger.info(f"Debug: Found Stripe customer by email search: {cust_id}")
                
                # Create portal session
                portal_session = stripe.billing_portal.Session.create(
                    customer=cust_id,
                    return_url=STRIPE_PORTAL_RETURN_URL
                )
                portal_url = portal_session.url
                logger.info(f"Debug: Generated portal URL for user {user_email}")
        except stripe.error.StripeError as stripe_err:
            logger.error(f"Debug: Stripe error generating portal URL: {stripe_err}")
            # Continue without portal URL
        except Exception as e:
            logger.error(f"Debug: Could not generate portal URL: {e}")
            # Continue without portal URL
    
    # Return a simple version of the billing page
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "subscription": subscription,
        "next_invoice_date": None,
        "portal_url": portal_url,
        "invoices": []
    })

