# stripe_payments.py
import stripe
import os
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse
import mysql.connector # Keep import if needed elsewhere, but remove DB logic below

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# This route correctly uses @router.post
@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request, # Keep request parameter
    plan: str = Query(...)
):
    try:
        # Get email directly from session (stored under 'user_id')
        user_email = request.session.get("user_id")
        if not user_email:
            raise HTTPException(status_code=401, detail="Not logged in")

        # Basic email format check (already have email from session)
        if "@" not in user_email:
            print(f"Invalid email format found in session: {user_email}")
            raise HTTPException(status_code=400, detail="Invalid email format associated with user")

        # Determine Stripe Price ID
        if plan == "monthly":
            price_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
        elif plan == "annual":
            price_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")
        else:
            raise HTTPException(status_code=400, detail="Invalid plan")

        # Check if price_id was actually found
        if not price_id:
             print(f"Stripe Price ID not found for plan: {plan}")
             raise HTTPException(status_code=500, detail=f"Configuration error: Price ID for plan '{plan}' not set.")

        print(f"🔁 Creating Stripe checkout session for {user_email} (from session) with plan {plan} using Price ID: {price_id}") # Updated log

        # Create Stripe Checkout Session using the email from session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user_email, # Use the email from session
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://cricketstatspack.com/success", # Ensure these URLs are correct
            cancel_url="https://cricketstatspack.com/cancel",
        )

        print(f"✅ Stripe session created: {session.url}")
        return {"url": session.url}

    # Specific exception for Stripe errors
    except stripe.error.StripeError as e:
        print(f"❌ Stripe API error: {str(e)}")
        # Consider logging the full error e.json_body maybe
        return {"error": f"Could not initiate checkout. Stripe error: {str(e)}"}
    # Specific exception for DB errors
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return {"error": "Could not retrieve user information. Please try again later."}
    # General exception for other issues (like HTTPException from checks)
    except HTTPException as http_exc:
        # Re-raise HTTPException to let FastAPI handle it
        raise http_exc
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}") # Catch-all for other errors
        # Provide a more generic error message to the client
        return {"error": f"An unexpected error occurred: {str(e)}"}
    finally:
        pass # No DB connection to close in this specific block anymore


@router.get("/manage-subscription")
async def manage_subscription(request: Request):
    # Get email directly from session (stored under 'user_id')
    email = request.session.get("user_id")
    if not email:
        # Redirect to login if not authenticated
        return RedirectResponse("/login")

    # Proceed with Stripe logic using the email from session
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            print(f"Stripe customer not found for email: {email}")
            raise HTTPException(status_code=404, detail="Stripe customer not found for this email.")

        customer_id = customers.data[0].id

        # Create a billing portal session
        return_url = os.getenv("STRIPE_PORTAL_RETURN_URL", "https://cricketstatspack.com/dashboard")
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )

        # Redirect to Stripe Billing Portal
        return RedirectResponse(portal_session.url, status_code=303)

    except stripe.error.StripeError as e:
        print(f"Stripe error creating portal session for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error creating portal session for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
