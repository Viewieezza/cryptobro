import os, json, requests
from dotenv import load_dotenv
load_dotenv()
BASE_URL = "https://mainnet.zklighter.elliot.ai"
LLP_WALLET_ADDRESS = os.getenv("LLP_WALLET_ADDRESS")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
subs = requests.get(f"{BASE_URL}/api/v1/accountsByL1Address", headers=HEADERS, params={"l1_address": LLP_WALLET_ADDRESS}).json()["sub_accounts"]
for sub in subs:
    idx = sub["index"] if isinstance(sub, dict) else sub.index
    acc = requests.get(f"{BASE_URL}/api/v1/account", headers=HEADERS, params={"by": "index", "value": str(idx)}).json().get("accounts", [{}])[0]
    print(f"Index {idx}: shares={json.dumps(acc.get('shares'))}, pending_unlocks={json.dumps(acc.get('pending_unlocks'))}")
