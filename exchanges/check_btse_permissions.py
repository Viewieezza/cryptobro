#!/usr/bin/env python3
"""
BTSE API Permissions Checker

This script checks what endpoints your BTSE API key has access to
and provides guidance on how to enable access to earn positions.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from exchanges.btse_client import BTSEClient, BTSEError, ConfigError

def main():
    """Check API permissions and provide guidance"""
    try:
        # Initialize the BTSE client
        client = BTSEClient()
        client.load_environment()
        
        print("🔍 BTSE API Permissions Checker")
        print("=" * 50)
        
        # Check permissions
        print("\n📋 Checking API key permissions...")
        permissions = client.check_api_permissions()
        
        print("\n📊 Permission Summary:")
        print("-" * 30)
        for endpoint, has_access in permissions.items():
            status = "✅ ALLOWED" if has_access else "❌ RESTRICTED"
            print(f"  {endpoint.upper()}: {status}")
        
        # Provide guidance based on results
        print("\n💡 Guidance:")
        print("-" * 20)
        
        if not permissions['positions']:
            print("❌ Your API key cannot access earn positions.")
            print("\n🔧 To fix this:")
            print("1. Log into your BTSE account")
            print("2. Go to Account → API Management")
            print("3. Edit your API key permissions")
            print("4. Enable 'Read' permission for 'Investment' or 'Earn' features")
            print("5. Save the changes")
            print("6. Wait a few minutes for changes to take effect")
            print("\n📝 Required permissions:")
            print("   - Investment Orders (Read)")
            print("   - Investment History (Read)")
            print("   - Account Balance (Read)")
        
        if permissions['products']:
            print("\n✅ Your API key can access earn products (public data)")
        
        # Try to fetch positions anyway to show the exact error
        print("\n🔍 Testing positions endpoint...")
        try:
            positions = client.get_earn_positions()
            if positions:
                print(f"✅ Found {len(positions)} positions!")
                for i, pos in enumerate(positions[:3], 1):
                    print(f"  {i}. {pos}")
            else:
                print("ℹ️  No positions found (empty array returned)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("Check complete!")
        
    except ConfigError as e:
        print(f"❌ Configuration Error: {e}")
        print("\n💡 Make sure to set your environment variables:")
        print("   export BTSE_API_KEY='your_api_key'")
        print("   export BTSE_API_SECRET='your_api_secret'")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()
