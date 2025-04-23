from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from auth_utils import verify_user

print("🔥 FASTAPI LOADED 🔥")


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Home page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
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

# Dummy dashboard route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
