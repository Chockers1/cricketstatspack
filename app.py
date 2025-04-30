import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException # Keep Depends/HTTPException for now, might be needed elsewhere
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import mysql.connector # Added for direct DB access in login
import bcrypt # Added for password checking in login

from auth_utils import verify_user, create_user # Keep verify_user for now, though login route overrides it
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

# Updated POST route for login to store is_premium in session
@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    print("🚨 Login POST received")
    conn = None # Initialize DB variables
    cursor = None

    try:
        # DB connection
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        print("🔎 User from DB:", user) # Debug output

        # Verify password and user existence
        # Ensure 'password_hash' matches your actual DB column name
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            print("✅ Login success — redirecting to dashboard")
            # Store user_id and is_premium status in session
            request.session["user_id"] = username
            # Convert DB value (likely 0 or 1) to boolean for the session
            request.session["is_premium"] = bool(user.get("is_premium", 0)) # <-- THIS LINE IS KEY
            response = RedirectResponse(url="/dashboard", status_code=302)
            return response
        else:
            # Invalid credentials
            print("❌ Login failed — invalid username/password")
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

    except mysql.connector.Error as db_err:
        print(f"🔥 Login DB error: {db_err}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Database error during login"})
    except Exception as e:
        print(f"🔥 Login error: {e}") # General error logging
        # Generic error message for the user
        return templates.TemplateResponse("login.html", {"request": request, "error": "Something went wrong during login"})
    finally:
        # Ensure cursor and connection are closed
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
           
    # Check DB to get premium status
    import mysql.connector # Import locally as requested
    conn = None
    cursor = None
    user = None # Initialize user

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

    except mysql.connector.Error as err:
        print(f"Database error fetching premium status for {username}: {err}")
        # Handle DB error, perhaps redirect to an error page or show a generic message
        # For now, treat as non-premium / error
        return templates.TemplateResponse("subscribe_prompt.html", { # Or an error template
            "request": request,
            "message": "⚠️ Could not verify subscription status. Please try again later.",
            "cta": "Return Home", # Adjust CTA as needed
            "cta_link": "/" # Link for the CTA button
        })
    except Exception as e:
        print(f"An unexpected error occurred fetching premium status for {username}: {e}")
        # Handle other errors similarly
        return templates.TemplateResponse("subscribe_prompt.html", { # Or an error template
            "request": request,
            "message": "⚠️ An unexpected error occurred. Please try again later.",
            "cta": "Return Home",
            "cta_link": "/"
        })
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Check if user exists and is_premium is 1
    if not user or user.get("is_premium") != 1:
        # User is not premium — render subscription prompt template
        # Ensure subscribe_prompt.html exists and handles these variables
        return templates.TemplateResponse("subscribe_prompt.html", {
            "request": request,
            "message": "🔒 You need a premium subscription to access the dashboard.",
            "cta": "Subscribe Now",
            "cta_link": "/subscribe" # Link for the CTA button
        })

    # Premium user — show full dashboard
    # Pass necessary context for dashboard.html
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "is_premium": True, # User is confirmed premium here
        "user": username    # Pass username as 'user'
        })

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

