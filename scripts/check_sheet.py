import os
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")

if not credentials_base64 or not google_sheet_id:
    print("Environment variables missing.")
    exit()

try:
    GOOGLE_APPLICATION_CREDENTIALS_json = base64.b64decode(credentials_base64).decode("utf-8")
    GOOGLE_APPLICATION_CREDENTIALS = json.loads(GOOGLE_APPLICATION_CREDENTIALS_json)
except Exception as e:
    print("Error decoding or parsing service account key:", e)
    exit()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_APPLICATION_CREDENTIALS, scope)
try:
    client = gspread.authorize(creds)
    sheet = client.open_by_key(google_sheet_id).worksheet("LLP")
except Exception as e:
    print("Error opening Google Sheet:", e)
    exit()

all_values = sheet.get_all_values()
print(f"Total rows found: {len(all_values)}")
print("-" * 50)

for i, row in enumerate(all_values):
    if i == 0:
        continue # skip header
    if len(row) > 0:
        date_str = row[0]
        lit_price = row[7] if len(row) > 7 else "N/A"
        print(f"Row {i+1}: Date = {date_str:20s} | LIT Price = {lit_price}")
