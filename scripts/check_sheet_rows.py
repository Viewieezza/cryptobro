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
all_values = sheet.get_all_values()
for row in all_values[-5:]:
    print(row)
