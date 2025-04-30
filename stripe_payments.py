import stripe
import os
from fastapi import APIRouter

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/create-checkout-session")
async def create_checkout_session(plan: str):
    try:
        if plan == "monthly":
            price_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
        elif plan == "annual":
            price_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")
        else:
            raise ValueError("Invalid plan selected")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://cricketstatspack.com/success",
            cancel_url="https://cricketstatspack.com/cancel",
        )
        return {"url": session.url}

    except Exception as e:
        return {"error": str(e)}
