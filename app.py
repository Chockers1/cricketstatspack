import os
from dotenv import load_dotenv
# Remove Query, uuid4, timedelta, send_reset_email from imports
# Remove unused imports: Query, uuid4, timedelta, send_reset_email
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
# import secrets # Keep secrets if needed elsewhere, uuid is removed
from datetime import datetime # Remove timedelta if not used elsewhere
import mysql.connector
import bcrypt # Ensure bcrypt is imported

from auth_utils import verify_user, create_user
from stripe_payments import router as stripe_payments_router # Add this import
from stripe_webhook import router as stripe_webhook_router # Add this import

print("🔥 FASTAPI LOADED 🔥")

load_dotenv()  # loads .env into os.environ

# SECRET_KEY = os.getenv("SECRET_KEY", "replace-this-with-a-real-secret") # Remove this line
app = FastAPI()

# Add Session Middleware:
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY) # Remove this line

# load your SECRET_KEY from the env
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("You must set SECRET_KEY in your .env before starting")

# install the middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Include the Stripe payments router
app.include_router(stripe_payments_router) # Add this line
app.include_router(stripe_webhook_router) # Add this line

# your existing mounts & templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# ✅ Single, correct POST route for login (Updated for session)
@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    print("🚨 Login POST received")
    # Assuming verify_user returns True on success, or maybe user info
    # For now, let's assume it returns True and we store username in session
    # The parameters 'username' and 'password' match the HTML form names.
    # The 'password' variable is passed directly to verify_user without modification here.
    if verify_user(username, password):
        print("✅ Login success — redirecting to dashboard")
        # Store user identifier in session
        request.session["user_id"] = username # Store username as user_id
        response = RedirectResponse(url="/dashboard", status_code=302)
        # response.set_cookie(key="logged_in", value="yes", httponly=True) # Remove cookie setting
        return response
    else:
        print("❌ Login failed — invalid username/password")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

# Registration page
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

# Registration submission
@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    security_question_1: str = Form(...),
    security_answer_1: str = Form(...),
    security_question_2: str = Form(...),
    security_answer_2: str = Form(...)
):
    # Pass all fields including security questions/answers to create_user
    if create_user(
        username,
        email,
        password,
        security_question_1,
        security_answer_1,
        security_question_2,
        security_answer_2
    ):
        print(f"✅ User '{username}' created successfully — redirecting to login")
        return RedirectResponse(url="/login", status_code=302)
    else:
        print(f"❌ Registration failed for user '{username}' — username or email might already exist")
        # Return simpler error message as requested
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or email already exists."
        })

# Add the new subscribe route here
@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("subscribe.html", {"request": request})


# Updated dashboard route to always check DB and update session
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")

    username = request.session["user_id"]

    # 🔄 ALWAYS check DB for latest premium status
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
        cursor.execute("SELECT is_premium FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            # 🔁 Refresh premium status in session, ensuring it's a boolean
            request.session["is_premium"] = bool(user.get("is_premium"))
        else:
            # If user somehow not found in DB (though they are logged in), set premium to False
            print(f"⚠️ User {username} found in session but not in DB during dashboard load.")
            request.session["is_premium"] = False

    except mysql.connector.Error as err: # Catch specific DB errors
        print(f"🔥 Dashboard DB check failed for {username}: {err}")
        # Keep existing session value or default to False if error occurs
        request.session["is_premium"] = request.session.get("is_premium", False)
    except Exception as e: # Catch other potential errors
        print(f"🔥 Dashboard DB check failed unexpectedly for {username}: {e}")
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

# --- Security Question Verification Routes ---

@app.get("/verify-security", response_class=HTMLResponse)
async def verify_security_form(request: Request):
    # Renders the security question verification form
    return templates.TemplateResponse("verify_security.html", {"request": request, "error": None})

@app.post("/verify-security") # Removed response_class=HTMLResponse, will use RedirectResponse on success
async def verify_security_submit(
    request: Request,
    username: str = Form(...),
    answer1: str = Form(...),
    answer2: str = Form(...)
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
        cursor = conn.cursor(dictionary=True) # Use dictionary cursor

        # Fetch user and security answers
        cursor.execute("SELECT id, security_answer_1_hash, security_answer_2_hash, reset_attempts FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        # Use a generic error message to avoid revealing if a user exists
        generic_error = "Invalid username or answers."

        if not user:
            print(f"Security verification attempt for non-existent user: {username}")
            return templates.TemplateResponse("verify_security.html", {"request": request, "error": generic_error}, status_code=400)

        # Check reset attempts
        if user.get('reset_attempts', 0) >= 3: # Default to 0 if column is somehow NULL
            print(f"Security verification blocked for user {username} due to too many attempts.")
            return templates.TemplateResponse("verify_security.html", {"request": request, "error": "Too many failed attempts. Please contact support."}, status_code=403) # Use 403 Forbidden

        # Verify answers using bcrypt
        # Ensure security answer columns exist and are not NULL before encoding
        sa1_hash = user.get('security_answer_1_hash')
        sa2_hash = user.get('security_answer_2_hash')

        if not sa1_hash or not sa2_hash:
             print(f"Security answers missing for user {username}.")
             # Increment attempts even if answers are missing to prevent probing
             cursor.execute("UPDATE users SET reset_attempts = reset_attempts + 1 WHERE id = %s", (user['id'],))
             conn.commit()
             return templates.TemplateResponse("verify_security.html", {"request": request, "error": generic_error}, status_code=400)

        correct1 = bcrypt.checkpw(answer1.encode('utf-8'), sa1_hash.encode('utf-8'))
        correct2 = bcrypt.checkpw(answer2.encode('utf-8'), sa2_hash.encode('utf-8'))

        if correct1 and correct2:
            print(f"Security verification successful for user: {username}")
            # Reset attempt count
            cursor.execute("UPDATE users SET reset_attempts = 0 WHERE id = %s", (user['id'],))
            conn.commit()

            # Store username in session temporarily for reset step
            request.session['reset_user'] = username
            return RedirectResponse("/reset-password", status_code=302)
        else:
            print(f"Security verification failed for user: {username}")
            # Increment attempt count
            cursor.execute("UPDATE users SET reset_attempts = reset_attempts + 1 WHERE id = %s", (user['id'],))
            conn.commit()
            return templates.TemplateResponse("verify_security.html", {"request": request, "error": generic_error}, status_code=400)

    except mysql.connector.Error as err:
        print(f"Database error during security verification for {username}: {err}")
        return templates.TemplateResponse("verify_security.html", {"request": request, "error": "A database error occurred."}, status_code=500)
    except Exception as e:
        print(f"Unexpected error during security verification for {username}: {e}")
        return templates.TemplateResponse("verify_security.html", {"request": request, "error": "An unexpected error occurred."}, status_code=500)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Security Question Verification Routes ---


# --- Form-Based Reset Password Routes (Updated for Session Verification) ---

# GET /reset-password
@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request):
    # Check if user has passed security verification via session
    if 'reset_user' not in request.session:
        print("Access denied to /reset-password GET: No 'reset_user' in session.")
        # Redirect to the start of the process if session key is missing
        return RedirectResponse("/verify-security", status_code=303) # Use 303 See Other

    # User is verified, render the reset form
    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None})

# POST /reset-password
@app.post("/reset-password") # Removed response_class=HTMLResponse, uses RedirectResponse
async def reset_password_submit(request: Request, new_password: str = Form(...), confirm_password: str = Form(...)):
    # Double-check session key existence on POST
    if 'reset_user' not in request.session:
        print("Access denied to /reset-password POST: No 'reset_user' in session.")
        return RedirectResponse("/verify-security", status_code=303)

    username = request.session['reset_user'] # Get username from session

    # 1. Check if passwords match
    if new_password != confirm_password:
        print(f"Password mismatch for user {username} during reset attempt.")
        # Note: We don't pass username back to template anymore
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "Passwords do not match."
        }, status_code=400)

    # Optional: Basic password validation (e.g., minimum length)
    if len(new_password) < 8: # Example: Minimum length check
         print(f"Password too short for user {username} during reset attempt.")
         return templates.TemplateResponse("reset_password.html", {
             "request": request,
             "error": "Password must be at least 8 characters long."
         }, status_code=400)

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

        # 2. Hash the new password
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 3. Update password_hash in the database using username from session
        # Ensure your password column is named 'password_hash'
        update_query = "UPDATE users SET password_hash = %s WHERE username = %s"
        cursor.execute(update_query, (hashed_pw, username))
        conn.commit()

        # Check if the update was successful
        if cursor.rowcount == 1:
            print(f"Password successfully reset for username: {username}")
            # 4. Clear the session key and redirect to login on success
            request.session.pop('reset_user', None) # Safely remove the key
            return RedirectResponse("/login?message=Password+reset+successfully", status_code=302)
        else:
            # This might happen if the user was deleted between verification and reset
            print(f"Password reset failed for username: {username}. User might no longer exist.")
            # Clear the potentially stale session key
            request.session.pop('reset_user', None)
            return templates.TemplateResponse("reset_password.html", {
                "request": request,
                "error": "Could not update password. User may not exist.",
            }, status_code=404) # User not found during update

    except mysql.connector.Error as err:
        print(f"Database error during password reset for username {username}: {err}")
        # Don't clear session key on DB error, user might retry
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "A database error occurred. Please try again.",
        }, status_code=500)
    except Exception as e:
        print(f"Unexpected error during password reset for username {username}: {e}")
        # Don't clear session key on unexpected error
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again.",
        }, status_code=500)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Reset Password Routes ---

