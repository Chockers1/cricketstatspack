"""
Quick revenue verification script
"""
import sys

# Based on the MySQL data:
monthly_subs = 0  # No users with subscription_type = 'monthly'
annual_subs = 4   # 4 users with subscription_type = 'annual'

# Current pricing (GBP)
monthly_price = 5.00
annual_price = 49.99

# Calculate monthly revenue equivalent
monthly_revenue = (monthly_subs * monthly_price) + (annual_subs * (annual_price / 12))

print("=== Revenue Calculation Verification ===", flush=True)
print(f"Monthly subscribers: {monthly_subs}", flush=True)
print(f"Annual subscribers: {annual_subs}", flush=True)
print(f"", flush=True)
print(f"Monthly pricing: £{monthly_price:.2f}", flush=True)
print(f"Annual pricing: £{annual_price:.2f}", flush=True)
print(f"Annual monthly equivalent: £{annual_price / 12:.2f}", flush=True)
print(f"", flush=True)
print(f"Revenue calculation:", flush=True)
print(f"  Monthly: {monthly_subs} × £{monthly_price:.2f} = £{monthly_subs * monthly_price:.2f}", flush=True)
print(f"  Annual: {annual_subs} × £{annual_price / 12:.2f} = £{annual_subs * (annual_price / 12):.2f}", flush=True)
print(f"", flush=True)
print(f"Total monthly revenue: £{monthly_revenue:.2f}", flush=True)
print(f"", flush=True)

# Previous calculation with £50.00 annual
old_annual_price = 50.00
old_monthly_revenue = (monthly_subs * monthly_price) + (annual_subs * (old_annual_price / 12))
print(f"Previous calculation (£50.00 annual): £{old_monthly_revenue:.2f}", flush=True)
print(f"Difference: £{monthly_revenue - old_monthly_revenue:.2f}", flush=True)

sys.stdout.flush()
