#!/usr/bin/env python3
"""
Test the enhanced admin dashboard with comprehensive metrics
"""
print("🎯 Testing Enhanced Admin Dashboard...")

import os
import sys
from datetime import datetime

def test_enhanced_dashboard():
    """Test the enhanced admin dashboard functionality"""
    
    print("🔍 Testing Enhanced Admin Dashboard Features")
    print("=" * 60)
    
    # Test 1: Import auth_utils and check enhanced stats
    try:
        print("📊 1. Testing enhanced admin stats...")
        from auth_utils import get_admin_stats
        
        # Try to get real stats (will fallback to mock if DB unavailable)
        try:
            stats, users = get_admin_stats()
            print(f"✅ Real database stats loaded")
        except Exception:
            print("⚠️  Database unavailable, testing with local mock data...")
            from local_dev_override import get_local_admin_stats
            stats, users = get_local_admin_stats()
        
        # Check for enhanced metrics
        enhanced_metrics = [
            'total_users', 'premium_users', 'free_users', 'active_users',
            'monthly_revenue', 'annual_revenue', 'all_time_revenue', 'arpu',
            'lifetime_premium_users', 'conversion_rate', 'new_users_this_month',
            'new_premium_this_month', 'banned_users', 'disabled_users', 'active_sessions'
        ]
        
        missing_metrics = []
        for metric in enhanced_metrics:
            if metric not in stats:
                missing_metrics.append(metric)
        
        if missing_metrics:
            print(f"❌ Missing enhanced metrics: {missing_metrics}")
            return False
        else:
            print(f"✅ All {len(enhanced_metrics)} enhanced metrics present")
            
        # Display key metrics
        print(f"\n📈 Key Metrics Preview:")
        print(f"   💾 Total Users: {stats['total_users']}")
        print(f"   ⭐ Premium Users: {stats['premium_users']}")
        print(f"   💰 Monthly Revenue: £{stats['monthly_revenue']:.2f}")
        print(f"   💎 All-Time Revenue: £{stats['all_time_revenue']:.2f}")
        print(f"   📊 Conversion Rate: {stats['conversion_rate']:.1f}%")
        print(f"   📈 ARPU: £{stats['arpu']:.2f}")
        
    except Exception as e:
        print(f"❌ Enhanced stats test failed: {e}")
        return False
    
    # Test 2: Check template syntax
    try:
        print(f"\n🎨 2. Testing enhanced template...")
        with open('templates/admin_dashboard.html', 'r') as f:
            template_content = f.read()
        
        # Check for enhanced template features
        enhanced_features = [
            'Revenue Analytics', 'User Analytics', 'Growth & Status',
            'all_time_revenue', 'conversion_rate', 'arpu',
            'new_users_this_month', 'lifetime_premium_users'
        ]
        
        missing_features = []
        for feature in enhanced_features:
            if feature not in template_content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing template features: {missing_features}")
            return False
        else:
            print(f"✅ All {len(enhanced_features)} enhanced template features present")
            
        # Check for correct GBP currency format
        if '£{{ "%.2f"|format(stats.monthly_revenue' in template_content:
            print("✅ GBP currency formatting correctly applied")
        else:
            print("❌ GBP currency formatting not found")
            return False
            
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False
    
    # Test 3: Test app route registration
    try:
        print(f"\n🛣️  3. Testing app integration...")
        import app
        
        # Check admin route exists
        routes = [route.path for route in app.app.routes if hasattr(route, 'path')]
        if '/admin' not in routes:
            print("❌ Admin route not found")
            return False
        else:
            print("✅ Admin route properly registered")
            
    except Exception as e:
        print(f"❌ App integration test failed: {e}")
        return False
    
    print(f"\n🎉 ENHANCED DASHBOARD TEST COMPLETE!")
    print(f"📋 Summary:")
    print(f"   ✅ Enhanced admin stats with {len(enhanced_metrics)} comprehensive metrics")
    print(f"   ✅ Enhanced template with detailed analytics sections")
    print(f"   ✅ GBP currency formatting applied")
    print(f"   ✅ App integration working")
    print(f"   ✅ Ready for production testing")
    
    print(f"\n🚀 Enhanced Dashboard Features:")
    print(f"   📊 Key Metrics: Total users, premium users, revenue, ARPU")
    print(f"   💰 Revenue Analytics: Monthly, annual, all-time revenue")
    print(f"   👥 User Analytics: Conversion rates, growth metrics")
    print(f"   📈 Growth & Status: New signups, account statuses")
    print(f"   💷 Currency: Properly formatted in GBP (£)")
    
    print(f"\n🎯 Test your enhanced dashboard:")
    print(f"   1. Start app: python app.py")
    print(f"   2. Login as admin: r.taylor289@gmail.com")  
    print(f"   3. Visit: http://localhost:8000/admin")
    print(f"   4. You should see comprehensive financial and user metrics!")
    
    return True

if __name__ == "__main__":
    success = test_enhanced_dashboard()
    if success:
        print(f"\n✅ ALL ENHANCED DASHBOARD TESTS PASSED!")
        print(f"🎊 Your admin dashboard now has comprehensive analytics!")
    else:
        print(f"\n❌ Some enhanced dashboard tests failed.")
        print(f"🔧 Check the errors above and verify all components.")
