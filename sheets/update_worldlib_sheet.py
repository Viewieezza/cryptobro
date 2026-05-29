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
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
    raise


def _gmt7_now():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def ensure_headers(sheet):
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


def get_existing_dates(sheet):
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


def get_wlfi_stats(wallet_address, initial_deposit_usd):
    """ดึง Account Values จาก on-chain แล้วคำนวณ stats"""
    from defi.wlfi_account_values import get_account_values

    values = get_account_values(wallet_address)
    if values is None:
        logging.error(f"ไม่สามารถดึง on-chain account values ได้ สำหรับ wallet: {wallet_address}")
        return None

    current_usd = values["supply_value_usd"]
    total_profit = current_usd - initial_deposit_usd

    return {
        "initial_usd": initial_deposit_usd,
        "current_usd": current_usd,
        "total_profit_usd": total_profit,
        "chain": "ethereum",
    }


def find_next_row(sheet):
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


def append_row(sheet, stats):
    """เพิ่มหนึ่งแถว A–G ถ้าวันที่วันนี้ยังไม่มี"""
    try:
        date_str = _gmt7_now().strftime("%Y-%m-%d")
        existing = get_existing_dates(sheet)
        if date_str in existing:
            logging.info(f"Date {date_str} already in sheet, skip")
            return
        row_num = find_next_row(sheet)
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


def update_wallet_to_sheet(wallet_address, worksheet_title, initial_deposit_usd):
    logging.info("=" * 60)
    logging.info(f"Processing wallet: {wallet_address}")
    logging.info(f"Worksheet title  : {worksheet_title}")
    logging.info(f"Initial deposit  : ${initial_deposit_usd:,.2f}")
    logging.info("=" * 60)
    try:
        try:
            sheet = spreadsheet.worksheet(worksheet_title)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=10)
            logging.info(f"Created worksheet: {worksheet_title}")

        ensure_headers(sheet)
        stats = get_wlfi_stats(wallet_address, initial_deposit_usd)
        if stats:
            append_row(sheet, stats)
            logging.info(f"Finished updating '{worksheet_title}' successfully.")
        else:
            logging.error(f"No stats fetched for wallet '{wallet_address}'.")
    except Exception as e:
        logging.error(f"Error updating wallet '{wallet_address}' to worksheet '{worksheet_title}': {e}")


if __name__ == "__main__":
    logging.info("WLFI → Worldlib sheet (A–G) [on-chain]")
    
    # Wallet 1
    wallet1 = os.getenv("WALLET_ADDRESS", "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7")
    worksheet1 = os.getenv("WLFI_WORKSHEET_TITLE_1", "Worldlib")
    initial_deposit1 = float(os.getenv("WLFI_INITIAL_DEPOSIT_USD", "500073.4"))
    
    update_wallet_to_sheet(wallet1, worksheet1, initial_deposit1)
    
    # Wallet 2
    wallet2 = os.getenv("WALLET_ADDRESS_2")
    if wallet2 and wallet2.strip():
        worksheet2 = os.getenv("WLFI_WORKSHEET_TITLE_2", "Worldlib_2.2")
        raw_deposit2 = os.getenv("WLFI_INITIAL_DEPOSIT_USD_2")
        initial_deposit2 = 0.0
        if raw_deposit2:
            try:
                initial_deposit2 = float(raw_deposit2)
            except ValueError:
                logging.warning(f"Invalid WLFI_INITIAL_DEPOSIT_USD_2: {raw_deposit2}, using 0.0")
        
        update_wallet_to_sheet(wallet2, worksheet2, initial_deposit2)
    else:
        logging.info("WALLET_ADDRESS_2 is not set. Skipping second wallet update.")
        
    logging.info("Done.")
