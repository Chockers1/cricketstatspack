#!/usr/bin/env python3
"""Diagnostic script to identify potential runtime issues in the billing route"""

import ast
import re

def analyze_billing_route():
    print("🔍 Analyzing billing route for potential issues...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the billing function
    billing_start = content.find("@app.get(\"/billing\"")
    if billing_start == -1:
        print("❌ Could not find billing route")
        return
    
    # Find the end of the billing function (next route definition)
    next_route = content.find("@app.", billing_start + 1)
    if next_route == -1:
        billing_content = content[billing_start:]
    else:
        billing_content = content[billing_start:next_route]
    
    print(f"✅ Found billing route ({len(billing_content)} characters)")
    
    # Check for common issues
    issues = []
    
    # Check for undefined variables
    if "portal_url" in billing_content and billing_content.count("portal_url = None") == 0:
        if billing_content.find("portal_url =") > billing_content.find("portal_url"):
            issues.append("⚠️  portal_url may be used before definition")
    
    # Check for incomplete try/except blocks
    try_count = billing_content.count("try:")
    except_count = billing_content.count("except")
    if try_count != except_count:
        issues.append(f"⚠️  Mismatched try/except blocks: {try_count} try, {except_count} except")
    
    # Check for incomplete if/else blocks
    if_count = billing_content.count("if ")
    else_count = billing_content.count("else:")
    elif_count = billing_content.count("elif ")
    
    # Check for return statements
    return_count = billing_content.count("return ")
    if return_count == 0:
        issues.append("❌ No return statement found")
    
    # Check for template response
    if "TemplateResponse" not in billing_content:
        issues.append("❌ No TemplateResponse found")
    
    # Check for required template variables
    required_vars = ["subscription", "next_invoice_date", "portal_url", "invoices"]
    for var in required_vars:
        if f'"{var}":' not in billing_content and f"'{var}':" not in billing_content:
            issues.append(f"⚠️  Template variable '{var}' may not be passed to template")
    
    # Print results
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ No obvious issues detected")
    
    # Check for syntax errors by trying to parse
    try:
        ast.parse(content)
        print("✅ Syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
    
    print("\n📋 Summary:")
    print(f"  - Function length: {len(billing_content)} characters")
    print(f"  - Try blocks: {try_count}")
    print(f"  - Except blocks: {except_count}")
    print(f"  - Return statements: {return_count}")

if __name__ == "__main__":
    analyze_billing_route()
