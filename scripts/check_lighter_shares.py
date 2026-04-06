import os
import json
import logging
from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

BASE_URL = "https://mainnet.zklighter.elliot.ai"
LLP_WALLET_ADDRESS = os.getenv("LLP_WALLET_ADDRESS")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def run():
    url_l1 = f"{BASE_URL}/api/v1/accountsByL1Address"
    r = requests.get(url_l1, headers=HEADERS, params={"l1_address": LLP_WALLET_ADDRESS})
    data_l1 = r.json()
    sub_accounts = data_l1.get("sub_accounts") or []
    if not sub_accounts:
        print("No sub_accounts")
        return
    
    account_index = sub_accounts[0].get("index") if isinstance(sub_accounts[0], dict) else getattr(sub_accounts[0], "index", None)
    print(f"Account Index: {account_index}")

    url_acc = f"{BASE_URL}/api/v1/account"
    r2 = requests.get(url_acc, headers=HEADERS, params={"by": "index", "value": str(account_index)})
    acc_data = r2.json()
    accounts = acc_data.get("accounts") or []
    if not accounts:
        print("No accounts")
        return
    acc = accounts[0]

    shares = acc.get("shares") or []
    print("Found SHARES:")
    print(json.dumps(shares, indent=2))

if __name__ == "__main__":
    run()
