#!/usr/bin/env python3
"""
stUSDT: ดึง balanceOf จาก contract แล้วเรียก previewRedeem(balance) ออกผลลัพธ์
Contract: 0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9
Wallet: 0x68Bc6dCb7793369a59289ddc5479F6DF417975E7
"""
import os
from dotenv import load_dotenv
load_dotenv()

WALLET = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
STUSDT_CONTRACT = "0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9"
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
DECIMALS = 18

def main():
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        print("เชื่อม RPC ไม่ได้")
        return
    wallet = Web3.to_checksum_address(WALLET)
    contract_addr = Web3.to_checksum_address(STUSDT_CONTRACT)
    abi = [
        {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "shares", "type": "uint256"}], "name": "previewRedeem", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    c = w3.eth.contract(address=contract_addr, abi=abi)
    balance_raw = c.functions.balanceOf(wallet).call()
    assets_raw = c.functions.previewRedeem(balance_raw).call()
    balance_human = balance_raw / (10 ** DECIMALS)
    assets_human = assets_raw / (10 ** DECIMALS)
    print("Contract:", STUSDT_CONTRACT)
    print("Wallet: ", WALLET)
    print()
    print("balanceOf(wallet)  (raw)   :", balance_raw)
    print("balanceOf(wallet)  (human)  :", balance_human)
    print()
    print("previewRedeem(balance) (raw)   :", assets_raw)
    print("previewRedeem(balance) (human) :", assets_human)

if __name__ == "__main__":
    main()
