#!/usr/bin/env python3
"""
Backfill Morpho — ดึง ERC4626 vault balances ย้อนหลังทุกวัน → Google Sheet "test_Morpho"

ใช้ balanceOf + convertToAssets ณ historical block ตั้งแต่วันฝากแรก
(Jan-28-2026 09:03:59 UTC) จนถึงวันนี้  แล้วเขียนลง Google Sheet

Usage:
    python3 scripts/backfill_morpho.py
"""
import sys
import os
import json
import base64
import logging
import time as time_mod
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
WALLET = os.getenv("WALLET_ADDRESS", "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7")

RPC = os.getenv("ETH_RPC_URL2") or os.getenv("ETH_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 30

# วันแรกที่ฝาก: Jan-28-2026 09:03:59 UTC
DEPOSIT_TS = int(datetime(2026, 1, 28, 9, 3, 59, tzinfo=timezone.utc).timestamp())
DEPOSIT_DATE = datetime(2026, 1, 28, tzinfo=timezone.utc)

# Morpho vaults (same as defi/morpho_balance.py)
VAULTS = [
    {
        "name": "sky.money USDS Risk Capital",
        "address": "0xf42bca228D9bd3e2F8EE65Fec3d21De1063882d4",
        "asset_symbol": "USDS",
        "asset_decimals": 18,
    },
    {
        "name": "sky.money USDT Risk Capital",
        "address": "0x2bD3A43863c07B6A01581FADa0E1614ca5DF0E3d",
        "asset_symbol": "USDT",
        "asset_decimals": 6,
    },
    {
        "name": "sky.money USDT Savings",
        "address": "0x23f5E9c35820f4baB695Ac1F19c203cC3f8e1e11",
        "asset_symbol": "USDT",
        "asset_decimals": 6,
    },
]

VAULT_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "shares", "type": "uint256"}],
        "name": "convertToAssets",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Google Sheet
WORKSHEET_TITLE = "test_Morpho"
DEFAULT_HEADERS = [
    "Date", "Protocol", "Chain", "Asset",
    "Initial Deposit", "Current Balance", "Incentive Received",
]


# ──────────────────────────────────────────────
# Google Sheets helpers
# ──────────────────────────────────────────────
def _get_sheet():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not credentials_base64:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")
    if not google_sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is not set")

    creds_dict = json.loads(base64.b64decode(credentials_base64).decode("utf-8"))
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(google_sheet_id)
    try:
        sheet = spreadsheet.worksheet(WORKSHEET_TITLE)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=WORKSHEET_TITLE, rows=1000, cols=10)
        logging.info(f"Created worksheet: {WORKSHEET_TITLE}")

    return sheet


def _ensure_headers(sheet):
    row1 = sheet.row_values(1)
    if len(row1) < 7 or not any(str(c).strip() for c in row1[:7]):
        sheet.update(range_name="A1:G1", values=[DEFAULT_HEADERS], value_input_option="USER_ENTERED")
        sheet.format("A1:G1", {"textFormat": {"bold": True}})
        logging.info(f"Set header row: {DEFAULT_HEADERS}")


def _get_existing_dates(sheet):
    col_a = sheet.col_values(1)
    existing = set()
    for i, cell in enumerate(col_a):
        if i == 0 and cell and "date" in str(cell).lower():
            continue
        part = str(cell).strip()[:10]
        if len(part) >= 10:
            existing.add(part)
    return existing


# ──────────────────────────────────────────────
# Ethereum helpers
# ──────────────────────────────────────────────
def _get_w3():
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to RPC: {RPC[:60]}...")
    logging.info(f"Connected to RPC: {RPC[:60]}...")
    return w3


def _find_block_by_timestamp(w3, target_ts):
    """Binary search หา block ที่ timestamp ใกล้เคียง target_ts ที่สุด"""
    lo = 1
    hi = w3.eth.block_number

    while lo < hi:
        mid = (lo + hi) // 2
        block = w3.eth.get_block(mid)
        if block["timestamp"] < target_ts:
            lo = mid + 1
        else:
            hi = mid

    return lo


def _get_vault_balance_at_block(w3, vault_info, wallet, block_number):
    """อ่าน balance จาก ERC4626 vault ตัวเดียว ณ historical block"""
    from web3 import Web3

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(vault_info["address"]),
        abi=VAULT_ABI,
    )

    try:
        shares = contract.functions.balanceOf(wallet).call(block_identifier=block_number)
        if shares == 0:
            return 0.0

        assets_raw = contract.functions.convertToAssets(shares).call(block_identifier=block_number)
        assets = assets_raw / (10 ** vault_info["asset_decimals"])
        return assets
    except Exception as e:
        logging.warning(f"  Vault {vault_info['name']} failed at block {block_number}: {e}")
        return 0.0


def _get_all_balances_at_block(w3, block_number):
    """อ่าน balance จากทุก vault ณ historical block แล้วรวม"""
    from web3 import Web3

    wallet = Web3.to_checksum_address(WALLET)
    total = 0.0
    details = []

    for vault_info in VAULTS:
        assets = _get_vault_balance_at_block(w3, vault_info, wallet, block_number)
        total += assets
        if assets > 0:
            details.append(f"{vault_info['name']}: ${assets:,.2f} {vault_info['asset_symbol']}")

    return total, details


# ──────────────────────────────────────────────
# Main backfill logic
# ──────────────────────────────────────────────
def _generate_daily_dates():
    """สร้าง list ของ (date_str, target_timestamp) ตั้งแต่วันฝากจนถึงวันนี้"""
    now = datetime.now(timezone.utc)
    current = DEPOSIT_DATE
    dates = []

    while current.date() <= now.date():
        # ใช้เวลา 09:03:59 UTC ของแต่ละวัน (= เวลาที่ฝาก)
        target_dt = current.replace(hour=9, minute=3, second=59)
        if target_dt > now:
            target_dt = now
        dates.append((current.strftime("%Y-%m-%d"), int(target_dt.timestamp())))
        current += timedelta(days=1)

    return dates


def main():
    print("=" * 60)
    print("Morpho — Historical Backfill (ERC4626 Vaults)")
    print("=" * 60)
    print(f"Wallet   : {WALLET}")
    print(f"RPC      : {RPC[:60]}...")
    print(f"Sheet    : {WORKSHEET_TITLE}")
    print(f"Vaults   : {len(VAULTS)}")
    print()

    # --- Connect RPC ---
    w3 = _get_w3()
    latest_block = w3.eth.block_number
    logging.info(f"Latest block: {latest_block:,}")

    # --- Generate dates ---
    daily_dates = _generate_daily_dates()
    logging.info(f"Date range: {daily_dates[0][0]} → {daily_dates[-1][0]} ({len(daily_dates)} days)")

    # --- Open Google Sheet ---
    sheet = _get_sheet()
    _ensure_headers(sheet)
    existing_dates = _get_existing_dates(sheet)
    logging.info(f"Dates already in sheet: {len(existing_dates)}")

    # Filter out dates already in sheet
    to_process = [(d, ts) for d, ts in daily_dates if d not in existing_dates]
    if not to_process:
        logging.info("✅ ไม่มีวันใหม่ที่ต้อง backfill — ข้อมูลครบแล้ว")
        return

    logging.info(f"Days to backfill: {len(to_process)}")
    print()

    # --- Backfill ---
    rows_to_write = []

    for i, (date_str, target_ts) in enumerate(to_process):
        logging.info(f"[{i+1}/{len(to_process)}] {date_str} — finding block for ts={target_ts} ...")

        # Find block
        block_num = _find_block_by_timestamp(w3, target_ts)
        block = w3.eth.get_block(block_num)
        actual_ts = block["timestamp"]
        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
        logging.info(f"  Block {block_num:,} — {actual_dt.isoformat()}")

        # Query all vault balances at that block
        total_usd, details = _get_all_balances_at_block(w3, block_num)
        for d in details:
            logging.info(f"    {d}")
        logging.info(f"  Total: ${total_usd:,.2f}")

        rows_to_write.append({
            "date": date_str,
            "total_usd": round(total_usd, 2),
        })

        # Rate limit
        time_mod.sleep(0.5)

    if not rows_to_write:
        logging.info("ไม่มี row ใหม่ที่ต้องเขียน")
        return

    # --- Write to Google Sheet (batch) ---
    logging.info(f"\n📝 Writing {len(rows_to_write)} rows to sheet '{WORKSHEET_TITLE}' ...")

    col_a = sheet.col_values(1)
    next_row = len(col_a) + 1
    for idx in range(len(col_a)):
        if not col_a[idx] or str(col_a[idx]).strip() == "":
            next_row = idx + 1
            break

    # Prepare batch data
    ad_rows = []
    f_rows = []
    for row_data in rows_to_write:
        ad_rows.append([
            row_data["date"],
            "Morpho",
            "Ethereum",
            "USDT",
        ])
        f_rows.append([row_data["total_usd"]])

    end_row = next_row + len(rows_to_write) - 1

    # Write A-D
    sheet.update(
        range_name=f"A{next_row}:D{end_row}",
        values=ad_rows,
        value_input_option="USER_ENTERED",
    )

    # Write F (Current Balance)
    sheet.update(
        range_name=f"F{next_row}:F{end_row}",
        values=f_rows,
        value_input_option="USER_ENTERED",
    )

    logging.info(f"✅ Done! Wrote {len(rows_to_write)} rows (row {next_row}–{end_row})")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
