#!/usr/bin/env python3
"""
Backfill WorldLib (WLFI) สำหรับ Wallet 2 — ดึงยอดคงเหลือย้อนหลังรายวัน → Google Sheet "Worldlib_2.2"

ดึงยอดคงเหลือ (supply_value_usd) ณ บล็อกย้อนหลังในแต่ละวัน
ตั้งแต่วันแรกที่เริ่มฝาก (2026-05-20 13:17:47 GMT+7) จนถึงปัจจุบัน

Usage:
    python scripts/backfill_worldlib_2.py
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

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
WALLET = os.getenv("WALLET_ADDRESS_2")
WLFI_CONTRACT = "0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D"
SUB_ACCOUNT_ID = "0x4747474747474747474747474747474747474747474747474747474747474747"
VALUE_DECIMALS = 36  # dYdX-style margin protocol uses 36 decimals

RPC = os.getenv("ETH_RPC_URL2") or os.getenv("ETH_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 30

# วันที่เริ่มฝากครั้งแรก: 2026-05-20 13:17:47 GMT+7 (= 06:17:47 UTC)
DEPOSIT_DATE = datetime(2026, 5, 20, tzinfo=timezone.utc)
DEPOSIT_HOUR = 6
DEPOSIT_MIN = 17
DEPOSIT_SEC = 47

# Google Sheet
WORKSHEET_TITLE = os.getenv("WLFI_WORKSHEET_TITLE_2", "Worldlib_2.2")
DEFAULT_HEADERS = ["Date", "Protocol", "Chain", "Asset", "Initial Deposit", "Current Balance", "Incentive Received"]


# ──────────────────────────────────────────────
# Google Sheets helpers
# ──────────────────────────────────────────────
def _get_sheet():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if google_sheet_id:
        google_sheet_id = google_sheet_id.replace(" ", "").strip()
    if not credentials_base64 or not google_sheet_id:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS และ GOOGLE_SHEET_ID ต้องตั้งใน .env")

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
    """Binary search หา block ที่ timestamp ใกล้เคียง target_ts ที่สุด บน Ethereum"""
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


def _get_wlfi_balance_at_block(w3, block_number):
    """ดึงยอดคงเหลือ supply_value_usd จากสัญญา WLFI ณ บล็อกที่กำหนด"""
    from web3 import Web3
    from eth_abi import encode

    wallet = Web3.to_checksum_address(WALLET)
    contract_addr = Web3.to_checksum_address(WLFI_CONTRACT)
    sub_id = int(SUB_ACCOUNT_ID[2:], 16)

    # getAccountValues((address,uint256)) → selector 0x124f914c
    selector = Web3.keccak(text="getAccountValues((address,uint256))")[:4]
    encoded = encode(["(address,uint256)"], [(wallet, sub_id)])
    calldata = selector + encoded

    try:
        result = w3.eth.call(
            {"to": contract_addr, "data": "0x" + calldata.hex()},
            block_identifier=block_number,
        )
        supply_raw = int.from_bytes(result[0:32], "big", signed=True)
        return supply_raw / (10 ** VALUE_DECIMALS)
    except Exception as e:
        logging.warning(f"  WLFI query failed at block {block_number}: {e}")
        return None


# ──────────────────────────────────────────────
# Main backfill logic
# ──────────────────────────────────────────────
def _generate_daily_dates():
    """สร้าง list ของ (date_str, target_timestamp) ตั้งแต่วันเริ่มฝากถึงปัจจุบัน"""
    now = datetime.now(timezone.utc)
    current = DEPOSIT_DATE
    dates = []

    while current.date() <= now.date():
        target_dt = current.replace(hour=DEPOSIT_HOUR, minute=DEPOSIT_MIN, second=DEPOSIT_SEC)
        if target_dt > now:
            target_dt = now
        dates.append((current.strftime("%Y-%m-%d"), int(target_dt.timestamp())))
        current += timedelta(days=1)

    return dates


def main():
    print("=" * 60)
    print("Worldlib — Historical Backfill for Wallet 2")
    print("=" * 60)
    print(f"Wallet   : {WALLET}")
    print(f"RPC      : {RPC[:60]}...")
    print(f"Sheet    : {WORKSHEET_TITLE}")
    print()

    if not WALLET:
        logging.error("❌ WALLET_ADDRESS_2 ไม่ได้กำหนดใน .env")
        return

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

    # กรองเฉพาะวันที่ยังไม่มีข้อมูลในชีต
    to_process = [(d, ts) for d, ts in daily_dates if d not in existing_dates]
    if not to_process:
        logging.info("✅ ข้อมูลย้อนหลังครบถ้วนแล้ว ไม่มีข้อมูลใหม่ที่ต้องใส่!")
        return

    logging.info(f"Days to backfill: {len(to_process)}")
    print()

    # --- Backfill ---
    rows_to_write = []

    for i, (date_str, target_ts) in enumerate(to_process):
        logging.info(f"[{i+1}/{len(to_process)}] {date_str} — finding block for ts={target_ts} ...")

        # ค้นหาบล็อกที่ใกล้เคียงเวลาเป้าหมายที่สุด
        block_num = _find_block_by_timestamp(w3, target_ts)
        block = w3.eth.get_block(block_num)
        actual_ts = block["timestamp"]
        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
        logging.info(f"  Block {block_num:,} — {actual_dt.isoformat()}")

        # ดึงยอดคงเหลือ ณ บล็อกนั้น
        balance = _get_wlfi_balance_at_block(w3, block_num)
        if balance is None:
            logging.warning(f"  ⚠️ Skip {date_str} — ดึงข้อมูลไม่สำเร็จ")
            time_mod.sleep(0.5)
            continue

        logging.info(f"  Balance: ${balance:,.2f}")

        rows_to_write.append({
            "date": date_str,
            "balance": round(balance, 2),
        })

        time_mod.sleep(0.5)

    if not rows_to_write:
        logging.info("ไม่มียอดใหม่ที่ต้องบันทึก")
        return

    # --- Write to Google Sheet ---
    logging.info(f"\n📝 Writing {len(rows_to_write)} rows to sheet '{WORKSHEET_TITLE}' ...")

    col_a = sheet.col_values(1)
    next_row = len(col_a) + 1
    for idx in range(len(col_a)):
        if not col_a[idx] or str(col_a[idx]).strip() == "":
            next_row = idx + 1
            break

    ad_rows = []
    f_rows = []
    for row_data in rows_to_write:
        ad_rows.append([
            row_data["date"],
            "WLFI",
            "ethereum",
            "USD1",
        ])
        f_rows.append([row_data["balance"]])

    end_row = next_row + len(rows_to_write) - 1

    # เขียนคอลัมน์ A-D
    sheet.update(
        range_name=f"A{next_row}:D{end_row}",
        values=ad_rows,
        value_input_option="USER_ENTERED",
    )

    # เขียนคอลัมน์ F
    sheet.update(
        range_name=f"F{next_row}:F{end_row}",
        values=f_rows,
        value_input_option="USER_ENTERED",
    )

    # จัดเรียงลำดับชีตตามคอลัมน์ A (วันที่) เพื่อไม่ให้ข้ามวันสลับกัน
    try:
        logging.info("Sorting sheet by Date ascending (keeping row 1 intact)...")
        # เรียงลำดับช่วง A2:G1000
        sheet.sort((1, 'asc'), range=f"A2:G{end_row + 100}")
    except Exception as e_sort:
        logging.warning(f"Could not sort sheet: {e_sort}")

    logging.info(f"✅ เสร็จสมบูรณ์! บันทึกยอด {len(rows_to_write)} วันเรียบร้อยแล้ว (แถวที่ {next_row}–{end_row})")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
