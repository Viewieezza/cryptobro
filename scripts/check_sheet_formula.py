import os, json, base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()
credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
cred_json = base64.b64decode(credentials_base64).decode("utf-8")
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(cred_json), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open_by_key(google_sheet_id).worksheet("LLP")

# Get formulas instead of values
all_formulas = sheet.get_all_values(value_render_option='FORMULA')
if len(all_formulas) > 1:
    last_row = all_formulas[-1]
    print("Formulas in the last row:")
    for i, col in enumerate(last_row):
        # Convert index to column letter
        letter = chr(65 + i) if i < 26 else chr(64 + i // 26) + chr(65 + i % 26)
        print(f"{letter}: {col}")
