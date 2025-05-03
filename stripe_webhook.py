# stripe_webhook.py
from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import mysql.connector

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Modify function signature to accept customer_id and subscription_type
def update_subscription(email, is_active, customer_id=None, subscription_type=None):
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

        # Build query dynamically based on whether it's activation or deactivation
        if is_active and customer_id and subscription_type:
            # Update is_premium, stripe_customer_id, and subscription_type on activation
            query = """
                UPDATE users
                SET is_premium = %s, stripe_customer_id = %s, subscription_type = %s
                WHERE email = %s
            """
            params = (1, customer_id, subscription_type, email)
            print(f"✅ [Webhook] Activating subscription for {email}. Type: {subscription_type}, Customer ID: {customer_id}")
        elif not is_active:
            # Only update is_premium on deactivation (keep customer_id and type)
            query = """
                UPDATE users SET is_premium = %s WHERE email = %s
            """
            params = (0, email)
            print(f"❌ [Webhook] Deactivating subscription for {email}.")
        else:
            # Handle cases where required info might be missing for activation
            print(f"⚠️ [Webhook] Insufficient info to update subscription for {email}. Active: {is_active}, CustID: {customer_id}, SubType: {subscription_type}")
            return # Don't proceed if info is missing for activation

        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            print(f"⚠️ [Webhook] No user found with email {email} to update subscription status.")
        else:
            print(f"✅ [Webhook] DB updated successfully for {email}.")

    except mysql.connector.Error as err:
        print(f"🔥 [Webhook] Database error updating subscription for {email}: {err}")
    except Exception as e:
        print(f"🔥 [Webhook] Unexpected error updating subscription for {email}: {e}")
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

    # Handle checkout.session.completed
    if event_type == 'checkout.session.completed':
        # Add the retrieve call here to ensure line_items are expanded
        try:
            session = stripe.checkout.Session.retrieve(
                data["id"], # Use the ID from the event data
                expand=["line_items"]
            )
            print(f"ℹ️ [Webhook] Retrieved expanded checkout session: {session.id}")
        except stripe.error.StripeError as e:
            print(f"🔥 [Webhook] Stripe error retrieving expanded checkout session {data.get('id')}: {e}")
            # If retrieval fails, we might not be able to determine the plan reliably.
            # Raise an exception to signal a server error.
            raise HTTPException(status_code=500, detail="Failed to retrieve expanded session details from Stripe.")
        except Exception as e:
             print(f"🔥 [Webhook] Unexpected error retrieving expanded checkout session {data.get('id')}: {e}")
             raise HTTPException(status_code=500, detail="Unexpected error retrieving session details.")

        # Now use the retrieved 'session' object which includes line_items
        email = session.get('customer_email')
        customer_id = session.get('customer')
        # subscription_id = session.get('subscription') # Keep if needed for logging

        # Ensure essential data is present
        if email and customer_id:
            subscription_type = "unknown" # Default
            price_id = None

            # --- Try extracting price_id directly from the retrieved session line_items ---
            try:
                # Use line_items (should now be present due to expand)
                if session.get('line_items') and session['line_items'].get('data'):
                    price_id = session['line_items']['data'][0]['price']['id']
                    print(f"ℹ️ [Webhook] Extracted price_id from expanded line_items: {price_id}")
                else:
                    # This case should be less likely now, but log it.
                    print("⚠️ [Webhook] line_items not found in retrieved expanded session object.")
                    # Optional: Add fallback logic here if needed, e.g., retrieving subscription

                # Determine subscription type based on price_id
                if price_id:
                    monthly_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
                    annual_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")

                    if price_id == monthly_id:
                        subscription_type = "monthly"
                    elif price_id == annual_id:
                        subscription_type = "annual"
                    else:
                        print(f"⚠️ [Webhook] Price ID {price_id} does not match known monthly/annual IDs.")
                        subscription_type = "unknown" # Keep as unknown if no match
                else:
                    print("⚠️ [Webhook] Failed to determine price_id. Subscription type remains 'unknown'.")


                # Call updated function with determined type
                update_subscription(email, True, customer_id, subscription_type)

            except Exception as e:
                 # Catch errors during price_id extraction or type determination
                 print(f"🔥 [Webhook] Error processing session data for {email}: {e}")
                 # Decide if you still want to grant premium access despite the error
                 print(f"⚠️ [Webhook] Granting premium access for {email} despite error, type set to 'unknown'.")
                 update_subscription(email, True, customer_id, "unknown") # Grant access with unknown type

        else:
            # Log missing essential data more clearly
            print(f"⚠️ checkout.session.completed event received without required data after retrieve. Email: {email}, CustomerID: {customer_id}")

    # Handle subscription deleted or payment failed
    elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
        email = data.get('customer_email')
        customer_id = data.get('customer') # Get customer ID for potential lookup

        # If email not directly on object, try fetching customer details
        if not email and customer_id:
             try:
                 customer = stripe.Customer.retrieve(customer_id)
                 email = customer.email
             except stripe.error.StripeError as e:
                 print(f"🔥 [Webhook] Error retrieving customer {customer_id} for event {event_type}: {e}")

        if email:
            # Call update_subscription with is_active=False
            update_subscription(email, False) # No need for customer_id or type on deactivation
        else:
             print(f"⚠️ [Webhook] {event_type} event received without customer_email or could not retrieve.")

    return {"status": "success"}
