import connect_db
import binance_get
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, db
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

API_KEY1 = os.getenv("API_KEY1")
API_SECRET1 = os.getenv("API_SECRET1")
API_KEY2 = os.getenv("API_KEY2")
API_SECRET2 = os.getenv("API_SECRET2")
API_KEY3 = os.getenv("API_KEY3")
API_SECRET3 = os.getenv("API_SECRET3")
API_KEY4 = os.getenv("API_KEY4")
API_SECRET4 = os.getenv("API_SECRET4")
API_KEY5 = os.getenv("API_KEY5")
API_SECRET5 = os.getenv("API_SECRET5")

# Get a reference to the database
ref = connect_db.db.reference('new_staking_wallet_9m')

def convert_timestamp_to_gmt_plus_7(timestamp):
    if isinstance(timestamp, int):
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    else:
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    dt_gmt_plus_7 = dt + timedelta(hours=7)
    return dt_gmt_plus_7.strftime('%Y-%m-%d %H:%M:%S')

def push_combined_data_to_firebase(api_key, api_secret,wallet_name):
    # Fetch flexible position data
    flexible_position = binance_get.get_flexible_position(api_key, api_secret)
    
    # Fetch subscription and redemption records
    now = datetime.now(timezone.utc)
    now_gmt_plus_7 = now + timedelta(hours=7)
    current_date_utc = now.strftime('%Y-%m-%d')
    current_timestamp = int(time.time() * 1000)
    start_time = current_timestamp - 86400000 + 1
    end_time = current_timestamp  # End of the current day in milliseconds

    subscription_records = binance_get.get_flexible_subscription_record(api_key, api_secret, start_time=start_time, end_time=end_time)
    redemption_records = binance_get.get_flexible_redemption_record(api_key, api_secret, start_time=start_time, end_time=end_time)
    
    combined_data = {}

    # Prepare flexible position data
    if 'rows' in flexible_position and flexible_position['rows']:
        now = datetime.now(timezone.utc)
        now_gmt_plus_7 = convert_timestamp_to_gmt_plus_7(int(now.timestamp() * 1000))
        date_gmt_plus_7, time_gmt_plus_7 = now_gmt_plus_7.split(' ')
        
        combined_data.update({
            'wallet_name': wallet_name,
            'totalAmount': flexible_position['rows'][0]['totalAmount'],
            'latestAnnualPercentageRate': flexible_position['rows'][0]['latestAnnualPercentageRate'],
            'asset': flexible_position['rows'][0]['asset'],
            'canRedeem': flexible_position['rows'][0]['canRedeem'],
            'collateralAmount': flexible_position['rows'][0]['collateralAmount'],
            'productId': flexible_position['rows'][0]['productId'],
            'yesterdayRealTimeRewards': flexible_position['rows'][0]['yesterdayRealTimeRewards'],
            'cumulativeBonusRewards': flexible_position['rows'][0]['cumulativeBonusRewards'],
            'cumulativeRealTimeRewards': flexible_position['rows'][0]['cumulativeRealTimeRewards'],
            'cumulativeTotalRewards': flexible_position['rows'][0]['cumulativeTotalRewards'],
            'autoSubscribe': flexible_position['rows'][0]['autoSubscribe'],
            'date': date_gmt_plus_7,
            'time': time_gmt_plus_7,
            'timestamp': int(now.timestamp() * 1000)  # Real timestamp in milliseconds
        })
    else:
        now = datetime.now(timezone.utc)
        now_gmt_plus_7 = convert_timestamp_to_gmt_plus_7(int(now.timestamp() * 1000))
        date_gmt_plus_7, time_gmt_plus_7 = now_gmt_plus_7.split(' ')
        combined_data.update({
            'totalAmount': 0,
            'date': date_gmt_plus_7,
            'time': time_gmt_plus_7,
            'timestamp': int(now.timestamp() * 1000)  # Real timestamp in milliseconds
        })

    # Calculate subscription and redemption totals
    subscription_total = sum(float(record['amount']) for record in subscription_records['rows']) if 'rows' in subscription_records else 0
    redemption_total = sum(float(record['amount']) for record in redemption_records['rows']) if 'rows' in redemption_records else 0

    # Add subscription records data
    if 'rows' in subscription_records and subscription_records['rows']:
        combined_data['subscription_records'] = subscription_records['rows']

    # Add redemption records data
    if 'rows' in redemption_records and redemption_records['rows']:
        combined_data['redemption_records'] = redemption_records['rows']

    # Calculate subscription_result
    combined_data['subscription_result'] = subscription_total - redemption_total
 

    # Push combined data to Firebase
    total_amount = float(combined_data.get('totalAmount', 0))  # Convert totalAmount to float
    if combined_data and (total_amount > 0 or combined_data['subscription_result'] != 0):
        ref.push(combined_data)
        logging.info("Combined data pushed to Firebase.")
    else:
        logging.error("No data available to push to Firebase.")

if __name__ == "__main__":
    push_combined_data_to_firebase(API_KEY1, API_SECRET1, 'wallet1')
    push_combined_data_to_firebase(API_KEY2, API_SECRET2, 'wallet2')
    push_combined_data_to_firebase(API_KEY3, API_SECRET3, 'wallet3')
    push_combined_data_to_firebase(API_KEY4, API_SECRET4, 'wallet4')
    push_combined_data_to_firebase(API_KEY5, API_SECRET5, 'wallet5')
