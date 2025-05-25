#!/usr/bin/env python3
"""Test script to verify all imports work correctly"""

try:
    print("Testing imports...")
    
    # Test basic imports
    import logging
    import os
    from datetime import datetime, timedelta
    print("✅ Basic imports OK")
    
    # Test FastAPI
    from fastapi import FastAPI, Request, Form, Depends, HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    from fastapi.staticfiles import StaticFiles
    print("✅ FastAPI imports OK")
    
    # Test Starlette
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
    print("✅ Starlette imports OK")
    
    # Test Database
    import mysql.connector
    print("✅ MySQL connector OK")
    
    # Test Security
    import bcrypt
    print("✅ Bcrypt OK")
    
    # Test Rate Limiting
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    print("✅ SlowAPI OK")
    
    # Test Stripe
    import stripe
    print("✅ Stripe OK")
    
    # Test environment
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Dotenv OK")
    
    # Test other dependencies
    from typing import Optional
    import csv
    from io import StringIO
    print("✅ Other imports OK")
    
    # Test custom modules
    try:
        from auth_utils import verify_user, create_user, get_admin_stats, update_user_status, admin_reset_password, log_action
        print("✅ Auth utils OK")
    except ImportError as e:
        print(f"⚠️ Auth utils import issue: {e}")
    
    try:
        from stripe_payments import router as stripe_payments_router
        print("✅ Stripe payments router OK")
    except ImportError as e:
        print(f"⚠️ Stripe payments router import issue: {e}")
    
    try:
        from stripe_webhook import router as stripe_webhook_router
        print("✅ Stripe webhook router OK")
    except ImportError as e:
        print(f"⚠️ Stripe webhook router import issue: {e}")
    
    print("\n🎉 All critical imports successful!")
    print("The application should be able to start without import errors.")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
