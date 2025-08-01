import os
from dotenv import load_dotenv
import connect_db
import gspread
import binance_get
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

import base64
from io import StringIO
import json

# Load environment variables from .env file
load_dotenv()

# Get the base64-encoded service account key from environment variables
credentials_base64 = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if credentials_base64 is None:
    raise ValueError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set")

# Decode the base64 string to JSON
try:
    GOOGLE_APPLICATION_CREDENTIALS_json = base64.b64decode(credentials_base64).decode('utf-8')
    GOOGLE_APPLICATION_CREDENTIALS = json.loads(GOOGLE_APPLICATION_CREDENTIALS_json)
except Exception as e:
    raise ValueError("Error decoding or parsing service account key: " + str(e))

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_APPLICATION_CREDENTIALS, scope)
    client = gspread.authorize(creds)
except Exception as e:
    print(f"Error setting up Google Sheets credentials: {e}")
    exit()

# Google Sheet ID
google_sheet_id = os.getenv('GOOGLE_SHEET_ID')
worksheet_title = 'Deposit & Withdrawal'

# Open the Google Sheet
try:
    sheet = client.open_by_key(google_sheet_id).worksheet(worksheet_title)
except gspread.exceptions.SpreadsheetNotFound:
    print("Error: The specified Google Sheet was not found. Check the ID and permissions.")
    exit()
except gspread.exceptions.WorksheetNotFound:
    print(f"Error: The worksheet '{worksheet_title}' was not found in the Google Sheet.")
    exit()
except Exception as e:
    print(f"An error occurred while opening the Google Sheet: {e}")
    exit()

# Clear the existing data in the sheet except the first row
try:
    sheet.batch_clear(["A2:M"])
    print("Sheet cleared successfully except for the header.")
except Exception as e:
    print(f"Error clearing the Google Sheet: {e}")
    exit()

# Get a reference to the database
ref = connect_db.db.reference('new_deposit_withdraw_history_9m')

# Fetch transactions from Firebase
try:
    transactions = ref.get() or {}
except Exception as e:
    print(f"Error fetching transactions from Firebase: {e}")
    transactions = {}

# Prepare data for Google Sheet
rows = []
for key, transaction in transactions.items():
    date, time = transaction['applyTime'].split(' ')

    try:
        price_data = transaction['price']
        if isinstance(price_data, dict):
            price = float(price_data.get('price', 1))
        else:
            price = float(price_data)
        amount_usdt = float(transaction['amount']) * price
    except Exception as e:
        print(f"Error calculating amount in USDT for transaction {transaction['id']}: {e}")
        amount_usdt = ''

    # Determine transaction type and set 'from' and 'to' columns
    if transaction['type'] == 'deposit':
        transaction_type = "Deposit"
    else:
        transaction_type = "Withdrawal"
        
    row = [
        transaction['wallet'],
        transaction['id'],  # Add id column
        transaction['coin'],
        date,
        time,
        transaction_type,  # Updated transaction type
        float(transaction['amount']),
        price,
        amount_usdt,  # Amount (USDT) - Conversion logic added
        transaction['network'],
        transaction.get('transactionFee', '-'),
        transaction.get('address', '-'),
        transaction['txId']
    ]
    rows.append(row)

# # Sort rows by date and time in descending order (newest to oldest)
# rows.sort(key=lambda x: datetime.strptime(f"{x[3]} {x[4]}", '%Y-%m-%d %H:%M:%S'), reverse=True)

# Sort rows by date and time in ascending order (oldest to newest)
rows.sort(key=lambda x: datetime.strptime(f"{x[3]} {x[4]}", '%Y-%m-%d %H:%M:%S'))


# Check if column A is empty and fill data if empty
try:
    column_a = sheet.col_values(1)[1:]  # Skip header
    if not any(column_a):
        sheet.update('A2:M', rows, value_input_option='USER_ENTERED')
        print("Data successfully written to the Google Sheet.")
    else:
        print("Column A is not empty. Data not written to the Google Sheet.")
except Exception as e:
    print(f"Error checking or updating the Google Sheet: {e}")

# Set number format for 'Amount' and 'Amount (USDT)' columns
try:
    sheet.format('G2:H', {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'}})
    print("Number format for 'Amount' and 'Amount (USDT)' columns set successfully.")
except Exception as e:
    print(f"Error setting number format: {e}")
