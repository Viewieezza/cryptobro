"""
GS → Google Sheet worksheet "nvodyo8iy"
ดึง Current Balance จาก stUSDS (USDS ใน wallet + vault convertToAssets) แล้วเขียนหนึ่งแถวลงชีต
เขียนเฉพาะ A–D และ F (ไม่แตะ E, G–K)
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

WORKSHEET_TITLE = "nvodyo8iy"

try:
    spreadsheet = client.open_by_key(google_sheet_id)
    sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("Google Sheet not found. Check GOOGLE_SHEET_ID and permissions.")
    raise
except gspread.exceptions.WorksheetNotFound:
    logging.error(f"Worksheet '{WORKSHEET_TITLE}' not found.")
    raise

# --- stUSDS (จาก stusds_tracker) ---
WALLET = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
USDS_TOKEN = "0xdc035D45d973E3EC169d2276DDab16f1e407384F"
STUSDS_VAULTS = ["0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD"]
DECIMALS = 18
RPC_TIMEOUT = 15
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"


def _gmt7_date():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")


def get_usds_balance():
    """ยอด USDS (ERC20) ใน wallet."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            return None
        wallet = Web3.to_checksum_address(WALLET.strip())
        token = Web3.to_checksum_address(USDS_TOKEN)
        abi = [{"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}]
        contract = w3.eth.contract(address=token, abi=abi)
        raw = contract.functions.balanceOf(wallet).call()
        return raw / (10 ** DECIMALS)
    except Exception as e:
        logging.error(f"get_usds_balance: {e}")
        return None


def get_vault_balance_usds(vault_address: str):
    """ยอดใน vault เป็น USDS (ERC4626)."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            return None
        wallet = Web3.to_checksum_address(WALLET.strip())
        vault = Web3.to_checksum_address(vault_address)
        abi = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        contract = w3.eth.contract(address=vault, abi=abi)
        shares = contract.functions.balanceOf(wallet).call()
        if shares == 0:
            return 0.0
        assets = contract.functions.convertToAssets(shares).call()
        return assets / (10 ** DECIMALS)
    except Exception as e:
        logging.error(f"get_vault_balance_usds: {e}")
        return None


def get_current_balance():
    """รวม USDS ใน wallet + stUSDS ใน vault(s)."""
    total = 0.0
    usds = get_usds_balance()
    if usds is not None:
        total += usds
    for vault_addr in STUSDS_VAULTS:
        v = get_vault_balance_usds(vault_addr)
        if v is not None:
            total += v
    return total if total > 0 else None


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
    """เขียนเฉพาะ A–D และ F (ไม่แตะ E, G–K)."""
    date_str = _gmt7_date()
    existing = get_existing_dates()
    if date_str in existing:
        logging.info(f"Date {date_str} already in sheet, skip")
        return
    row_num = find_next_row()
    sheet.update(range_name=f"A{row_num}:D{row_num}", values=[[date_str, "GS", "Ethereum", "USDS"]], value_input_option="USER_ENTERED")
    sheet.update(range_name=f"F{row_num}", values=[[round(current_balance, 2)]], value_input_option="USER_ENTERED")
    logging.info(f"Appended row {row_num}: {date_str} — Current Balance {current_balance:,.2f}")


if __name__ == "__main__":
    logging.info("GS (nvodyo8iy) → Sheet")
    balance = get_current_balance()
    if balance is not None:
        append_row(balance)
    else:
        logging.warning("Could not get balance, skip append")
    logging.info("Done.")
