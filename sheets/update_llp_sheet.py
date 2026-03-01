"""
Lighter LLP → Google Sheet (แบบ edgex_google_sheet).
ดึงข้อมูลจาก Lighter API (REST) แล้วเขียนลงชีต worksheet "LLP".
รองรับ OTHER_POOL_CURRENT_VALUE ใน .env เป็น override ค่า other pool (USDT) ได้ถ้าต้องการ
"""
import requests
import os
import json
import base64
import logging
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

# --- Google Sheets (แบบ edgex_google_sheet) ---
credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
google_sheet_id = os.getenv("GOOGLE_SHEET_ID")

if credentials_base64 is None:
    raise ValueError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set")

try:
    GOOGLE_APPLICATION_CREDENTIALS_json = base64.b64decode(credentials_base64).decode("utf-8")
    GOOGLE_APPLICATION_CREDENTIALS = json.loads(GOOGLE_APPLICATION_CREDENTIALS_json)
except Exception as e:
    raise ValueError("Error decoding or parsing service account key: " + str(e))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_APPLICATION_CREDENTIALS, scope)
    client = gspread.authorize(creds)
except Exception as e:
    logging.error(f"Error setting up Google Sheets credentials: {e}")
    exit()

worksheet_title = "LLP"

try:
    sheet = client.open_by_key(google_sheet_id).worksheet(worksheet_title)
except gspread.exceptions.SpreadsheetNotFound:
    logging.error("The specified Google Sheet was not found. Check GOOGLE_SHEET_ID and permissions.")
    exit()
except gspread.exceptions.WorksheetNotFound:
    try:
        spreadsheet = client.open_by_key(google_sheet_id)
        sheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=20)
        logging.info(f"Created new worksheet: {worksheet_title}")
    except Exception as e:
        logging.error(f"Error creating worksheet: {e}")
        exit()
except Exception as e:
    logging.error(f"Error opening Google Sheet: {e}")
    exit()

# --- Lighter REST ---
LLP_WALLET_ADDRESS = os.getenv("LLP_WALLET_ADDRESS")
OTHER_POOL_CURRENT_VALUE = os.getenv("OTHER_POOL_CURRENT_VALUE")  # optional override for Pool 2
LIT_POOL_ID = 281474976624800   # Pool 1 (LIT)
OTHER_POOL_ID = 281474976710654  # Pool 2 (Other)
BASE_URL = "https://mainnet.zklighter.elliot.ai"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def _get(url, params=None, timeout=15):
    try:
        return requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    except Exception as e:
        logging.error(f"Request error: {e}")
        return None


def fetch_lighter_data():
    """
    ดึงข้อมูล Lighter ผ่าน REST.
    Returns:
        dict สำหรับหนึ่งแถวในชีต หรือ None ถ้า error
    """
    if not LLP_WALLET_ADDRESS:
        logging.error("LLP_WALLET_ADDRESS not set")
        return None

    url_l1 = f"{BASE_URL}/api/v1/accountsByL1Address"
    r = _get(url_l1, params={"l1_address": LLP_WALLET_ADDRESS})
    if not r or r.status_code != 200:
        logging.error(f"Failed to get account by L1: {r.status_code if r else 'no response'}")
        return None
    data_l1 = r.json()
    sub_accounts = data_l1.get("sub_accounts") or []
    if not sub_accounts:
        logging.error("No sub_accounts in response")
        return None
    account_index = sub_accounts[0].get("index") if isinstance(sub_accounts[0], dict) else getattr(sub_accounts[0], "index", None)
    if account_index is None:
        logging.error("No account_index")
        return None

    url_acc = f"{BASE_URL}/api/v1/account"
    r2 = _get(url_acc, params={"by": "index", "value": str(account_index)})
    if not r2 or r2.status_code != 200:
        logging.error(f"Failed to get account by index: {r2.status_code if r2 else 'no response'}")
        return None
    acc_data = r2.json()
    accounts = acc_data.get("accounts") or []
    if not accounts:
        logging.error("No accounts in response")
        return None
    acc = accounts[0]

    spot_qty = 0.0
    short_qty = 0.0
    short_entry = 0.0
    short_pnl = 0.0
    short_position_value = 0.0
    market_id = 120

    for pos in acc.get("positions") or []:
        if "LIT" in (pos.get("symbol") or ""):
            market_id = pos.get("market_id") or market_id
            size = float(pos.get("position") or 0)
            sign = pos.get("sign", 0)
            short_qty = abs(size) if sign < 0 else 0
            short_entry = float(pos.get("avg_entry_price") or 0)
            short_pnl = float(pos.get("unrealized_pnl") or 0)
            short_position_value = float(pos.get("position_value") or 0)
            break

    for asset in acc.get("assets") or []:
        if "LIT" in (asset.get("symbol") or ""):
            spot_qty = float(asset.get("balance") or 0)
            break

    # ใช้ 2 pool แบบ fix: LIT (281474976624800), Other (281474976710654) จาก shares
    lit_pool_shares = None
    lit_pool_principal = 0.0
    other_pool_shares = None
    other_pool_principal = 0.0
    for s in acc.get("shares") or []:
        pid_raw = s.get("public_pool_index") or s.get("index") or s.get("pool_index") or s.get("pool_id")
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pid = None
        shares_amt = s.get("shares_amount") or s.get("sharesAmount")
        p = s.get("principal_amount") or (s.get("additional_properties") or {}).get("principal_amount") or "0"
        try:
            principal = float(p)
        except (TypeError, ValueError):
            principal = 0.0
        if pid == LIT_POOL_ID:
            lit_pool_shares = shares_amt
            lit_pool_principal = principal
        elif pid == OTHER_POOL_ID:
            other_pool_shares = shares_amt
            other_pool_principal = principal

    def _pool_value_from_share_price(pool_id, shares_amount):
        if pool_id is None:
            return None
        r = _get(url_acc, params={"by": "index", "value": str(pool_id)})
        if not r or r.status_code != 200:
            return None
        try:
            pool_data = r.json()
            pool_accounts = pool_data.get("accounts") or []
            if not pool_accounts:
                return None
            pool_info = pool_accounts[0].get("pool_info") or {}
            share_prices = pool_info.get("share_prices") or []
            if not share_prices or shares_amount is None:
                return None
            latest = max(share_prices, key=lambda x: x.get("timestamp", 0))
            sp = latest.get("share_price")
            if sp is None:
                return None
            sp_f = float(sp)
            # ถ้า share_price เป็น 0 ให้ return None จะได้ใช้ principal เป็น fallback
            if sp_f <= 0:
                return None
            return round(float(shares_amount) * sp_f, 2)
        except (KeyError, TypeError, ValueError):
            return None

    pool_values = [lit_pool_principal, other_pool_principal]
    v1 = _pool_value_from_share_price(LIT_POOL_ID, lit_pool_shares)
    if v1 is not None:
        pool_values[0] = v1
        logging.info("Pool 1 (LIT) value from share_price")
    else:
        pool_values[0] = round(lit_pool_principal, 2)
        logging.info("Pool 1 (LIT) using principal_amount (share_price 0 or missing)")
    v2 = _pool_value_from_share_price(OTHER_POOL_ID, other_pool_shares)
    if v2 is not None:
        pool_values[1] = v2
        logging.info("Pool 2 (Other) value from share_price")
    else:
        pool_values[1] = round(other_pool_principal, 2)
        logging.info("Pool 2 (Other) using principal_amount (share_price 0 or missing)")

    if OTHER_POOL_CURRENT_VALUE is not None and OTHER_POOL_CURRENT_VALUE.strip() != "":
        try:
            pool_values[1] = float(OTHER_POOL_CURRENT_VALUE.strip())
            logging.info("Using OTHER_POOL_CURRENT_VALUE from env for Pool 2")
        except (TypeError, ValueError):
            pass

    # Column H: Lighter (LIT) price — ลองหลาย endpoint
    price = 0.0
    def _parse_price(j):
        if isinstance(j, dict):
            asks = j.get("asks") or j.get("data", {}).get("asks") or []
            bids = j.get("bids") or j.get("data", {}).get("bids") or []
            if asks and bids:
                a0, b0 = asks[0], bids[0]
                ap = a0.get("price") if isinstance(a0, dict) else (a0[0] if isinstance(a0, (list, tuple)) else 0)
                bp = b0.get("price") if isinstance(b0, dict) else (b0[0] if isinstance(b0, (list, tuple)) else 0)
                return (float(ap) + float(bp)) / 2
            for key in ("last", "price", "close", "lastPrice"):
                v = j.get(key) or (j.get("data") or {}).get(key)
                if v is not None:
                    return float(v)
            tickers = j.get("tickers") or j.get("data") or []
            if isinstance(tickers, list):
                for t in tickers:
                    if isinstance(t, dict) and (t.get("market_id") == market_id or t.get("marketId") == market_id):
                        return float(t.get("last") or t.get("price") or t.get("close") or 0)
        if isinstance(j, list) and len(j) > 0:
            c = j[0]
            if isinstance(c, dict):
                return float(c.get("c") or c.get("close") or 0)
        return None
    for path, q in [
        (f"{BASE_URL}/api/v1/orderBook", {"market_id": market_id}),
        (f"{BASE_URL}/api/v1/order_book", {"market_id": market_id}),
        (f"{BASE_URL}/api/v1/ticker", {"market_id": market_id}),
        (f"{BASE_URL}/api/v1/tickers", None),
        (f"{BASE_URL}/api/v1/candlesticks", {"market_id": market_id, "resolution": "1D", "limit": 1}),
        (f"{BASE_URL}/api/v1/candlesticks", {"symbol": "LIT-USDC", "resolution": "1D", "limit": 1}),
        (f"{BASE_URL}/api/v1/candlesticks", {"symbol": "Lighter-USDC", "resolution": "1D", "limit": 1}),
    ]:
        rr = _get(path, params=q or {}, timeout=12)
        if rr and rr.status_code == 200:
            try:
                j = rr.json()
                p = _parse_price(j)
                if p is not None and p > 0:
                    price = p
                    logging.info(f"Lighter price from API: {price} (path={path})")
                    break
            except Exception:
                pass
        if price > 0:
            break
    if price <= 0 and short_entry > 0:
        price = short_entry
        logging.info(f"Lighter price fallback to short_entry: {price}")

    tz = pytz.timezone("Asia/Bangkok")
    now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "date": now_str,
        "pool_values": [round(pool_values[0], 2), round(pool_values[1], 2)],
        "spot_qty": round(spot_qty, 4),
        "price": round(price, 4),
        "short_qty": round(short_qty, 2),
        "short_entry": round(short_entry, 4),
        "short_pnl": round(short_pnl, 2),
        "short_position_value": round(short_position_value, 2),
    }


def get_existing_dates():
    """Get set of dates (YYYY-MM-DD) from column A to avoid duplicates."""
    try:
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            return set()
        existing = set()
        for row in all_values[1:]:
            if len(row) > 0 and row[0] and str(row[0]).strip():
                date_part = str(row[0]).strip()[:10]
                if len(date_part) >= 10:
                    existing.add(date_part)
        logging.info(f"Found {len(existing)} existing date(s) in sheet")
        return existing
    except Exception as e:
        logging.error(f"Error reading existing dates: {e}")
        return set()


def find_next_empty_row_in_column_a():
    """First empty row in column A (1-based)."""
    try:
        column_a = sheet.col_values(1)
        for i in range(1, len(column_a)):
            if not column_a[i] or str(column_a[i]).strip() == "":
                return i + 1
        return len(column_a) + 1
    except Exception as e:
        logging.error(f"Error finding next empty row: {e}")
        return 2


def fill_google_sheet(data):
    """Append one row (A–L) if this date not already in sheet."""
    try:
        if not data:
            logging.warning("No data to write to sheet")
            return
        date_part = (data.get("date") or "")[:10]
        existing = get_existing_dates()
        if date_part and date_part in existing:
            logging.info(f"Date {date_part} already in sheet, skip")
            return
        empty_row = find_next_empty_row_in_column_a()
        row_data = [[
            data["date"],
            "Lighter",
            "Arbitrum",
            "LIT",
            data["pool_values"][0],
            data["pool_values"][1],
            "Lighter",
            data["price"],
            data["short_qty"],
            data["short_entry"],
            data["short_pnl"],
            data["short_position_value"],
        ]]
        range_str = f"A{empty_row}:L{empty_row}"
        sheet.update(range_name=range_str, values=row_data, value_input_option="USER_ENTERED")
        logging.info(f"Added row {empty_row}: {data['date']}")
    except Exception as e:
        logging.error(f"Error writing to Google Sheet: {e}")


if __name__ == "__main__":
    logging.info("=" * 50)
    logging.info("Lighter LLP → Google Sheet (update_llp_sheet)")
    logging.info("=" * 50)

    api_data = fetch_lighter_data()

    if api_data:
        logging.info(f"Data fetched: {api_data}")
        fill_google_sheet(api_data)
        logging.info("=" * 50)
        logging.info("Process completed successfully!")
        logging.info("=" * 50)
    else:
        logging.error("Failed to fetch data from API. Process aborted.")
