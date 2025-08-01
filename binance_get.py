import requests
import time
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode

BASE_URL = "https://api.binance.com"

def get_signature(query_string, api_secret):
    if not api_secret or not query_string:
        raise ValueError("API secret and query string must not be None or empty")
    return hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_flexible_position(api_key, api_secret):
    endpoint = "/sapi/v1/simple-earn/flexible/position"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_locked_position(api_key, api_secret):
    endpoint = "/sapi/v1/simple-earn/locked/position"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_user_assets(api_key, api_secret):
    endpoint = "/sapi/v1/asset/getUserAsset"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_user_funding_assets(api_key, api_secret):
    endpoint = "/sapi/v1/asset/get-funding-asset"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.post(url, headers=headers)
    return response.json()

def get_spot_assets(api_key, api_secret):
    endpoint = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_asset_price(symbol):
    endpoint = "/api/v3/ticker/price"
    query_string = f"symbol={symbol}"
    url = f"{BASE_URL}{endpoint}?{query_string}"
    response = requests.get(url)
    return response.json()

def get_account_snapshot(api_key, api_secret, type='SPOT'):
    endpoint = "/sapi/v1/accountSnapshot"
    timestamp = int(time.time() * 1000)
    query_string = f"type={type}&timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_deposit_history(api_key, api_secret):
    endpoint = "/sapi/v1/capital/deposit/hisrec"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_trading_history(api_key, api_secret, symbol, start_time=None, end_time=None, limit=500):
    endpoint = "/api/v3/myTrades"
    timestamp = int(time.time() * 1000)
    query_string = f"symbol={symbol}&timestamp={timestamp}&limit={limit}"
    if start_time:
        query_string += f"&startTime={start_time}"
    if end_time:
        query_string += f"&endTime={end_time}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_withdraw_history(api_key, api_secret):
    endpoint = "/sapi/v1/capital/withdraw/history"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_flexible_subscription_record(api_key, api_secret, asset=None, start_time=None, end_time=None, current=1, size=10):
    endpoint = "/sapi/v1/simple-earn/flexible/history/subscriptionRecord"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}&current={current}&size={size}"
    if asset:
        query_string += f"&asset={asset}"
    if start_time:
        query_string += f"&startTime={start_time}"
    if end_time:
        query_string += f"&endTime={end_time}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_flexible_redemption_record(api_key, api_secret, asset=None, start_time=None, end_time=None, current=1, size=10):
    endpoint = "/sapi/v1/simple-earn/flexible/history/redemptionRecord"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}&current={current}&size={size}"
    if asset:
        query_string += f"&asset={asset}"
    if start_time:
        query_string += f"&startTime={start_time}"
    if end_time:
        query_string += f"&endTime={end_time}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_all_tokens():
    endpoint = "/api/v3/exchangeInfo"
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url)
    return response.json()

def get_all_orders(api_key, api_secret, symbol, start_time=None, end_time=None, limit=500):
    endpoint = "/api/v3/allOrders"
    timestamp = int(time.time() * 1000)
    query_string = f"symbol={symbol}&timestamp={timestamp}&limit={limit}"
    if start_time:
        query_string += f"&startTime={start_time}"
    if end_time:
        query_string += f"&endTime={end_time}"
    signature = get_signature(query_string, api_secret)
    headers = {
        "X-MBX-APIKEY": api_key
    }
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def get_historical_price(symbol, timestamp):
    endpoint = "/api/v3/aggTrades"
    query_string = f"symbol={symbol}&startTime={timestamp}&endTime={timestamp+60000}&limit=1"
    url = f"{BASE_URL}{endpoint}?{query_string}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]
        else:
            return {"error": "No data found for the given timestamp."}
    else:
        return {"error": response.json()}

def get_coinm_position_risk(api_key, api_secret, marginAsset=None, pair=None, recvWindow=None):
    """
    Retrieve Coin-M (Delivery) Futures position risk info via /dapi/v1/positionRisk

    Official docs:
    https://binance-docs.github.io/apidocs/delivery/en/#position-information-user_data

    Parameters:
    - api_key (str): Binance API key
    - api_secret (str): Binance API secret
    - marginAsset (str, optional): Filter by margin asset (e.g. "BTC")
    - pair (str, optional): Filter by pair (e.g. "BTCUSD")
    - recvWindow (int, optional): The number of milliseconds the request is valid for
    """
    COINM_BASE_URL = "https://dapi.binance.com"
    endpoint = "/dapi/v1/positionRisk"

    # Build query params
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp}
    if marginAsset:
        params["marginAsset"] = marginAsset
    if pair:
        params["pair"] = pair
    if recvWindow:
        params["recvWindow"] = recvWindow

    # Convert dict to query string
    query_string = urlencode(params)

    # Sign the query
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Construct final URL
    url = f"{COINM_BASE_URL}{endpoint}?{query_string}&signature={signature}"

    # Make request
    headers = {"X-MBX-APIKEY": api_key}
    response = requests.get(url, headers=headers)

    # Attempt JSON parse if valid; otherwise return raw info
    if "application/json" in response.headers.get("Content-Type", ""):
        return response.json()
    else:
        return {
            "error": f"HTTP {response.status_code}",
            "message": response.text
        }
