from fastapi import FastAPI, Request, Form, Depends, HTTPException # Add Depends and HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from auth_utils import verify_user, create_user # Import create_user

print("🔥 FASTAPI LOADED 🔥")


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Copilot: add require_login dependency
def require_login(request: Request):
  if request.cookies.get("logged_in") != "yes":
      raise HTTPException(status_code=401, detail="Not authenticated")

# Home page
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    # If there's a user_id in session, redirect to dashboard
    # Note: This requires session middleware to be configured
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard")
    # Otherwise render the public index
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

# ✅ Single, correct POST route for login
@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    print("🚨 Login POST received")
    if verify_user(username, password):
        print("✅ Login success — redirecting to dashboard")
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="logged_in", value="yes", httponly=True)
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
async def register_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if create_user(username, password):
        print(f"✅ User '{username}' created successfully — redirecting to login")
        return RedirectResponse(url="/login", status_code=302)
    else:
        print(f"❌ Registration failed for user '{username}' — username might already exist")
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists or invalid input"})

# Dummy dashboard route
@app.get("/dashboard", dependencies=[Depends(require_login)], response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Copilot: add logout endpoint
@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="logged_in")
    print("✅ Logout successful — redirecting to home")
    return response
