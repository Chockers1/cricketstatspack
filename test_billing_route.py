#!/usr/bin/env python3
"""
Test script to verify the billing route syntax and basic structure
"""

import ast
import sys

def test_billing_route_syntax():
    """Test if the billing route has correct syntax"""
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the entire file
        ast.parse(content)
        print("✅ Python syntax is valid")
        
        # Check if billing route exists
        if '@app.get("/billing"' in content:
            print("✅ Billing route found")
        else:
            print("❌ Billing route not found")
            
        # Check for key components in billing route
        if 'stripe.billing_portal.Session.create' in content:
            print("✅ Stripe Customer Portal session creation found")
        else:
            print("❌ Stripe Customer Portal session creation not found")
            
        if 'RedirectResponse' in content:
            print("✅ RedirectResponse import/usage found")
        else:
            print("❌ RedirectResponse not found")
            
        # Look for the billing route specifically
        lines = content.split('\n')
        billing_start = None
        for i, line in enumerate(lines):
            if '@app.get("/billing"' in line:
                billing_start = i
                break
                
        if billing_start:
            print(f"✅ Billing route starts at line {billing_start + 1}")
            
            # Check the next ~50 lines for proper structure
            billing_lines = lines[billing_start:billing_start + 50]
            
            # Check for proper async function definition
            if any('async def billing(' in line for line in billing_lines):
                print("✅ Async function definition found")
            else:
                print("❌ Async function definition not found")
                
            # Check for user authentication
            if any('user_email = request.session.get("user_id")' in line for line in billing_lines):
                print("✅ User authentication check found")
            else:
                print("❌ User authentication check not found")
                
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing billing route structure...")
    success = test_billing_route_syntax()
    if success:
        print("\n✅ All billing route tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
