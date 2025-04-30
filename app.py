import os
from dotenv import load_dotenv
# Add Query, secrets, datetime, mysql.connector to imports
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import secrets
import datetime
import mysql.connector
import bcrypt # Add bcrypt import

# Assuming email_utils.py exists with send_password_reset_email function
from email_utils import send_password_reset_email
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

@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...)):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        # Use dictionary cursor for potentially easier access later if needed
        cursor = conn.cursor(dictionary=True)

        # Check email exists
        cursor.execute("SELECT username FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            print(f"Password reset requested for non-existent email: {email}")
            return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "❌ Email not found"})

        # Generate token and expiry
        token = secrets.token_urlsafe(32)
        # Ensure expiry is timezone-aware if your DB requires it, otherwise UTC is fine
        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        # Insert token into password_resets table (ensure this table exists)
        # Columns assumed: email (VARCHAR), token (VARCHAR), expires_at (DATETIME/TIMESTAMP)
        insert_query = "INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (email, token, expiry))
        conn.commit()

        # Send email with the reset link
        # Ensure your base URL is correct (e.g., read from env var)
        base_url = os.getenv("BASE_URL", "https://cricketstatspack.com")
        reset_link = f"{base_url}/reset-password?token={token}"
        print(f"Generated reset link for {email}: {reset_link}") # Log the link for debugging

        # Call the email sending function
        send_password_reset_email(email, reset_link)
        print(f"Password reset email initiated for {email}")

        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "✅ If an account exists for this email, a password reset link has been sent."}) # More secure message

    except mysql.connector.Error as err:
        print(f"Database error during password reset for {email}: {err}")
        # Show a generic error to the user
        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "⚠️ An error occurred. Please try again later."})
    except Exception as e:
        print(f"Unexpected error during password reset for {email}: {e}")
        # Consider logging the full exception details
        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "⚠️ An unexpected error occurred. Please try again later."})
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Forgot Password Routes ---

# --- Add Reset Password Routes ---

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str = Query(...)):
    # Ensure reset_password.html exists in the templates directory
    # Pass the token to the template so it can be included in the form submission
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": None})

@app.post("/reset-password")
async def reset_password_submit(request: Request, token: str = Form(...), new_password: str = Form(...)):
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

        # Validate token and expiration
        # Ensure expires_at column type matches datetime.datetime.utcnow() comparison
        cursor.execute("SELECT email, expires_at FROM password_resets WHERE token = %s", (token,))
        record = cursor.fetchone()

        # Check if token exists and is not expired (using UTC comparison)
        if not record or record['expires_at'] < datetime.datetime.utcnow():
            print(f"Invalid or expired password reset token attempted: {token}")
            return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "❌ Invalid or expired token. Please request a new reset link."})

        # Basic password validation (optional but recommended)
        if len(new_password) < 8: # Example: Minimum length check
             return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "❌ Password must be at least 8 characters long."})

        # Update password
        # Ensure the password column name ('password_hash') matches your users table schema
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_query = "UPDATE users SET password_hash = %s WHERE email = %s"
        cursor.execute(update_query, (hashed_pw, record['email']))

        # Cleanup token immediately after successful password update
        delete_query = "DELETE FROM password_resets WHERE token = %s"
        cursor.execute(delete_query, (token,))

        conn.commit()
        print(f"Password successfully reset for email: {record['email']}")

        # Redirect to login page with a success message (optional, using query param or flash message)
        # For simplicity, just redirecting to login
        return RedirectResponse("/login?message=Password+reset+successfully", status_code=302)

    except mysql.connector.Error as err:
        print(f"Database error during password reset for token {token}: {err}")
        # Show a generic error on the reset form
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "⚠️ A database error occurred. Please try again."})
    except Exception as e:
        print(f"Unexpected error during password reset for token {token}: {e}")
        return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": "⚠️ An unexpected error occurred. Please try again."})
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- End Reset Password Routes ---

