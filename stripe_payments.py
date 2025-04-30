# stripe_payments.py
import stripe
import os
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# This route correctly uses @router.post
@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request, # Keep request parameter
    plan: str = Query(...)
):
    try:
        # Keep user email retrieval from session
        user_email = request.session.get("user_id")
        if not user_email:
            raise HTTPException(status_code=401, detail="User not logged in")

        if plan == "monthly":
            price_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
        elif plan == "annual":
            price_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")
        else:
            raise HTTPException(status_code=400, detail="Invalid plan")

        print(f"🔁 Using Stripe Price ID: {price_id}") # Add print statement

        session = stripe.checkout.Session.create(
            customer_email=user_email, # Keep using customer_email
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://cricketstatspack.com/success",
            cancel_url="https://cricketstatspack.com/cancel",
        )

        print(f"✅ Stripe session created: {session.url}") # Add print statement
        return {"url": session.url}

    except Exception as e:
        print(f"❌ Stripe session error: {str(e)}") # Add detailed print
        # Return the specific error message in the response
        return {"error": f"Stripe session error: {str(e)}"}

@router.get("/manage-subscription")
async def manage_subscription(request: Request):
    user_id = request.session.get("user_id") # user_id from session is the username
    if not user_id:
        # Redirect to login if not authenticated
        return RedirectResponse("/login")

    # Get email from DB using username (user_id)
    import mysql.connector # Import locally
    conn = None
    cursor = None
    email = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM users WHERE username = %s", (user_id,))
        result = cursor.fetchone()

        if not result or "email" not in result:
            # Handle case where user or email is not found in DB
            print(f"Email not found in DB for username: {user_id}")
            raise HTTPException(status_code=404, detail="User email not found.")

        email = result["email"]

    except mysql.connector.Error as err:
        print(f"Database error fetching email for {user_id}: {err}")
        raise HTTPException(status_code=500, detail="Database error.")
    except Exception as e:
        print(f"Unexpected error fetching email for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Proceed with Stripe logic only if email was found
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            # Handle case where customer not found in Stripe
            print(f"Stripe customer not found for email: {email}")
            # Maybe redirect to a page explaining this? Or show an error.
            # For now, raise an HTTPException or return an error response.
            # Depending on desired UX, could redirect to /subscribe or /dashboard with a message.
            raise HTTPException(status_code=404, detail="Stripe customer not found for this email.")

        customer_id = customers.data[0].id

        # Create a billing portal session
        # Ensure the return URL is appropriate, e.g., back to the dashboard
        return_url = os.getenv("STRIPE_PORTAL_RETURN_URL", "https://cricketstatspack.com/dashboard")
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )

        # Redirect to Stripe Billing Portal
        return RedirectResponse(portal_session.url, status_code=303) # Use 303 for POST-redirect-GET pattern

    except stripe.error.StripeError as e:
        print(f"Stripe error creating portal session for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error creating portal session for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
