# stripe_webhook.py
from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import mysql.connector

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

def update_subscription(email, is_active):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    query = """
        UPDATE users SET is_premium = %s WHERE username = %s
    """
    cursor.execute(query, (1 if is_active else 0, email))
    conn.commit()
    cursor.close()
    conn.close()

@router.post("/api/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event['type']
    data = event['data']['object']

    if event_type == 'checkout.session.completed':
        email = data['customer_email']
        update_subscription(email, True)
        print(f"✅ Premium access granted to {email}")

    elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
        email = data['customer_email']
        update_subscription(email, False)
        print(f"❌ Premium access removed for {email}")

    return {"status": "success"}
