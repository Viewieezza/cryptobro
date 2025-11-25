import requests
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timezone, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
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
    logging.error(f"Error setting up Google Sheets credentials: {e}")
    exit()

# Google Sheet ID and Worksheet name
worksheet_title = 'EdgeX Vault Trends'  # You can change this worksheet name

# Open the Google Sheet
try:
    sheet = client.open_by_key(google_sheet_id).worksheet(worksheet_title)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Error: The specified Google Sheet was not found. Check the ID and permissions.")
    exit()
except gspread.exceptions.WorksheetNotFound:
    # Create worksheet if it doesn't exist
    try:
        spreadsheet = client.open_by_key(google_sheet_id)
        sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=10)
        logging.info(f"Created new worksheet: {worksheet_title}")
    except Exception as e:
        logging.error(f"Error creating worksheet: {e}")
        exit()
except Exception as e:
    logging.error(f"An error occurred while opening the Google Sheet: {e}")
    exit()

def fetch_edgex_vault_trends(vault_id=1, trend_type="dailyReturnRate", vault_type="vault", days=30):
    """
    Fetch vault trends data from EdgeX API
    
    Args:
        vault_id: Vault ID (default: 1)
        trend_type: Type of trend data (default: dailyReturnRate)
        vault_type: Type of vault (default: vault)
        days: Number of days to fetch (default: 30)
    
    Returns:
        List of records with converted timestamps
    """
    url = "https://pro.edgex.exchange/api/v1/public/vault/vaultTrends"
    
    params = {
        "vaultId": vault_id,
        "trendtype": trend_type,
        "vaultType": vault_type,
        "days": days
    }
    
    try:
        logging.info(f"Fetching data from EdgeX API: {url}")
        logging.info(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("code") == "SUCCESS" and data.get("data", {}).get("list"):
            data_list = data["data"]["list"]
            logging.info(f"Successfully fetched {len(data_list)} records from API")
            return data_list
        else:
            logging.warning("API response does not contain expected data structure")
            return []
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def convert_to_gmt7(timestamp_ms):
    """
    Convert timestamp (milliseconds) to GMT+7 datetime string
    
    Args:
        timestamp_ms: Timestamp in milliseconds (string or int)
    
    Returns:
        Tuple of (date_string, time_string) in GMT+7
    """
    try:
        # Convert milliseconds to seconds
        timestamp_sec = int(timestamp_ms) / 1000
        
        # Create UTC datetime
        utc_dt = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        
        # Convert to GMT+7 (UTC+7)
        gmt7 = timezone(timedelta(hours=7))
        gmt7_dt = utc_dt.astimezone(gmt7)
        
        # Format as date and time strings
        date_str = gmt7_dt.strftime("%Y-%m-%d")
        time_str = gmt7_dt.strftime("%H:%M:%S")
        
        return date_str, time_str
    except Exception as e:
        logging.error(f"Error converting timestamp {timestamp_ms}: {e}")
        return "N/A", "N/A"

def setup_sheet_headers():
    """
    Set up headers in the Google Sheet if they don't exist (only update column A-D)
    """
    try:
        # Check if sheet is empty or doesn't have headers
        all_values = sheet.get_all_values()
        
        if not all_values or len(all_values) == 0:
            # Sheet is empty, add headers
            headers = ["Date (GMT+7)", "Time (GMT+7)", "Daily Return Rate", "Timestamp"]
            sheet.update(range_name="A1:D1", values=[headers])
            # Format header row (make it bold)
            sheet.format("A1:D1", {"textFormat": {"bold": True}})
            logging.info("Sheet headers set up successfully")
        elif all_values[0][:4] != ["Date (GMT+7)", "Time (GMT+7)", "Daily Return Rate", "Timestamp"]:
            # Headers are wrong, update only column A-D
            headers = ["Date (GMT+7)", "Time (GMT+7)", "Daily Return Rate", "Timestamp"]
            sheet.update(range_name="A1:D1", values=[headers])
            # Format header row (make it bold)
            sheet.format("A1:D1", {"textFormat": {"bold": True}})
            logging.info("Sheet headers updated successfully")
        else:
            logging.info("Sheet headers already exist")
    except Exception as e:
        logging.error(f"Error setting up sheet headers: {e}")

def get_existing_timestamps():
    """
    Get all existing timestamps from the Google Sheet (column D)
    Check all rows to see what data already exists
    
    Returns:
        Set of existing timestamps (as strings)
    """
    try:
        # Get all values from the sheet
        all_values = sheet.get_all_values()
        
        if len(all_values) <= 1:  # Only headers or empty
            return set()
        
        # Extract timestamps from column D (index 3), skip header row
        existing_timestamps = set()
        for row in all_values[1:]:  # Skip header row
            if len(row) > 3 and row[3] and row[3].strip():  # Check if column D exists and has value
                existing_timestamps.add(row[3].strip())
        
        logging.info(f"Found {len(existing_timestamps)} existing records in sheet")
        return existing_timestamps
        
    except Exception as e:
        logging.error(f"Error reading existing timestamps: {e}")
        return set()

def find_next_empty_row_in_column_a():
    """
    Find the first empty row by checking column A (check all rows)
    
    Returns:
        Row number (1-based) of the first empty row in column A
    """
    try:
        # Get all values from column A only
        column_a_values = sheet.col_values(1)  # Column A is index 1
        
        # Find first empty row (skip header row 1)
        for i in range(1, len(column_a_values)):
            if not column_a_values[i] or column_a_values[i].strip() == "":
                return i + 1  # Return 1-based row number
        
        # If all rows are filled, return next row
        return len(column_a_values) + 1
        
    except Exception as e:
        logging.error(f"Error finding next empty row: {e}")
        # Default to row 2 if error (row 1 is header)
        return 2

def fill_google_sheet(data_list):
    """
    Fill Google Sheet with EdgeX vault trends data
    - Check all rows to see what data already exists (by timestamp)
    - For new data, find the first empty row in column A and add it there
    - Only update columns A-D
    
    Args:
        data_list: List of records from API response
    """
    try:
        if not data_list:
            logging.warning("No data to write to sheet")
            return
        
        # Get all existing timestamps from sheet (check all rows)
        existing_timestamps = get_existing_timestamps()
        
        # Process each record from API
        new_records_count = 0
        skipped_count = 0
        
        for record in data_list:
            snapshot_time = str(record.get("snapshotTime", ""))
            amount = record.get("amount", "")
            
            # Skip if this timestamp already exists in sheet
            if snapshot_time in existing_timestamps:
                skipped_count += 1
                continue
            
            # Find the first empty row in column A
            empty_row = find_next_empty_row_in_column_a()
            
            # Convert timestamp to GMT+7
            date_str, time_str = convert_to_gmt7(snapshot_time)
            
            # Create row data: [Date, Time, Daily Return Rate, Timestamp] - only 4 columns
            row_data = [[date_str, time_str, amount, snapshot_time]]
            
            # Update only column A-D in the empty row
            range_str = f"A{empty_row}:D{empty_row}"
            sheet.update(range_name=range_str, values=row_data, value_input_option='USER_ENTERED')
            
            new_records_count += 1
            logging.info(f"Added new record to row {empty_row}: {date_str} {time_str}")
        
        # Summary
        if new_records_count > 0:
            logging.info(f"Successfully added {new_records_count} new records to Google Sheet (columns A-D only)")
        if skipped_count > 0:
            logging.info(f"Skipped {skipped_count} records that already exist in sheet")
        if new_records_count == 0 and skipped_count == 0:
            logging.warning("No rows to write")
            
    except Exception as e:
        logging.error(f"Error writing data to Google Sheet: {e}")

if __name__ == "__main__":
    logging.info("=" * 50)
    logging.info("EdgeX Vault Trends to Google Sheet")
    logging.info("=" * 50)
    
    # Fetch data from EdgeX API
    api_data = fetch_edgex_vault_trends()
    
    if api_data:
        # Setup sheet headers (if needed)
        setup_sheet_headers()
        
        # Fill sheet with data (only new records)
        fill_google_sheet(api_data)
        
        logging.info("=" * 50)
        logging.info("Process completed successfully!")
        logging.info("=" * 50)
    else:
        logging.error("Failed to fetch data from API. Process aborted.")

