"""
WLFI (World Liberty Finance) → Google Sheet "Worldlib"
อัพเดตรายวัน: ดึงข้อมูลจาก on-chain (getAccountValues) แล้วเขียนหนึ่งแถวลงชีต คอลัมน์ A–G
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

# --- Google Sheets ---
credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
if not credentials_base64:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")
if not google_sheet_id:
    raise ValueError("GOOGLE_SHEET_ID is not set")

try:
    GOOGLE_APPLICATION_CREDENTIALS = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
except Exception as e:
    raise ValueError("Error decoding GOOGLE_APPLICATION_CREDENTIALS: " + str(e))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_APPLICATION_CREDENTIALS, scope)
client = gspread.authorize(creds)

WORKSHEET_TITLE = "Worldlib"
INITIAL_DEPOSIT_USD = float(os.getenv("WLFI_INITIAL_DEPOSIT_USD", "500073.4"))

# Header คอลัมน์ A–G ตามชีต "Worldlib"
DEFAULT_HEADERS = ["Date", "Protocol", "Chain", "Asset", "Initial Deposit", "Current Balance", "Incentive Received"]

try:
    spreadsheet = client.open_by_key(google_sheet_id)
    sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
    raise
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=WORKSHEET_TITLE, rows=1000, cols=10)
    logging.info(f"Created worksheet: {WORKSHEET_TITLE}")


def _gmt7_now():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def ensure_headers():
    """ตรวจ/ตั้งค่า header แถว 1 คอลัมน์ A–G"""
    try:
        row1 = sheet.row_values(1)
        if len(row1) < 7 or not any(str(c).strip() for c in row1[:7]):
            sheet.update(range_name="A1:G1", values=[DEFAULT_HEADERS], value_input_option="USER_ENTERED")
            sheet.format("A1:G1", {"textFormat": {"bold": True}})
            logging.info(f"Set header row: {DEFAULT_HEADERS}")
        else:
            headers = [str(row1[i]).strip() if i < len(row1) else "" for i in range(7)]
            logging.info(f"Existing header A–G: {headers}")
    except Exception as e:
        logging.error(f"Error ensuring headers: {e}")


def get_existing_dates():
    """เซตของวันที่ (YYYY-MM-DD) ในคอลัมน์ A"""
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
        logging.info(f"Found {len(existing)} date(s) in sheet")
        return existing
    except Exception as e:
        logging.error(f"Error reading column A: {e}")
        return set()


def get_wlfi_stats():
    """ดึง Account Values จาก on-chain แล้วคำนวณ stats"""
    from defi.wlfi_account_values import get_account_values

    values = get_account_values()
    if values is None:
        logging.error("ไม่สามารถดึง on-chain account values ได้")
        return None

    current_usd = values["supply_value_usd"]
    initial_usd = INITIAL_DEPOSIT_USD
    total_profit = current_usd - initial_usd

    return {
        "initial_usd": initial_usd,
        "current_usd": current_usd,
        "total_profit_usd": total_profit,
        "chain": "ethereum",
    }


def find_next_row():
    """แถวว่างแถวแรกในคอลัมน์ A (1-based)"""
    try:
        col_a = sheet.col_values(1)
        for i in range(len(col_a)):
            if not col_a[i] or str(col_a[i]).strip() == "":
                return i + 1
        return len(col_a) + 1
    except Exception as e:
        logging.error(f"Error finding next row: {e}")
        return 2


def append_row(stats):
    """เพิ่มหนึ่งแถว A–G ถ้าวันที่วันนี้ยังไม่มี"""
    try:
        date_str = _gmt7_now().strftime("%Y-%m-%d")
        existing = get_existing_dates()
        if date_str in existing:
            logging.info(f"Date {date_str} already in sheet, skip")
            return
        row_num = find_next_row()
        # A–D: Date, Protocol, Chain, Asset
        sheet.update(range_name=f"A{row_num}:D{row_num}", values=[[
            date_str,
            "WLFI",
            stats.get("chain", "ethereum"),
            "USD1",
        ]], value_input_option="USER_ENTERED")
        # F: Current Balance (ข้าม E และ G)
        sheet.update(range_name=f"F{row_num}", values=[[
            round(stats["current_usd"], 2),
        ]], value_input_option="USER_ENTERED")
        logging.info(f"Appended row {row_num}: {date_str} — Current Balance ${stats['current_usd']:,.2f}")
    except Exception as e:
        logging.error(f"Error appending row: {e}")


if __name__ == "__main__":
    logging.info("WLFI → Worldlib sheet (A–G) [on-chain]")
    ensure_headers()
    stats = get_wlfi_stats()
    if stats:
        append_row(stats)
        logging.info("Done.")
    else:
        logging.error("No WLFI data to write.")
