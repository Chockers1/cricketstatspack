# stripe_webhook.py
from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import mysql.connector

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

def update_subscription(email, is_active):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        # Corrected query to update based on email - This matches the prompt
        query = """
            UPDATE users SET is_premium = %s WHERE email = %s
        """
        cursor.execute(query, (1 if is_active else 0, email))
        conn.commit()
        # Check if any row was actually updated
        if cursor.rowcount == 0:
            print(f"⚠️ [Webhook] No user found with email {email} to update subscription status.") # Added context
        else:
            print(f"✅ [Webhook] Subscription status updated for {email} to {is_active}.") # Added context

    except mysql.connector.Error as err:
        print(f"🔥 [Webhook] Database error updating subscription for {email}: {err}") # Added context
    except Exception as e:
        print(f"🔥 [Webhook] Unexpected error updating subscription for {email}: {e}") # Added context
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/api/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print(f"Webhook error: Invalid payload - {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Webhook error: Invalid signature - {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"Webhook error: Unexpected error constructing event - {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


    event_type = event['type']
    data = event['data']['object']

    # Use .get() for safer access and check if email exists
    if event_type == 'checkout.session.completed':
        email = data.get('customer_email')
        if email:
            update_subscription(email, True)
            print(f"✅ Premium access granted to {email} via checkout completion.")
        else:
            print("⚠️ checkout.session.completed event received without customer_email.")

    elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
        # Need to handle different data structures for these events if necessary
        # For subscription deleted, customer email might be nested differently or need separate retrieval
        # For invoice.payment_failed, email is usually directly available
        email = data.get('customer_email')

        # If email not directly on object, try fetching customer details if needed (more robust)
        if not email and data.get('customer'):
             try:
                 customer = stripe.Customer.retrieve(data.get('customer'))
                 email = customer.email
             except stripe.error.StripeError as e:
                 print(f"Error retrieving customer {data.get('customer')} for event {event_type}: {e}")

        if email:
            update_subscription(email, False)
            print(f"❌ Premium access potentially removed for {email} due to event: {event_type}")
        else:
             print(f"⚠️ {event_type} event received without customer_email or could not retrieve.")

    return {"status": "success"}
