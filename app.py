import os
from dotenv import load_dotenv
# Add Query, secrets, datetime, mysql.connector to imports
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
# import secrets # Keep secrets if needed elsewhere, otherwise uuid is used now
from uuid import uuid4 # Import uuid4
from datetime import datetime, timedelta # Import timedelta
import mysql.connector
import bcrypt # Add bcrypt import

# Assuming email_utils.py exists with send_reset_email function (updated name)
from email_utils import send_reset_email # Use send_reset_email as per prompt
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
async def register_submit(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    # ✅ Fix: Correct parameter order for create_user()
    if create_user(username, email, password): # Corrected argument order
        print(f"✅ User '{username}' created successfully — redirecting to login")
        return RedirectResponse(url="/login", status_code=302)
    else:
        print(f"❌ Registration failed for user '{username}' — username might already exist")
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists or invalid input"})

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

# --- Add Forgot Password Routes ---

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    # Ensure forgot_password.html exists in the templates directory
    return templates.TemplateResponse("forgot_password.html", {"request": request, "message": None})

# Replace the existing POST route implementation
@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...)): # Renamed from forgot_password_post for consistency
    conn = None
    cursor = None
    try:
        # Check if email exists in users table before generating token (optional but good practice)
        conn_check = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT email FROM users WHERE email = %s", (email,))
        user_exists = cursor_check.fetchone()
        cursor_check.close()
        conn_check.close()

        # Only proceed if the user exists to avoid leaking information
        if user_exists:
            token = str(uuid4()) # Use uuid4 for token generation
            expires_at = datetime.utcnow() + timedelta(hours=1)

            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                database=os.getenv("DB_NAME")
            )
            cursor = conn.cursor()
            # Ensure password_resets table exists with columns: email, token, expires_at
            cursor.execute("INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)", (email, token, expires_at))
            conn.commit()

            # Send email using the imported function
            base_url = os.getenv("BASE_URL", "https://cricketstatspack.com")
            reset_link = f"{base_url}/reset-password?token={token}"
            send_reset_email(email, reset_link) # Use send_reset_email
            print(f"Password reset email initiated for {email} (if user exists).")
        else:
             print(f"Password reset requested for non-existent email: {email}. No email sent.")


        # Always return the success message regardless of whether the email existed
        # This prevents attackers from confirming which emails are registered.
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "message": "✅ If an account exists for this email, a password reset link has been sent." # Use 'message' key consistent with GET route
        })

    except mysql.connector.Error as err:
        print(f"Database error during password reset for {email}: {err}")
        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "⚠️ An error occurred. Please try again later."})
    except Exception as e:
        print(f"Unexpected error during password reset for {email}: {e}")
        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "⚠️ An unexpected error occurred. Please try again later."})
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Forgot Password Routes ---

# --- Replace Reset Password Routes ---

# Replace existing GET /reset-password
@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request):
    # This version doesn't expect a token in the query parameter anymore
    # Ensure reset_password.html is updated to not require/use a token variable
    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None})

# Replace existing POST /reset-password
@app.post("/reset-password", response_class=HTMLResponse) # Changed decorator to match function name
async def reset_password_submit(request: Request, username: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    # Check if passwords match
    if new_password != confirm_password:
        print(f"Password mismatch for user {username} during reset attempt.")
        # Pass username back to template if needed, e.g., to pre-fill the form
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "Passwords do not match.",
            "username": username # Optional: pass username back
        })

    # Imports are already global, but kept here as per prompt structure
    # import bcrypt, mysql.connector
    conn = None
    cursor = None
    try:
        # Basic password validation (optional but recommended)
        if len(new_password) < 8: # Example: Minimum length check
             print(f"Password too short for user {username} during reset attempt.")
             return templates.TemplateResponse("reset_password.html", {
                 "request": request,
                 "error": "❌ Password must be at least 8 characters long.",
                 "username": username # Optional: pass username back
             })

        # Hash the new password
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        # Update password based on username
        # Ensure password column is 'password_hash'
        update_query = "UPDATE users SET password_hash = %s WHERE username = %s"
        cursor.execute(update_query, (hashed_pw, username))
        conn.commit()

        # Check if a row was actually updated (i.e., if the username existed)
        if cursor.rowcount == 0:
            print(f"Attempted password reset for non-existent username: {username}")
            # Return error if username wasn't found
            return templates.TemplateResponse("reset_password.html", {
                "request": request,
                "error": "Username not found.",
                "username": username # Optional: pass username back
            })

        print(f"Password successfully reset for username: {username}")
        # Redirect to login page after successful reset
        return RedirectResponse("/login?message=Password+reset+successfully", status_code=302)

    except mysql.connector.Error as err:
        print(f"Database error during password reset for username {username}: {err}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "⚠️ A database error occurred. Please try again.",
            "username": username # Optional: pass username back
        })
    except Exception as e:
        print(f"Unexpected error during password reset for username {username}: {e}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "⚠️ An unexpected error occurred. Please try again.",
            "username": username # Optional: pass username back
        })
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Reset Password Routes ---

