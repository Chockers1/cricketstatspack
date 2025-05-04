# stripe_webhook.py
from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import mysql.connector
from datetime import datetime # Import datetime

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Modify function signature to accept status and period_end
def update_subscription(email, is_active, customer_id=None, subscription_type=None, status=None, period_end=None):
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
            # Update is_premium, stripe_customer_id, subscription_type, status, and period_end on activation
            query = """
                UPDATE users
                SET is_premium = %s, stripe_customer_id = %s, subscription_type = %s,
                    subscription_status = %s, current_period_end = %s
                WHERE email = %s
            """
            params = (1, customer_id, subscription_type, status, period_end, email)
            print(f"✅ [Webhook] Activating subscription for {email}. Type: {subscription_type}, CustID: {customer_id}, Status: {status}, Period End: {period_end}")
        elif not is_active:
            # Only update is_premium on deactivation (keep customer_id, type, status, period_end)
            # Optionally clear status and period_end here if desired upon cancellation
            query = """
                UPDATE users SET is_premium = %s, subscription_status = %s
                WHERE email = %s
            """
            # Set status to 'canceled' or similar on deactivation event
            deactivation_status = "canceled" # Or derive from event if needed
            params = (0, deactivation_status, email)
            print(f"❌ [Webhook] Deactivating subscription for {email}. Setting status to {deactivation_status}.")
        else:
            # Handle cases where required info might be missing for activation
            print(f"⚠️ [Webhook] Insufficient info to update subscription for {email}. Active: {is_active}, CustID: {customer_id}, SubType: {subscription_type}, Status: {status}, PeriodEnd: {period_end}")
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
        # Invalid signature - Add detailed logging
        print(f"🚫 Invalid Stripe signature! Details: {e}")
        print(f"🔐 Header received: {stripe_signature}")
        # Decode payload for logging and truncate to avoid excessive output
        try:
            payload_str = payload.decode('utf-8')
            print(f"📦 Payload received (truncated): {payload_str[:300]}...")
        except UnicodeDecodeError:
            print("📦 Payload received (could not decode as UTF-8).")
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
        subscription_id = session.get('subscription') # Get subscription ID

        # Ensure essential data is present
        if email and customer_id:
            subscription_type = "unknown" # Default
            price_id = None
            status = None # Default status
            period_end = None # Default period end

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

                # --- Retrieve subscription details if ID exists ---
                if subscription_id:
                    try:
                        sub = stripe.Subscription.retrieve(subscription_id)
                        status = sub.get("status") # e.g., 'active', 'trialing', 'incomplete'
                        period_end_ts = sub.get("current_period_end")
                        if period_end_ts:
                            period_end = datetime.utcfromtimestamp(period_end_ts) # Convert timestamp
                        print(f"ℹ️ [Webhook] Retrieved subscription {subscription_id} details. Status: {status}, Period End: {period_end}")
                    except stripe.error.StripeError as e:
                        print(f"🔥 [Webhook] Stripe error retrieving subscription {subscription_id}: {e}")
                        # Decide if you still want to grant access even if sub retrieval fails
                        status = "error_retrieving" # Mark status as problematic
                    except Exception as e:
                        print(f"🔥 [Webhook] Unexpected error retrieving subscription {subscription_id}: {e}")
                        status = "error_retrieving"

                # Call updated function with determined type, status, and period_end
                update_subscription(email, True, customer_id, subscription_type, status, period_end)

            except Exception as e:
                 # Catch errors during price_id extraction or type determination
                 print(f"🔥 [Webhook] Error processing session data for {email}: {e}")
                 # Decide if you still want to grant premium access despite the error
                 print(f"⚠️ [Webhook] Granting premium access for {email} despite error, type set to 'unknown', status/period_end set to None.")
                 # Pass None for status and period_end in the fallback
                 update_subscription(email, True, customer_id, "unknown", None, None)

        else:
            # Log missing essential data more clearly
            print(f"⚠️ checkout.session.completed event received without required data after retrieve. Email: {email}, CustomerID: {customer_id}")

    # Handle subscription deleted or payment failed
    elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
        email = None
        customer_id = data.get('customer') # Get customer ID for potential lookup

        # For subscription deleted, email might be on the subscription object itself
        if event_type == 'customer.subscription.deleted':
             # Try getting email from customer details attached to subscription if available
             if data.get('customer_details') and data['customer_details'].get('email'):
                 email = data['customer_details']['email']
             # Fallback: use customer ID if email not directly available
             elif not email and customer_id:
                 try:
                     customer = stripe.Customer.retrieve(customer_id)
                     email = customer.email
                 except stripe.error.StripeError as e:
                     print(f"🔥 [Webhook] Error retrieving customer {customer_id} for event {event_type}: {e}")

        # For invoice payment failed, email is often directly on the invoice object
        elif event_type == 'invoice.payment_failed':
            email = data.get('customer_email')
            # Fallback: use customer ID if email not on invoice
            if not email and customer_id:
                 try:
                     customer = stripe.Customer.retrieve(customer_id)
                     email = customer.email
                 except stripe.error.StripeError as e:
                     print(f"🔥 [Webhook] Error retrieving customer {customer_id} for event {event_type}: {e}")


        if email:
            # Call update_subscription with is_active=False
            # Pass status based on event type if needed, otherwise handled in update_subscription
            update_subscription(email, False) # Status/period_end not strictly needed for deactivation query
        else:
             print(f"⚠️ [Webhook] {event_type} event received without customer_email or could not retrieve.")

    return {"status": "success"}
