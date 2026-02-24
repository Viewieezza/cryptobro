#!/usr/bin/env python3
"""
Morpho — ดึง balance จาก contract แล้วแปลงเป็นมูลค่าจริงผ่าน convertToAssets

Contract: 0xf42bca228D9bd3e2F8EE65Fec3d21De1063882d4
1. balanceOf(wallet) → ได้ตัวเลข (shares/balance)
2. convertToAssets(balance) → ได้มูลค่า assets (USDT)
"""
import os
from dotenv import load_dotenv
load_dotenv()

MORPHO_CONTRACT = "0xf42bca228D9bd3e2F8EE65Fec3d21De1063882d4"
WALLET = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 15
DECIMALS = 18  # ปรับถ้า USDT ใช้ 6


def main():
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
    if not w3.is_connected():
        print("เชื่อม RPC ไม่ได้")
        return
    wallet = Web3.to_checksum_address(WALLET)
    contract_addr = Web3.to_checksum_address(MORPHO_CONTRACT)
    abi = [
        {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    c = w3.eth.contract(address=contract_addr, abi=abi)
    balance_raw = c.functions.balanceOf(wallet).call()
    print("balanceOf(wallet)  (raw)  :", balance_raw)
    print("balanceOf(wallet)  (human):", balance_raw / (10 ** DECIMALS))
    assets_raw = c.functions.convertToAssets(balance_raw).call()
    print()
    print("convertToAssets(balance) (raw)  :", assets_raw)
    print("convertToAssets(balance) (human):", assets_raw / (10 ** DECIMALS))


if __name__ == "__main__":
    main()
