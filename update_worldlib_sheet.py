"""
WLFI (World Liberty Finance) → Google Sheet "Worldlib"
อัพเดตรายวัน: อ่านข้อมูลจาก wlfi_position_data.json + INITIAL_DEPOSIT_USD แล้วเขียนหนึ่งแถวลงชีต คอลัมน์ A–G
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

# Header คอลัมน์ A–G ตามชีต "Worldlib" (ถ้าชีตว่างจะใช้ค่านี้)
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

# ใช้ initial + โหลดข้อมูลจาก wlfi_position_tracker
try:
    from wlfi_position_tracker import load_data, get_stats, INITIAL_DEPOSIT_USD
except ImportError:
    load_data = get_stats = None
    INITIAL_DEPOSIT_USD = float(os.getenv("WLFI_INITIAL_DEPOSIT_USD", "500073.4"))


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
    """โหลดข้อมูล WLFI จาก wlfi_position_tracker (JSON + INITIAL_DEPOSIT_USD). คืนค่า dict สำหรับหนึ่งแถว"""
    if load_data is None or get_stats is None:
        logging.warning("wlfi_position_tracker not available, use WLFI_INITIAL_DEPOSIT_USD in .env")
        return _get_wlfi_stats_fallback()
    data = load_data()
    data["initial_deposit_usd"] = INITIAL_DEPOSIT_USD
    stats = get_stats(data)
    if stats.get("current_usd") is None:
        return None
    return {
        "initial_usd": stats["initial_usd"],
        "current_usd": stats["current_usd"],
        "total_profit_usd": stats["total_profit_usd"],
        "return_pct": stats["return_pct"],
        "days_elapsed": stats["days_elapsed"],
        "daily_profit_avg_usd": stats["daily_profit_avg_usd"],
        "chain": (data.get("chain") or "ethereum").strip(),
    }


def _get_wlfi_stats_fallback():
    """Fallback อ่านจาก JSON โดยตรงเมื่อ import tracker ไม่ได้"""
    data_file = "wlfi_position_data.json"
    if not os.path.exists(data_file):
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["initial_deposit_usd"] = INITIAL_DEPOSIT_USD
    snapshots = data.get("snapshots") or []
    if not snapshots:
        return None
    last = snapshots[-1]
    current = float(last["value_usd"])
    initial = float(data.get("initial_deposit_usd", INITIAL_DEPOSIT_USD))
    total_profit = current - initial
    return_pct = (100 * total_profit / initial) if initial else None
    first_dt = datetime.fromisoformat(snapshots[0]["datetime"].replace("Z", "+00:00"))
    last_dt = datetime.fromisoformat(last["datetime"].replace("Z", "+00:00"))
    days = max(0, (last_dt - first_dt).total_seconds() / 86400)
    daily_avg = (total_profit / days) if days > 0 else None
    return {
        "initial_usd": initial,
        "current_usd": current,
        "total_profit_usd": total_profit,
        "return_pct": return_pct,
        "days_elapsed": days,
        "daily_profit_avg_usd": daily_avg,
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
        # A–G ตาม header: Date, Protocol, Chain, Asset, Initial Deposit, Current Balance, Incentive Received
        row_data = [[
            date_str,
            "WLFI",
            stats.get("chain", "ethereum"),
            "USD1",
            round(stats["initial_usd"], 2),
            round(stats["current_usd"], 2),
            round(stats["total_profit_usd"], 2) if stats.get("total_profit_usd") is not None else "",
        ]]
        sheet.update(range_name=f"A{row_num}:G{row_num}", values=row_data, value_input_option="USER_ENTERED")
        logging.info(f"Appended row {row_num}: {date_str}")
    except Exception as e:
        logging.error(f"Error appending row: {e}")


if __name__ == "__main__":
    logging.info("WLFI → Worldlib sheet (A–G)")
    ensure_headers()
    stats = get_wlfi_stats()
    if stats:
        append_row(stats)
        logging.info("Done.")
    else:
        logging.error("No WLFI data to write.")
