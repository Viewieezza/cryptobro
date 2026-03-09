#!/usr/bin/env python3
"""
Morpho — ดึง balance จาก ERC4626 vaults แล้วแปลงเป็นมูลค่าจริงผ่าน convertToAssets

Vaults:
  1. sky.money USDS Risk Capital (0xf42bca22...) — underlying USDS (18 dec)
  2. sky.money USDT Risk Capital (0x2bD3A438...) — underlying USDT (6 dec)
"""
import os
from dotenv import load_dotenv

load_dotenv()

WALLET = os.getenv("WALLET_ADDRESS", "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7")
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 15

VAULTS = [
    {
        "name": "sky.money USDS Risk Capital",
        "address": "0xf42bca228D9bd3e2F8EE65Fec3d21De1063882d4",
        "asset_symbol": "USDS",
        "asset_decimals": 18,
    },
    {
        "name": "sky.money USDT Risk Capital",
        "address": "0x2bD3A43863c07B6A01581FADa0E1614ca5DF0E3d",
        "asset_symbol": "USDT",
        "asset_decimals": 6,
    },
    {
        "name": "sky.money USDT Savings",
        "address": "0x23f5E9c35820f4baB695Ac1F19c203cC3f8e1e11",
        "asset_symbol": "USDT",
        "asset_decimals": 6,
    },
]

VAULT_ABI = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]


def get_vault_balance(w3, vault_info, wallet):
    """อ่าน balance จาก ERC4626 vault ตัวเดียว"""
    from web3 import Web3

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(vault_info["address"]),
        abi=VAULT_ABI,
    )
    shares = contract.functions.balanceOf(wallet).call()
    if shares == 0:
        return {"shares": 0, "assets_raw": 0, "assets": 0.0, **vault_info}

    assets_raw = contract.functions.convertToAssets(shares).call()
    assets = assets_raw / (10 ** vault_info["asset_decimals"])
    return {"shares": shares, "assets_raw": assets_raw, "assets": assets, **vault_info}


def get_all_balances():
    """อ่าน balance จากทุก vault แล้วรวม"""
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
    if not w3.is_connected():
        print("❌ เชื่อม RPC ไม่ได้")
        return None

    wallet = Web3.to_checksum_address(WALLET)
    results = []
    total = 0.0

    for vault_info in VAULTS:
        bal = get_vault_balance(w3, vault_info, wallet)
        results.append(bal)
        total += bal["assets"]

    return {"vaults": results, "total_usd": total}


def main():
    print("=" * 60)
    print("Morpho — Vault Balances")
    print("=" * 60)
    print(f"Wallet: {WALLET}")
    print()

    data = get_all_balances()
    if data is None:
        return

    for v in data["vaults"]:
        status = f"${v['assets']:>15,.2f} {v['asset_symbol']}" if v["assets"] > 0 else "          (empty)"
        print(f"  {v['name']}")
        print(f"    {status}")
        print()

    print("-" * 40)
    print(f"  Total: ${data['total_usd']:>15,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
