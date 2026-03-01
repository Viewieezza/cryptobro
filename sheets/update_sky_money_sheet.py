"""
Sky Money (stUSDT) → Google Sheet "Sky Money"
ดึง Current Balance จาก contract stUSDT (balanceOf → previewRedeem) แล้วเขียนหนึ่งแถวลงชีต
ไม่ใส่: Initial Stake, Days Active, Annualized Gain, Cumulative Income, Cumulative ROI %
"""
import os
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
if not credentials_base64 or not google_sheet_id:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS และ GOOGLE_SHEET_ID ต้องตั้งใน .env")

try:
    creds_dict = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
except Exception as e:
    raise ValueError("Error decoding GOOGLE_APPLICATION_CREDENTIALS: " + str(e))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

WORKSHEET_TITLE = "Sky Money"

try:
    spreadsheet = client.open_by_key(google_sheet_id)
    sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
    raise
except gspread.exceptions.WorksheetNotFound:
    logging.error(f"Worksheet '{WORKSHEET_TITLE}' not found.")
    raise

# --- stUSDT contract ---
WALLET = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
STUSDT_CONTRACT = "0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9"
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
DECIMALS = 18
RPC_TIMEOUT = 15


def _gmt7_date():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")


def get_stusdt_current_balance():
    """ดึง Current Balance (previewRedeem(balanceOf)) จาก stUSDT contract. คืนค่า float หรือ None."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            logging.warning("เชื่อม RPC ไม่ได้")
            return None
        wallet = Web3.to_checksum_address(WALLET)
        contract_addr = Web3.to_checksum_address(STUSDT_CONTRACT)
        abi = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "shares", "type": "uint256"}], "name": "previewRedeem", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        c = w3.eth.contract(address=contract_addr, abi=abi)
        balance_raw = c.functions.balanceOf(wallet).call()
        assets_raw = c.functions.previewRedeem(balance_raw).call()
        return assets_raw / (10 ** DECIMALS)
    except Exception as e:
        logging.error(f"get_stusdt_current_balance: {e}")
        return None


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
        return existing
    except Exception as e:
        logging.error(f"Error reading column A: {e}")
        return set()


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


def append_row(current_balance: float):
    """เพิ่มเฉพาะคอลัมน์ A–D และ F (ไม่แตะ E, G–K เพื่อไม่ให้ clear column อื่น)"""
    date_str = _gmt7_date()
    existing = get_existing_dates()
    if date_str in existing:
        logging.info(f"Date {date_str} already in sheet, skip")
        return
    row_num = find_next_row()
    # เขียนเฉพาะ A: Date, B: Protocol, C: Chain, D: Asset, F: Current Balance — ไม่เขียน E, G–K
    sheet.update(range_name=f"A{row_num}:D{row_num}", values=[[date_str, "Sky Money", "Ethereum", "USDT"]], value_input_option="USER_ENTERED")
    sheet.update(range_name=f"F{row_num}", values=[[round(current_balance, 2)]], value_input_option="USER_ENTERED")
    logging.info(f"Appended row {row_num}: {date_str} — Current Balance {current_balance:,.2f}")


if __name__ == "__main__":
    logging.info("Sky Money (stUSDT) → Sheet")
    balance = get_stusdt_current_balance()
    if balance is not None:
        append_row(balance)
        logging.info("Done.")
    else:
        logging.error("ไม่สามารถดึง Current Balance ได้")
