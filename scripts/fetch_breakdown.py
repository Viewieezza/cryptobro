import os, json, requests
from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO)

load_dotenv()
BASE_URL = "https://mainnet.zklighter.elliot.ai"
LLP_WALLET_ADDRESS = os.getenv("LLP_WALLET_ADDRESS")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Get sub account
r1 = requests.get(f"{BASE_URL}/api/v1/accountsByL1Address", headers=HEADERS, params={"l1_address": LLP_WALLET_ADDRESS})
subs = r1.json().get("sub_accounts", [])
idx = subs[0]["index"] if isinstance(subs[0], dict) else subs[0].index

# Get account data
r2 = requests.get(f"{BASE_URL}/api/v1/account", headers=HEADERS, params={"by": "index", "value": str(idx)})
acc = r2.json()["accounts"][0]

# Print out relevant info
print("=== TRADING ACCOUNT ===")
print("Total Asset Value (API):", acc.get("total_asset_value"))
print("Collateral:", acc.get("collateral"))
print("Positions:")
for pos in acc.get("positions", []):
    print(f"  {pos.get('symbol')} | Size: {pos.get('position')} | Unrealized PNL: {pos.get('unrealized_pnl')} | Position Value: {pos.get('position_value')} | Entry Price: {pos.get('avg_entry_price')}")

print("\n=== STAKING / POOL ===")
shares = acc.get("shares", [])
print(f"Shares: {len(shares)}")
for s in shares:
    print(f"  Pool ID: {s.get('public_pool_index', s.get('pool_index', '?'))} | Amount: {s.get('shares_amount')} | Principal: {s.get('principal_amount')}")

pending = acc.get("pending_unlocks", [])
print(f"Pending Unlocks: {len(pending)}")
for pu in pending:
    print(f"  Asset Index: {pu.get('asset_index')} | Amount: {pu.get('amount')}")

# Add LIT Price fetch
try:
    import ccxt
    exchange = ccxt.okx()
    ticker = exchange.fetch_ticker('LIT/USDT')
    print(f"\nCurrent LIT Price (OKX): {ticker['last']}")
except Exception as e:
    print("\nCould not fetch LIT price", e)
