import os
import json
import base64
import gspread
import ccxt
from datetime import datetime
import pytz
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")

if not credentials_base64 or not google_sheet_id:
    print("Environment variables GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEET_ID missing.")
    exit()

try:
    GOOGLE_APPLICATION_CREDENTIALS_json = base64.b64decode(credentials_base64).decode("utf-8")
    GOOGLE_APPLICATION_CREDENTIALS = json.loads(GOOGLE_APPLICATION_CREDENTIALS_json)
except Exception as e:
    print("Error decoding service account key:", e)
    exit()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_APPLICATION_CREDENTIALS, scope)
try:
    client = gspread.authorize(creds)
    sheet = client.open_by_key(google_sheet_id).worksheet("LLP")
except Exception as e:
    print("Error opening Google Sheet:", e)
    exit()

print("Initializing ccxt kucoin for historical data...")
exchange = ccxt.kucoin()
bkk_tz = pytz.timezone("Asia/Bangkok")

all_values = sheet.get_all_values()
print(f"Total rows found in sheet: {len(all_values)}")

cells_to_update = []

for i, row in enumerate(all_values):
    if i == 0:
        continue # skip header row
    
    # row[0] is Date
    if len(row) > 0 and row[0].strip():
        date_str = row[0].strip()
        
        try:
            # Parse the sheet's BKK time into a timestamp
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            dt = bkk_tz.localize(dt)
            ts = int(dt.timestamp() * 1000)
            
            # Fetch 1h candle around that time since
            candles = exchange.fetch_ohlcv('LIT/USDT', timeframe='1h', since=ts, limit=1)
            new_price = 0.0
            if candles and len(candles) > 0:
                new_price = candles[0][4] # close price
            else:
                print(f"Row {i+1}: No 1h candle found for ts={ts}. Trying 1d...")
                # fallback daily candle if 1h doesn't yield results
                candles = exchange.fetch_ohlcv('LIT/USDT', timeframe='1d', since=ts, limit=1)
                if candles and len(candles) > 0:
                    new_price = candles[0][4]
                else:
                    print(f"Row {i+1}: No 1d candle found either!")

            if new_price > 0:
                old_price = row[7] if len(row) > 7 else "N/A"
                print(f"Row {i+1} [{date_str}]: Old Price = {old_price} -> New Price = {new_price}")
                
                # Format for batch update: ranges vs values
                cells_to_update.append({
                    'range': f'H{i+1}', 
                    'values': [[new_price]]
                })
            else:
                print(f"Row {i+1}: Price is still 0.0")
                
        except Exception as e:
            print(f"Row {i+1}: Error processing date {date_str} (skipped): {e}")

if cells_to_update:
    print(f"\nProceeding to batch update {len(cells_to_update)} rows in the Google Sheet...")
    sheet.batch_update(cells_to_update, value_input_option="USER_ENTERED")
    print("Successfully batch updated!")
else:
    print("\nNo valid rows to update.")
