# stripe_payments.py
import stripe
import os
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/create-checkout-session")
async def create_checkout_session(plan: str = Query(...)):
    try:
        if plan == "monthly":
            price_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
        elif plan == "annual":
            price_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")
        else:
            raise HTTPException(status_code=400, detail="Invalid plan")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://cricketstatspack.com/success",
            cancel_url="https://cricketstatspack.com/cancel",
        )
        return {"url": session.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/manage-subscription")
async def manage_subscription(request: Request):
    user_email = request.session.get("user_id") # Assuming user_id in session is the email
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Fetch Stripe customer by email
        customers = stripe.Customer.list(email=user_email, limit=1).data
        if not customers:
            # Handle case where customer is not found - perhaps redirect to pricing or show a message
            raise HTTPException(status_code=404, detail="Stripe customer not found for this email.")

        customer_id = customers[0].id
        
        # Ensure a return URL is configured in your environment variables
        return_url = os.getenv("STRIPE_PORTAL_RETURN_URL", "https://cricketstatspack.com/account") # Provide a default or ensure it's set

        # Create a Billing Portal session
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        # Redirect the user to the Billing Portal
        return RedirectResponse(session.url, status_code=303)

    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        # Handle other potential errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
