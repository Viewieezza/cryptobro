#!/usr/bin/env python3
"""
BTSE Client Usage Example

This script demonstrates how to use the BTSEClient to fetch earn/invest data.
Make sure to set your BTSE_API_KEY and BTSE_API_SECRET environment variables.
"""

import os
import json
from btse_client import BTSEClient, BTSEError, ConfigError

def main():
    """Main function to demonstrate BTSE client usage"""
    try:
        # Initialize the BTSE client
        client = BTSEClient()
        
        # Load environment variables (BTSE_API_KEY and BTSE_API_SECRET)
        client.load_environment()
        
        print("🚀 BTSE Earn/Invest Data Fetcher")
        print("=" * 50)
        
        # Fetch all earn data
        print("\n📊 Fetching all earn data...")
        all_data = client.get_all_earn_data()
        
        # Display summary
        print(f"\n📈 Summary:")
        print(f"  • Available Products: {len(all_data['products'])}")
        print(f"  • Active Positions: {len(all_data['positions'])}")
        print(f"  • History Records: {len(all_data['history'])}")
        
        # Display earn products
        if all_data['products']:
            print(f"\n💰 Available Earn Products:")
            for i, product in enumerate(all_data['products'][:5], 1):  # Show first 5
                name = product.get('name', 'Unknown')
                currency = product.get('currency', '')
                product_type = product.get('type', '')
                rates = product.get('rates', [])
                rate_info = f"Rates: {rates[0]['rate']}% for {rates[0]['days']} days" if rates else "No rates"
                print(f"  {i}. {name} ({currency}) - {product_type} - {rate_info}")
        
        # Display active positions
        if all_data['positions']:
            print(f"\n🎯 Active Positions:")
            for i, position in enumerate(all_data['positions'], 1):
                print(f"  {i}. {position.get('productName', 'Unknown')} - "
                      f"Amount: {position.get('amount', 'N/A')} "
                      f"{position.get('currency', '')}")
        
        # Display recent history
        if all_data['history']:
            print(f"\n📋 Recent History (last 3):")
            for i, record in enumerate(all_data['history'][:3], 1):
                print(f"  {i}. {record.get('type', 'Unknown')} - "
                      f"Amount: {record.get('amount', 'N/A')} "
                      f"{record.get('currency', '')} - "
                      f"Date: {record.get('timestamp', 'N/A')}")
        
        # Save data to file (optional)
        output_file = 'btse_earn_data.json'
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        print(f"\n💾 Data saved to: {output_file}")
        
        print(f"\n✅ Successfully fetched BTSE earn/invest data!")
        
    except ConfigError as e:
        print(f"❌ Configuration Error: {e}")
        print("\n💡 Make sure to set your environment variables:")
        print("   export BTSE_API_KEY='your_api_key'")
        print("   export BTSE_API_SECRET='your_api_secret'")
        
    except BTSEError as e:
        print(f"❌ BTSE API Error: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()
