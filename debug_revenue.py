import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_premium_users():
    """Check subscription details for all premium users"""
    try:
        print("Starting database connection...")
        
        # Check environment variables
        db_host = os.getenv("DB_HOST")
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_name = os.getenv("DB_NAME")
        
        print(f"DB Host: {db_host}")
        print(f"DB User: {db_user}")
        print(f"DB Name: {db_name}")
        print(f"DB Pass: {'***' if db_pass else 'Not set'}")
        
        if not all([db_host, db_user, db_pass, db_name]):
            print("ERROR: Missing database environment variables!")
            return
        
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get all premium users with their subscription details
        cursor.execute("""
            SELECT email, is_premium, subscription_type, subscription_status, 
                   current_period_end, stripe_customer_id, created_at
            FROM users 
            WHERE is_premium = 1
            ORDER BY created_at DESC
        """)
        
        premium_users = cursor.fetchall()
        
        print(f"Found {len(premium_users)} premium users:")
        print("=" * 80)
        
        monthly_count = 0
        annual_count = 0
        missing_type_count = 0
        
        for user in premium_users:
            print(f"Email: {user['email']}")
            print(f"  Premium: {user['is_premium']}")
            print(f"  Subscription Type: {user['subscription_type']}")
            print(f"  Subscription Status: {user['subscription_status']}")
            print(f"  Period End: {user['current_period_end']}")
            print(f"  Stripe Customer ID: {user['stripe_customer_id']}")
            print(f"  Created: {user['created_at']}")
            print("-" * 40)
            
            # Count subscription types
            if user['subscription_type'] == 'monthly':
                monthly_count += 1
            elif user['subscription_type'] == 'annual':
                annual_count += 1
            else:
                missing_type_count += 1
        
        print(f"\nSubscription Type Summary:")
        print(f"Monthly subscriptions: {monthly_count}")
        print(f"Annual subscriptions: {annual_count}")
        print(f"Missing subscription type: {missing_type_count}")
        
        # Calculate expected revenue
        monthly_revenue = (monthly_count * 5.00) + (annual_count * (50.00 / 12))
        print(f"\nExpected monthly revenue calculation:")
        print(f"Monthly users ({monthly_count}) × £5.00 = £{monthly_count * 5.00:.2f}")
        print(f"Annual users ({annual_count}) × £{50.00 / 12:.2f} = £{annual_count * (50.00 / 12):.2f}")
        print(f"Total expected monthly revenue: £{monthly_revenue:.2f}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_premium_users()
