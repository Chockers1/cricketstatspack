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
        session = data # The 'object' is the session object
        email = session.get('customer_email')
        customer_id = session.get('customer')
        subscription_id = session.get('subscription') # Get subscription ID

        if email and customer_id and subscription_id:
            subscription_type = None
            try:
                # Retrieve the subscription to find the price ID
                subscription_details = stripe.Subscription.retrieve(subscription_id)
                # Assuming the first item's price ID determines the type
                if subscription_details.items and subscription_details.items.data:
                    price_id = subscription_details.items.data[0].price.id
                    monthly_id = os.getenv("STRIPE_PRICE_ID_MONTHLY")
                    annual_id = os.getenv("STRIPE_PRICE_ID_ANNUAL")

                    if price_id == monthly_id:
                        subscription_type = "monthly"
                    elif price_id == annual_id:
                        subscription_type = "annual"
                    else:
                        print(f"⚠️ [Webhook] Unknown price ID {price_id} for subscription {subscription_id}")

                if subscription_type:
                     # Call updated function with all details
                    update_subscription(email, True, customer_id, subscription_type)
                else:
                    # Still activate premium even if type is unknown, but log it
                    print(f"⚠️ [Webhook] Could not determine subscription type for {email}, activating premium without type.")
                    update_subscription(email, True, customer_id, None) # Pass None for type

            except stripe.error.StripeError as e:
                print(f"🔥 [Webhook] Stripe error retrieving subscription {subscription_id}: {e}")
                # Decide if you still want to grant premium access despite the error
                # update_subscription(email, True, customer_id, None) # Example: Grant access anyway
            except Exception as e:
                 print(f"🔥 [Webhook] Unexpected error processing subscription details for {email}: {e}")

        else:
            print(f"⚠️ checkout.session.completed event received without required data. Email: {email}, CustID: {customer_id}, SubID: {subscription_id}")

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
