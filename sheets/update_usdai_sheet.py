"""
USD.AI (USDai) → Google Sheet "USD.ai"
ดึง Current Balance (USDai + sUSDai) บน Arbitrum One แล้วเขียนข้อมูลลงแถวใหม่ คอลัมน์ A–D และ F
เขียนเฉพาะกรณีที่มี WALLET_ADDRESS_2 ตั้งไว้ใน Env เท่านั้น หากไม่มีให้ข้าม (skip)
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

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _gmt7_date():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")


def main():
    logging.info("USD.AI (USDai) → Sheet")
    
    # 1. ตรวจสอบกระเป๋าที่ 2 (ถ้าไม่มี ให้ skip ตามเงื่อนไข)
    wallet2 = os.getenv("WALLET_ADDRESS_2")
    if not wallet2 or not wallet2.strip():
        logging.info("WALLET_ADDRESS_2 is not set. Skipping USD.AI tracking as requested.")
        return

    # --- Google Sheets Setup ---
    credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if google_sheet_id:
        google_sheet_id = google_sheet_id.replace(" ", "").strip()
    if not credentials_base64 or not google_sheet_id:
        logging.error("GOOGLE_APPLICATION_CREDENTIALS และ GOOGLE_SHEET_ID ต้องตั้งใน .env")
        return

    try:
        creds_dict = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
    except Exception as e:
        logging.error("Error decoding GOOGLE_APPLICATION_CREDENTIALS: " + str(e))
        return

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    WORKSHEET_TITLE = os.getenv("USDAI_WORKSHEET_TITLE_2", "USD.ai")

    try:
        spreadsheet = client.open_by_key(google_sheet_id)
        sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
        return
    except gspread.exceptions.WorksheetNotFound:
        # หากไม่มี ให้ทำการสร้างแท็บชีตใหม่พร้อมใส่ header
        sheet = spreadsheet.add_worksheet(title=WORKSHEET_TITLE, rows=1000, cols=12)
        logging.info(f"Created worksheet: {WORKSHEET_TITLE}")
        DEFAULT_HEADERS = ['Date', 'Protocol', 'Chain', 'Asset', 'Initial Deposit', 'Current Balance', 'Incentive Received', 'Cumulative Income', 'Cumulative ROI %', 'Days Active', 'Annualized Gain %', 'Notes']
        sheet.update(range_name="A1:L1", values=[DEFAULT_HEADERS], value_input_option="USER_ENTERED")
        sheet.format("A1:L1", {"textFormat": {"bold": True}})

    # 2. ดึงข้อมูลจาก on-chain
    from defi.usdai_tracker import get_usdai_balances
    
    logging.info(f"Fetching balances for Wallet 2: {wallet2}")
    balances = get_usdai_balances(wallet2)
    if balances is None:
        logging.error("ไม่สามารถดึงยอดเงินจาก on-chain ได้")
        return

    total_usd = balances["total_usdai"]
    logging.info(f"USD.AI Balance - Wallet: ${balances['wallet_usdai']:,.2f}, Vault: ${balances['vault_usdai']:,.2f}, Total: ${total_usd:,.2f}")

    # 3. เช็คยอดวันที่วันนี้เพื่อกันซ้ำ
    try:
        col_a = sheet.col_values(1)
        existing_dates = set()
        for i, cell in enumerate(col_a):
            if i == 0 and cell and "date" in str(cell).lower():
                continue
            if cell and str(cell).strip():
                part = str(cell).strip()[:10]
                if len(part) >= 10:
                    existing_dates.add(part)
    except Exception as e:
        logging.error(f"Error reading column A: {e}")
        existing_dates = set()

    date_str = _gmt7_date()
    if date_str in existing_dates:
        logging.info(f"Date {date_str} already in sheet '{WORKSHEET_TITLE}', skip")
        return

    # 4. หาแถวว่างถัดไป
    row_num = 2
    try:
        for i in range(len(col_a)):
            if not col_a[i] or str(col_a[i]).strip() == "":
                row_num = i + 1
                break
        else:
            row_num = len(col_a) + 1
    except Exception:
        pass

    # 5. อัปเดตข้อมูลลงชีต (เขียนเฉพาะ A–D และ F)
    sheet.update(range_name=f"A{row_num}:D{row_num}", values=[[
        date_str,
        "USD.ai",
        "Arbitrum",
        "USDai",
    ]], value_input_option="USER_ENTERED")

    sheet.update(range_name=f"F{row_num}", values=[[
        round(total_usd, 2),
    ]], value_input_option="USER_ENTERED")

    logging.info(f"Appended row {row_num} to '{WORKSHEET_TITLE}': {date_str} — Current Balance ${total_usd:,.2f}")
    logging.info("Done.")


if __name__ == "__main__":
    main()
