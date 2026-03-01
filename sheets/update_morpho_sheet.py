"""
Morpho → Google Sheet "Morpho"
ดึง Current Balance จาก on-chain (ทุก vault รวมกัน) แล้วเขียนเฉพาะ A–D และ F
ไม่แตะ E, G–K
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import base64
import logging
from datetime import datetime, timezone, timedelta

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
if not credentials_base64 or not google_sheet_id:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS และ GOOGLE_SHEET_ID ต้องตั้งใน .env")

try:
    creds_dict = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
except Exception as e:
    raise ValueError("Error decoding GOOGLE_APPLICATION_CREDENTIALS: " + str(e))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

WORKSHEET_TITLE = "Morpho"

try:
    spreadsheet = client.open_by_key(google_sheet_id)
    sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
    raise
except gspread.exceptions.WorksheetNotFound:
    logging.error(f"Worksheet '{WORKSHEET_TITLE}' not found.")
    raise


def _gmt7_date():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")


def get_existing_dates():
    try:
        col_a = sheet.col_values(1)
        existing = set()
        for i, cell in enumerate(col_a):
            if i == 0 and cell and "date" in str(cell).lower():
                continue
            if cell and str(cell).strip():
                part = str(cell).strip()[:10]
                if len(part) >= 10:
                    existing.add(part)
        return existing
    except Exception as e:
        logging.error(f"Error reading column A: {e}")
        return set()


def find_next_row():
    try:
        col_a = sheet.col_values(1)
        for i in range(len(col_a)):
            if not col_a[i] or str(col_a[i]).strip() == "":
                return i + 1
        return len(col_a) + 1
    except Exception as e:
        logging.error(f"Error finding next row: {e}")
        return 2


def append_row(current_balance: float):
    """เขียนเฉพาะ A–D และ F ไม่แตะ E, G–K"""
    date_str = _gmt7_date()
    existing = get_existing_dates()
    if date_str in existing:
        logging.info(f"Date {date_str} already in sheet, skip")
        return
    row_num = find_next_row()
    sheet.update(range_name=f"A{row_num}:D{row_num}", values=[[date_str, "Morpho", "Ethereum", "USDT"]], value_input_option="USER_ENTERED")
    sheet.update(range_name=f"F{row_num}", values=[[round(current_balance, 2)]], value_input_option="USER_ENTERED")
    logging.info(f"Appended row {row_num}: {date_str} — Current Balance ${current_balance:,.2f}")


if __name__ == "__main__":
    from defi.morpho_balance import get_all_balances

    logging.info("Morpho → Sheet [on-chain, all vaults]")
    data = get_all_balances()
    if data and data["total_usd"] > 0:
        for v in data["vaults"]:
            if v["assets"] > 0:
                logging.info(f"  {v['name']}: ${v['assets']:,.2f} {v['asset_symbol']}")
        append_row(data["total_usd"])
        logging.info("Done.")
    else:
        logging.error("ไม่สามารถดึง Current Balance ได้ หรือ balance = 0")
