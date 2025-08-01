import connect_db
import binance_get
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from firebase_admin import db

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
ref = connect_db.db.reference('new_deposit_withdraw_history_9m')

def get_transaction_history(api_key, api_secret):
    try:
        # Check if API credentials are properly set
        if not api_key or not api_secret:
            logging.warning(f"API credentials are not properly set. API_KEY: {bool(api_key)}, API_SECRET: {bool(api_secret)}")
            return [], []
        
        deposit_history = binance_get.get_deposit_history(api_key, api_secret)
        withdraw_history = binance_get.get_withdraw_history(api_key, api_secret)
        return deposit_history, withdraw_history
    except Exception as e:
        logging.error(f"Error fetching transaction history: {e}")
        return [], []

def fetch_existing_transactions():
    try:
        return ref.get() or {}
    except Exception as e:
        logging.error(f"Error fetching existing transactions: {e}")
        return {}

def transaction_exists(transaction_id, transaction_type, existing_transactions):
    return any(value['id'] == transaction_id and value['type'] == transaction_type for value in existing_transactions.values())

def convert_timestamp_to_gmt_plus_7(timestamp):
    if isinstance(timestamp, int):
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    else:
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    dt_gmt_plus_7 = dt + timedelta(hours=7)
    return dt_gmt_plus_7.strftime('%Y-%m-%d %H:%M:%S')

def ensure_timestamp_format(timestamp):
    if isinstance(timestamp, int):
        return timestamp
    try:
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        logging.error(f"Invalid timestamp format: {timestamp}")
        return None

def get_transaction_price(coin_symbol, timestamp):
    if timestamp is None:
        return None
    price_data = binance_get.get_historical_price(coin_symbol, timestamp)
    return '1' if coin_symbol == 'USDTUSDT' else price_data.get('p')

def push_transaction_to_firebase(transaction_data):
    try:
        ref.push(transaction_data)
        logging.info(f"{transaction_data['type'].capitalize()} transaction {transaction_data['id']} pushed successfully.")
    except Exception as e:
        logging.error(f"Error pushing {transaction_data['type']} transaction {transaction_data['id']}: {e}")

def process_transactions(transactions, transaction_type, wallet, existing_transactions):
    for transaction in transactions:
        if transaction_exists(transaction['id'], transaction_type, existing_transactions):
            logging.info(f"{transaction_type.capitalize()} transaction {transaction['id']} already exists. Skipping.")
            continue

        time_key = 'insertTime' if transaction_type == 'deposit' else 'applyTime'
        timestamp = ensure_timestamp_format(transaction.get(time_key))
        if timestamp is None:
            logging.error(f"Transaction {transaction['id']} has invalid {time_key}. Skipping.")
            continue

        apply_time = convert_timestamp_to_gmt_plus_7(timestamp)
        coin_symbol = transaction['coin'] + 'USDT'
        price = get_transaction_price(coin_symbol, timestamp)

        transaction_data = {
            'wallet': wallet,
            'type': transaction_type,
            'id': transaction['id'],
            'amount': transaction['amount'],
            'coin': transaction['coin'],
            'status': transaction['status'],
            'address': transaction['address'],
            'txId': transaction['txId'],
            'applyTime': apply_time,
            'network': transaction['network'],
            'transferType': transaction['transferType'],
            'confirmTimes': transaction.get('confirmTimes', 'N/A'),
            'walletType': transaction['walletType'],
            'price': price
        }
        
        if transaction_type == 'withdrawal':
            transaction_data.update({
                'transactionFee': transaction['transactionFee'],
                'withdrawOrderId': transaction.get('withdrawOrderId', ''),
                'confirmNo': transaction.get('confirmNo', 0),
                'txKey': transaction.get('txKey', ''),
                'completeTime': convert_timestamp_to_gmt_plus_7(transaction['completeTime'])
            })
        
        push_transaction_to_firebase(transaction_data)

def main():
    existing_transactions = fetch_existing_transactions()

    # Check which API credentials are properly set
    wallets = [
        ('wallet1', API_KEY1, API_SECRET1),
        ('wallet2', API_KEY2, API_SECRET2),
        ('wallet3', API_KEY3, API_SECRET3),
        ('wallet4', API_KEY4, API_SECRET4),
        ('wallet5', API_KEY5, API_SECRET5)
    ]
    
    for wallet_name, api_key, api_secret in wallets:
        if not api_key or not api_secret:
            logging.warning(f"Skipping {wallet_name} - API credentials not properly set")
            continue
            
        logging.info(f"Processing {wallet_name}...")
        deposit_history, withdraw_history = get_transaction_history(api_key, api_secret)
        process_transactions(deposit_history, 'deposit', wallet_name, existing_transactions)
        process_transactions(withdraw_history, 'withdrawal', wallet_name, existing_transactions)

    logging.info("Deposit and withdrawal transactions have been pushed to Firebase.")

if __name__ == "__main__":
    main()
