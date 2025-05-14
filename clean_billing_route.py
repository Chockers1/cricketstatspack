# -- BILLING HISTORY --

@app.get("/billing", response_class=HTMLResponse)
async def billing_history(request: Request):
    user_email = request.session.get("user_id")
    logger.info(f"Billing history page accessed by user: {user_email if user_email else 'Guest'}")
    
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)

    # First, check if the user has premium status in their session
    is_premium = request.session.get("is_premium", False)
    logger.info(f"User {user_email} has premium status: {is_premium}")
    
    conn = None
    cursor = None
    try:
        # 1) Fetch stripe_customer_id from your DB
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT stripe_customer_id FROM users WHERE email=%s", (user_email,))
        row = cursor.fetchone()
        logger.debug(f"Retrieved Stripe customer data for {user_email}")
        
    except mysql.connector.Error as err:
        logger.error(f"Database error retrieving Stripe customer ID for {user_email}: {err}")
        row = None
    except Exception as e:
        logger.error(f"Unexpected error retrieving Stripe customer ID for {user_email}: {e}")
        row = None
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not row or not row.get("stripe_customer_id"):
        logger.info(f"No Stripe customer ID found for user {user_email}")
        
        # If the user is marked as premium but has no Stripe customer ID,
        # fetch additional information for debugging
        if is_premium:
            logger.warning(f"User {user_email} marked as premium but has no Stripe customer ID")
            try:
                conn = mysql.connector.connect(
                    host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT email, is_premium, subscription_type, subscription_status, 
                           current_period_end, stripe_customer_id
                    FROM users WHERE email = %s
                """, (user_email,))
                user_details = cursor.fetchone()
                logger.debug(f"User details for debugging: {user_details}")
            except Exception as db_err:
                logger.error(f"Error fetching additional user details: {db_err}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        
        # Create dummy subscription for premium users with missing Stripe info
        if is_premium:
            logger.warning(f"Creating fallback subscription display for premium user {user_email}")
            subscription = {
                "plan_name": "Premium Plan",
                "status": "active",
                "current_period_end": "Not available"
            }
            return templates.TemplateResponse("billing.html", {
                "request": request,
                "subscription": subscription,
                "next_invoice_date": None,
                "portal_url": None,
                "invoices": []
            })
        else:
            return templates.TemplateResponse("billing.html", {
                "request": request,
                "subscription": None,
                "next_invoice_date": None,
                "portal_url": None,
                "invoices": []
            })

    cust_id = row["stripe_customer_id"]
    subscription = None
    next_invoice_date = None
    portal_url = None
    invoices = []
    
    try:
        # 2) Current Subscription
        logger.debug(f"Fetching subscription data for customer_id: {cust_id}")
        subs = stripe.Subscription.list(customer=cust_id, status="all", limit=1).data
        logger.debug(f"Found {len(subs)} subscriptions for customer {cust_id}")
        
        current_sub = subs[0] if subs else None
        
        if current_sub:
            logger.debug(f"Subscription details: id={current_sub.id}, status={current_sub.status}")
            if (not hasattr(current_sub, 'items') or 
                not hasattr(current_sub.items, 'data') or 
                len(current_sub.items.data) == 0):
                logger.error(f"Subscription {current_sub.id} has no valid items")
            else:
                plan_item = current_sub["items"]["data"][0]["plan"]
                subscription = {
                    "plan_name": plan_item.get("nickname", plan_item["id"]),
                    "status": current_sub["status"],
                    "current_period_end": datetime.fromtimestamp(
                        current_sub["current_period_end"]
                    ).strftime("%Y-%m-%d")
                }
                logger.debug(f"Found active subscription for {user_email}: {subscription['plan_name']}")
        else:
            logger.warning(f"No subscription found for customer {cust_id}, but user has customer ID")
            
            # Create fallback subscription for premium users with customer ID but no subscription
            if is_premium:
                logger.warning(f"Creating fallback subscription for premium user with customer ID but no subscription")
                subscription = {
                    "plan_name": "Premium Plan",
                    "status": "active",
                    "current_period_end": "Not available"
                }

        # 3) Next Upcoming Invoice
        try:
            logger.debug(f"Fetching upcoming invoice for customer_id: {cust_id}")
            upcoming = stripe.Invoice.upcoming(customer=cust_id)
            next_invoice_date = datetime.fromtimestamp(
                upcoming.next_payment_attempt or upcoming.period_end
            ).strftime("%Y-%m-%d")
            logger.debug(f"Next invoice date for {user_email}: {next_invoice_date}")
        except stripe.error.InvalidRequestError as inv_err:
            logger.info(f"No upcoming invoice for {user_email}: {str(inv_err)}")
            next_invoice_date = None

        # 4) Customer Portal Link
        logger.debug(f"Creating customer portal session for {user_email}")
        portal_session = stripe.billing_portal.Session.create(
            customer=cust_id,
            return_url=STRIPE_PORTAL_RETURN_URL
        )
        portal_url = portal_session.url
        logger.debug(f"Generated customer portal URL for {user_email}")

        # 5) Past Invoices
        logger.debug(f"Fetching invoice history for customer_id: {cust_id}")
        stripe_invs = stripe.Invoice.list(customer=cust_id, limit=100).data
        
        invoices = [
            {
                "date": datetime.fromtimestamp(inv.created).strftime("%Y-%m-%d"),
                "amount": f"{inv.amount_paid/100:.2f} {inv.currency.upper()}",
                "status": inv.status,
                "pdf": inv.invoice_pdf
            }
            for inv in stripe_invs
        ]
        
        logger.info(f"Retrieved {len(invoices)} invoices for user {user_email}")
        
    except stripe.error.StripeError as stripe_err:
        logger.error(f"Stripe API error for user {user_email}: {str(stripe_err)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching billing data for user {user_email}: {str(e)}", exc_info=True)

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "subscription": subscription,
        "next_invoice_date": next_invoice_date,
        "portal_url": portal_url,
        "invoices": invoices
    })
