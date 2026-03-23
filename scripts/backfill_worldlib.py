#!/usr/bin/env python3
"""
Backfill WorldLib (WLFI) — ดึง Account Values ย้อนหลังทุกวัน → Google Sheet "test_Worldlib"

ใช้ getAccountValues((address,uint256)) ณ historical block ตั้งแต่วันฝากแรก
(Feb-01-2026 13:48:47 UTC) จนถึงวันนี้  แล้วเขียนลง Google Sheet

Usage:
    python scripts/backfill_worldlib.py
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
WLFI_CONTRACT = "0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D"
SUB_ACCOUNT_ID = "0x4747474747474747474747474747474747474747474747474747474747474747"
VALUE_DECIMALS = 36  # dYdX-style margin protocol

RPC = os.getenv("ETH_RPC_URL2") or os.getenv("ETH_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 30

# วันแรกที่ฝาก: Feb-01-2026 13:48:47 UTC
DEPOSIT_TS = int(datetime(2026, 2, 1, 13, 48, 47, tzinfo=timezone.utc).timestamp())
DEPOSIT_DATE = datetime(2026, 2, 1, tzinfo=timezone.utc)

# Google Sheet
WORKSHEET_TITLE = "test_Worldlib"
DEFAULT_HEADERS = [
    "Date", "Protocol", "Chain", "Asset",
    "Initial Deposit", "Current Balance", "Incentive Received",
]

INITIAL_DEPOSIT_USD = float(os.getenv("WLFI_INITIAL_DEPOSIT_USD", "500073.4"))


# ──────────────────────────────────────────────
# Google Sheets helpers
# ──────────────────────────────────────────────
def _get_sheet():
    """เปิด (หรือสร้าง) worksheet test_Worldlib แล้ว return sheet object"""
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
    """Return set ของ date strings (YYYY-MM-DD) ที่มีอยู่แล้วใน column A"""
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
    """
    Binary search หา block ที่ timestamp ใกล้เคียง target_ts ที่สุด
    Return block number
    """
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


def _get_account_values_at_block(w3, block_number):
    """
    เรียก getAccountValues((address,uint256)) ณ block_number
    Returns: dict with supply_value_usd, borrow_value_usd, net_value_usd or None
    """
    from web3 import Web3
    from eth_abi import encode

    contract_addr = Web3.to_checksum_address(WLFI_CONTRACT)
    sub_id = int(SUB_ACCOUNT_ID[2:], 16)

    # getAccountValues((address,uint256)) → selector 0x124f914c
    selector = Web3.keccak(text="getAccountValues((address,uint256))")[:4]
    encoded = encode(["(address,uint256)"], [(WALLET, sub_id)])
    calldata = selector + encoded

    try:
        result = w3.eth.call(
            {"to": contract_addr, "data": "0x" + calldata.hex()},
            block_identifier=block_number,
        )
    except Exception as e:
        logging.warning(f"  eth_call failed at block {block_number}: {e}")
        return None

    supply_raw = int.from_bytes(result[0:32], "big", signed=True)
    borrow_raw = int.from_bytes(result[32:64], "big", signed=True)

    supply_usd = supply_raw / (10 ** VALUE_DECIMALS)
    borrow_usd = borrow_raw / (10 ** VALUE_DECIMALS)
    net_usd = supply_usd - abs(borrow_usd)

    return {
        "supply_value_usd": supply_usd,
        "borrow_value_usd": borrow_usd,
        "net_value_usd": net_usd,
    }


# ──────────────────────────────────────────────
# Main backfill logic
# ──────────────────────────────────────────────
def _generate_daily_dates():
    """
    สร้าง list ของ (date_str, target_timestamp) ตั้งแต่วันฝากจนถึงวันนี้
    ใช้เวลา 13:48:47 UTC ของแต่ละวัน (= เวลาที่ฝาก)
    """
    now = datetime.now(timezone.utc)
    current = DEPOSIT_DATE
    dates = []

    while current.date() <= now.date():
        target_dt = current.replace(hour=13, minute=48, second=47)
        # สำหรับวันนี้ ถ้ายังไม่ถึงเวลา 13:48 → ใช้เวลาปัจจุบัน
        if target_dt > now:
            target_dt = now
        dates.append((current.strftime("%Y-%m-%d"), int(target_dt.timestamp())))
        current += timedelta(days=1)

    return dates


def main():
    print("=" * 60)
    print("WorldLib (WLFI) — Historical Backfill")
    print("=" * 60)
    print(f"Contract : {WLFI_CONTRACT}")
    print(f"Wallet   : {WALLET}")
    print(f"RPC      : {RPC[:60]}...")
    print(f"Sheet    : {WORKSHEET_TITLE}")
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
    block_cache = {}  # cache block lookups

    for i, (date_str, target_ts) in enumerate(to_process):
        logging.info(f"[{i+1}/{len(to_process)}] {date_str} — finding block for ts={target_ts} ...")

        # Find block
        block_num = _find_block_by_timestamp(w3, target_ts)
        block = w3.eth.get_block(block_num)
        actual_ts = block["timestamp"]
        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
        logging.info(f"  Block {block_num:,} — {actual_dt.isoformat()}")

        # Query account values at that block
        values = _get_account_values_at_block(w3, block_num)
        if values is None:
            logging.warning(f"  ⚠️ Skip {date_str} — could not get account values")
            time_mod.sleep(0.5)
            continue

        supply_usd = values["supply_value_usd"]
        logging.info(f"  Supply: ${supply_usd:,.2f}")

        rows_to_write.append({
            "date": date_str,
            "supply_usd": round(supply_usd, 2),
        })

        # Rate limit
        time_mod.sleep(0.5)

    if not rows_to_write:
        logging.info("ไม่มี row ใหม่ที่ต้องเขียน")
        return

    # --- Write to Google Sheet (batch) ---
    logging.info(f"\n📝 Writing {len(rows_to_write)} rows to sheet '{WORKSHEET_TITLE}' ...")

    # Find the first empty row
    col_a = sheet.col_values(1)
    next_row = len(col_a) + 1
    # Check for empty rows in between
    for idx in range(len(col_a)):
        if not col_a[idx] or str(col_a[idx]).strip() == "":
            next_row = idx + 1
            break

    # Prepare batch data for A-D columns
    ad_rows = []
    f_rows = []
    for row_data in rows_to_write:
        ad_rows.append([
            row_data["date"],
            "WLFI",
            "ethereum",
            "USD1",
        ])
        f_rows.append([row_data["supply_usd"]])

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
