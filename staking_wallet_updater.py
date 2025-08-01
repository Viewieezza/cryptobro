import connect_db
import binance_get
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import firebase_admin
from firebase_admin import credentials, db
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import base64
from io import StringIO
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Get the base64-encoded service account key from environment variables
credentials_base64 = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")

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
google_sheet_id = google_sheet_id
worksheet_title = 'Staking'

# Open the Google Sheet
try:
    sheet = client.open_by_key(google_sheet_id).worksheet(worksheet_title)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Error: The specified Google Sheet was not found. Check the ID and permissions.")
    exit()
except gspread.exceptions.WorksheetNotFound:
    logging.error(f"Error: The worksheet '{worksheet_title}' was not found in the Google Sheet.")
    exit()
except Exception as e:
    logging.error(f"An error occurred while opening the Google Sheet: {e}")
    exit()

# Clear the existing data in the sheet except the first row
try:
    sheet.batch_clear(["A2:G"])
    logging.info("Sheet cleared successfully except for the header.")
except Exception as e:
    logging.error(f"Error clearing the Google Sheet: {e}")
    exit()

# Get a reference to the database
ref = connect_db.db.reference('new_staking_wallet_9m')

def fetch_data_from_firebase():
    try:
        data = ref.get()
        logging.info("Data fetched from Firebase successfully.")
        return data
    except Exception as e:
        logging.error(f"Error fetching data from Firebase: {e}")
        return None

def fill_google_sheet(data):
    try:
        cell_list = sheet.range(2, 1, len(data) + 1, 7)  # Adjust range as per number of columns
        for i, (key, record) in enumerate(data.items()):
            cell_list[i * 7].value = record.get('wallet_name', '')  # Wallet
            cell_list[i * 7 + 1].value = record.get('date', '')  # Date
            cell_list[i * 7 + 2].value = record.get('time', '')  # Time
            cell_list[i * 7 + 3].value = record.get('asset', '')  # Ticker
            cell_list[i * 7 + 4].value = record.get('totalAmount', '')  # Amount of token staked
            cell_list[i * 7 + 5].value = record.get('subscription_result', '')
            if (record.get('yesterdayRealTimeRewards', '')):
                cell_list[i * 7 + 6].value = record.get('yesterdayRealTimeRewards', '')  # Placeholder for Daily ROI (USDT), can be calculated if needed
            else:
                cell_list[i * 7 + 6].value = 0

        sheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        logging.info("Data successfully written to the Google Sheet.")
    except Exception as e:
        logging.error(f"Error writing data to the Google Sheet: {e}")

if __name__ == "__main__":
    firebase_data = fetch_data_from_firebase()
    if firebase_data:
        fill_google_sheet(firebase_data)
