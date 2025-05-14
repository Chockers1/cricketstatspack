@app.get("/cancel-subscription")
async def cancel_subscription(request: Request):
    """Cancel the user's subscription and redirect to the billing page."""
    user_email = request.session.get("user_id")
    if not user_email:
        logger.info("User not logged in, redirecting to login.")
        return RedirectResponse("/login", status_code=303)
    
    logger.info(f"User {user_email} attempting to cancel subscription")
    
    # Show confirmation page first
    if not request.query_params.get("confirm"):
        return templates.TemplateResponse("cancel_confirm.html", {
            "request": request,
            "email": user_email
        })
    
    conn = None
    cursor = None
    try:
        # Fetch stripe_customer_id and subscription_id from the database
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"), database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT stripe_customer_id, subscription_id 
            FROM users 
            WHERE email = %s
        """, (user_email,))
        row = cursor.fetchone()
        
        if not row or not row.get("stripe_customer_id") or not row.get("subscription_id"):
            logger.warning(f"No valid subscription information found for user {user_email}")
            return RedirectResponse("/billing?error=no_subscription", status_code=303)
        
        # Cancel the subscription via Stripe API
        try:
            subscription = stripe.Subscription.retrieve(row["subscription_id"])
            stripe.Subscription.modify(
                row["subscription_id"],
                cancel_at_period_end=True
            )
            
            # Update the user record in the database
            cursor.execute("""
                UPDATE users 
                SET subscription_status = 'canceled' 
                WHERE email = %s
            """, (user_email,))
            conn.commit()
            
            logger.info(f"Subscription {row['subscription_id']} for {user_email} marked for cancellation at period end")
            
            # Subscription will remain active until the end of the period
            return RedirectResponse("/billing?message=cancellation_scheduled", status_code=303)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription for {user_email}: {e}")
            return RedirectResponse("/billing?error=stripe_error", status_code=303)
        
    except mysql.connector.Error as err:
        logger.error(f"Database error retrieving subscription information for {user_email}: {err}")
        return RedirectResponse("/billing?error=db_error", status_code=303)
    except Exception as e:
        logger.error(f"Unexpected error canceling subscription for {user_email}: {e}", exc_info=True)
        return RedirectResponse("/billing?error=unknown", status_code=303)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
