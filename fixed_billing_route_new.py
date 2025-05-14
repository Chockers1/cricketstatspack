@app.get("/billing", response_class=HTMLResponse)
async def billing(request: Request):
    """Display billing history and subscription info"""
    user_email = request.session.get("user_id")  # This will hold the email now
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)

    # First, check if the user has premium status in their session
    is_premium = request.session.get("is_premium", False)
    logger.info(f"User {user_email} has premium status: {is_premium}")
    
    conn = None
    cursor = None
    row = None
    subscription = None
    next_invoice_date = None
    portal_url = None
    invoices = []
    
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
    except Exception as e:
        logger.error(f"Unexpected error retrieving Stripe customer ID for {user_email}: {e}")
    finally:
        if cursor: 
            cursor.close()
        if conn and conn.is_connected(): 
            conn.close()

    # Handle case where no Stripe customer ID is found
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
                if cursor: 
                    cursor.close()
                if conn and conn.is_connected(): 
                    conn.close()
        
        # Create dummy subscription for premium users with missing Stripe info
        if is_premium:
            logger.warning(f"Creating fallback subscription display for premium user {user_email}")
            subscription = {
                "plan_name": "Premium Plan",
                "status": "active",
                "current_period_end": "Not available"
            }
            
            # Try to generate a Stripe Customer Portal URL even for users without a customer ID
            try:
                # Search for a customer with the given email
                customers = stripe.Customer.list(email=user_email, limit=1).data
                if customers:
                    cust_id = customers[0].id
                    logger.info(f"Found Stripe customer by email search: {cust_id}")
                    
                    # Create portal session
                    portal_session = stripe.billing_portal.Session.create(
                        customer=cust_id,
                        return_url=STRIPE_PORTAL_RETURN_URL
                    )
                    portal_url = portal_session.url
                    logger.info(f"Generated portal URL for user {user_email} via email search")
            except Exception as e:
                logger.error(f"Could not generate portal URL for premium user {user_email}: {e}")
                # Continue without portal URL
                
            return templates.TemplateResponse("billing.html", {
                "request": request,
                "subscription": subscription,
                "next_invoice_date": None,
                "portal_url": portal_url,
                "invoices": []
            })
        else:
            # Non-premium user without Stripe customer ID
            return templates.TemplateResponse("billing.html", {
                "request": request,
                "subscription": None,
                "next_invoice_date": None,
                "portal_url": None,
                "invoices": []
            })

    # User has stripe_customer_id, proceed with Stripe API calls
    cust_id = row["stripe_customer_id"]
    
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
            if hasattr(upcoming, 'next_payment_attempt') and upcoming.next_payment_attempt:
                payment_date = upcoming.next_payment_attempt
            elif hasattr(upcoming, 'period_end') and upcoming.period_end:
                payment_date = upcoming.period_end
            else:
                payment_date = None
                
            if payment_date:
                next_invoice_date = datetime.fromtimestamp(payment_date).strftime("%Y-%m-%d")
                logger.debug(f"Next invoice date for {user_email}: {next_invoice_date}")
        except stripe.error.InvalidRequestError as inv_err:
            logger.info(f"No upcoming invoice for {user_email}: {str(inv_err)}")
        except Exception as inv_err:
            logger.error(f"Error getting upcoming invoice for {user_email}: {str(inv_err)}")

        # 4) Customer Portal Link
        logger.debug(f"Creating customer portal session for {user_email}")
        portal_session = stripe.billing_portal.Session.create(
            customer=cust_id,
            return_url=STRIPE_PORTAL_RETURN_URL
        )
        portal_url = portal_session.url
        logger.debug(f"Generated customer portal URL for {user_email}")

        # 5) Past Invoices
        try:
            logger.debug(f"Fetching invoice history for customer_id: {cust_id}")
            stripe_invs = stripe.Invoice.list(customer=cust_id, limit=100).data
            
            invoices = []
            for inv in stripe_invs:
                try:
                    invoice_entry = {
                        "date": datetime.fromtimestamp(inv.created).strftime("%Y-%m-%d"),
                        "amount": f"{inv.amount_paid/100:.2f} {inv.currency.upper()}",
                        "status": inv.status,
                        "pdf": inv.invoice_pdf if hasattr(inv, 'invoice_pdf') else "#"
                    }
                    invoices.append(invoice_entry)
                except Exception as inv_err:
                    logger.error(f"Error processing invoice {inv.id}: {str(inv_err)}")
                    continue
            
            logger.info(f"Retrieved {len(invoices)} invoices for user {user_email}")
        except Exception as inv_err:
            logger.error(f"Error retrieving invoices for {user_email}: {str(inv_err)}")
            invoices = []
        
    except stripe.error.StripeError as stripe_err:
        logger.error(f"Stripe API error for user {user_email}: {str(stripe_err)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching billing data for user {user_email}: {str(e)}", exc_info=True)

    # Final fallback - ensure premium users always have a subscription object
    if is_premium and subscription is None:
        logger.warning(f"Fixing display for premium user with no subscription data: {user_email}")
        
        # Try to get the period_end date from the database if possible
        period_end = "Not available"
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT current_period_end FROM users WHERE email=%s", (user_email,))
            user_data = cursor.fetchone()
            if user_data and user_data.get("current_period_end"):
                try:
                    if isinstance(user_data["current_period_end"], (int, float)):
                        # If it's stored as a timestamp
                        period_end = datetime.fromtimestamp(user_data["current_period_end"]).strftime("%Y-%m-%d")
                    elif isinstance(user_data["current_period_end"], datetime):
                        # If it's already a datetime object
                        period_end = user_data["current_period_end"].strftime("%Y-%m-%d")
                    elif isinstance(user_data["current_period_end"], str):
                        # If it's already a formatted string
                        period_end = user_data["current_period_end"]
                    else:
                        logger.warning(f"Unrecognized current_period_end type: {type(user_data['current_period_end'])}")
                        period_end = str(user_data["current_period_end"])
                except Exception as date_err:
                    logger.error(f"Error formatting current_period_end: {date_err}")
            else:
                logger.warning(f"No current_period_end found in database for user {user_email}")
        except Exception as e:
            logger.error(f"Error retrieving period_end from database for {user_email}: {e}")
        finally:
            if cursor: 
                cursor.close()
            if conn and conn.is_connected(): 
                conn.close()
            
        subscription = {
            "plan_name": "Premium Plan",
            "status": "active",
            "current_period_end": period_end
        }

    # Return template with all collected data
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "subscription": subscription,
        "next_invoice_date": next_invoice_date,
        "portal_url": portal_url,
        "invoices": invoices
    })
