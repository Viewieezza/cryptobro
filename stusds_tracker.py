#!/usr/bin/env python3
"""
Sky Money — ติดตาม stUSDS (Staked USDS) position บน Ethereum

ใช้ wallet address ดึงยอดจาก chain:
- USDS ใน wallet (ERC20)
- stUSDS/sUSDS position (ERC4626 vault: balanceOf → convertToAssets เป็น USDS)

รันด้วย venv: source venv/bin/activate แล้ว python stusds_tracker.py
ต้องติดตั้ง: pip install web3 python-dotenv
"""
import os
from typing import Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

# --- ตั้งค่าตรงนี้ ---
WALLET_ADDRESS = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
CHAIN = "ethereum"

# Sky Protocol — Ethereum (จาก Etherscan / Sky docs)
USDS_TOKEN = "0xdc035D45d973E3EC169d2276DDab16f1e407384F"   # USDS stablecoin
# stUSDS Expert / sUSDS Savings — vault เป็น ERC4626 (deposit USDS ได้ stUSDS/sUSDS tokens)
# ถ้า stUSDS อยู่คนละ contract จาก sUSDS ให้เพิ่มที่อยู่ใน STUSDS_VAULTS (จาก app หรือ Etherscan)
STUSDS_VAULTS = [
    "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD",  # sUSDS (Savings USDS) — ERC4626
]
DECIMALS = 18
RPC_TIMEOUT = 15

ETHEREUM_RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"


def get_usds_balance(rpc_url: str) -> Tuple[Optional[float], str]:
    """ยอด USDS (ERC20) ใน wallet."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            return None, "เชื่อม RPC ไม่ได้"
        wallet = Web3.to_checksum_address(WALLET_ADDRESS.strip())
        token = Web3.to_checksum_address(USDS_TOKEN)
        abi = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        contract = w3.eth.contract(address=token, abi=abi)
        raw = contract.functions.balanceOf(wallet).call()
        return raw / (10 ** DECIMALS), ""
    except Exception as e:
        return None, str(e)


def get_vault_balance_usds(rpc_url: str, vault_address: str) -> Tuple[Optional[float], str]:
    """ยอดใน vault เป็น USDS (ERC4626: balanceOf แล้ว convertToAssets)."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            return None, "เชื่อม RPC ไม่ได้"
        wallet = Web3.to_checksum_address(WALLET_ADDRESS.strip())
        vault = Web3.to_checksum_address(vault_address)
        abi = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        contract = w3.eth.contract(address=vault, abi=abi)
        shares = contract.functions.balanceOf(wallet).call()
        if shares == 0:
            return 0.0, ""
        assets = contract.functions.convertToAssets(shares).call()
        return assets / (10 ** DECIMALS), ""
    except Exception as e:
        return None, str(e)


def main():
    print("Sky Money — stUSDS tracker")
    print("Wallet:", WALLET_ADDRESS[:10] + "..." + WALLET_ADDRESS[-8:])
    print("Chain:", CHAIN)
    print()

    usds_balance, err = get_usds_balance(ETHEREUM_RPC)
    if err:
        print("USDS balance:", "Error —", err)
    else:
        print(f"USDS ใน wallet:     {usds_balance:,.4f} USDS")

    total_vault_usds = 0.0
    for i, vault_addr in enumerate(STUSDS_VAULTS):
        val, err = get_vault_balance_usds(ETHEREUM_RPC, vault_addr)
        if err:
            print(f"Vault {vault_addr[:10]}...: Error —", err)
        elif val is not None:
            total_vault_usds += val
            print(f"stUSDS/sUSDS (vault): {val:,.4f} USDS  (vault {vault_addr[:10]}...)")

    if total_vault_usds > 0:
        print()
        print(f"รวม position (vault): {total_vault_usds:,.4f} USDS")
    print()
    print("(อ้างอิง: https://app.sky.money/?network=Ethereum&widget=expert&expert_module=stusds&flow=supply)")


if __name__ == "__main__":
    main()
