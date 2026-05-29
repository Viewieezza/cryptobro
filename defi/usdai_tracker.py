#!/usr/bin/env python3
"""
USD.AI — ติดตามยอด USDai (stablecoin) และ sUSDai (Staked/Yield-bearing vault) บน Arbitrum One

Contract:
- USDai (ERC20): 0x0A1A1A107E45b7ced86833863f482Bc5f4ED82ef
- sUSDai (ERC4626 Vault): 0x0b2B2b2076D95dDA7817E785989Fe353fe955ef9
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Config ---
WALLET = os.getenv("WALLET_ADDRESS_2")
USDAI_TOKEN = "0x0A1A1A107E45b7ced86833863f482Bc5f4ED82ef"
SUSDAI_VAULT = "0x0b2B2b2076D95dDA7817E785989Fe353fe955ef9"
RPC = os.getenv("ARB_RPC_URL", "https://arb1.arbitrum.io/rpc")
RPC_TIMEOUT = 15
DECIMALS = 18


def get_usdai_balances(wallet_address=None):
    """
    ดึงยอดคงเหลือของ USDai (ERC20) และ sUSDai (ERC4626 Vault) จาก Arbitrum One
    Returns: dict with wallet_usdai, vault_usdai, total_usdai or None
    """
    target_wallet = wallet_address or WALLET
    if not target_wallet:
        logging.error("ไม่มีการระบุ wallet_address (WALLET_ADDRESS_2 ใน env ว่างเปล่า)")
        return None

    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            logging.error("เชื่อมต่อ Arbitrum RPC ไม่สำเร็จ")
            return None

        wallet = Web3.to_checksum_address(target_wallet.strip())
        usdai_addr = Web3.to_checksum_address(USDAI_TOKEN)
        susdai_addr = Web3.to_checksum_address(SUSDAI_VAULT)

        # Standard ERC20 balanceOf ABI
        abi_erc20 = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]

        # ERC4626 Vault balanceOf and convertToAssets ABI
        abi_vault = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]

        usdai_contract = w3.eth.contract(address=usdai_addr, abi=abi_erc20)
        susdai_contract = w3.eth.contract(address=susdai_addr, abi=abi_vault)

        # 1. ยอด USDai ในกระเป๋าแมนวล
        wallet_raw = usdai_contract.functions.balanceOf(wallet).call()
        wallet_usdai = wallet_raw / (10 ** DECIMALS)

        # 2. ยอด sUSDai ใน Vault (ฝากไว้)
        shares_raw = susdai_contract.functions.balanceOf(wallet).call()
        vault_usdai = 0.0

        if shares_raw > 0:
            # แปลง sUSDai shares เป็น USDai assets
            try:
                assets_raw = susdai_contract.functions.convertToAssets(shares_raw).call()
                vault_usdai = assets_raw / (10 ** DECIMALS)
            except Exception as e_vault:
                logging.warning(f"convertToAssets error: {e_vault}, trying alternative previewRedeem")
                try:
                    # Alternative previewRedeem
                    abi_vault_alt = [
                        {"inputs": [{"name": "shares", "type": "uint256"}], "name": "previewRedeem", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
                    ]
                    c_alt = w3.eth.contract(address=susdai_addr, abi=abi_vault_alt)
                    assets_raw = c_alt.functions.previewRedeem(shares_raw).call()
                    vault_usdai = assets_raw / (10 ** DECIMALS)
                except Exception as e_alt:
                    logging.error(f"previewRedeem error: {e_alt}")
                    # fallback ใช้ยอด raw shares โดยตรง (โดยอนุมานว่า 1 share = 1 asset ถ้าแปลงไม่ได้เลย)
                    vault_usdai = shares_raw / (10 ** DECIMALS)

        total_usdai = wallet_usdai + vault_usdai

        return {
            "wallet_usdai": wallet_usdai,
            "vault_usdai": vault_usdai,
            "total_usdai": total_usdai
        }

    except ImportError:
        logging.error("กรุณาติดตั้ง web3 library — pip install web3")
        return None
    except Exception as e:
        logging.error(f"get_usdai_balances error: {e}")
        return None


def main():
    print("=" * 60)
    print("USD.AI Tracker — Arbitrum One")
    print("=" * 60)
    print(f"Wallet : {WALLET}")
    print(f"RPC    : {RPC}")
    print()

    balances = get_usdai_balances()
    if balances is None:
        print("❌ ไม่สามารถดึงยอดคงเหลือของ USD.AI ได้")
        return

    print("📊 ยอดเงิน USD.AI (USDai)")
    print("-" * 40)
    print(f"  USDai ใน Wallet : ${balances['wallet_usdai']:>15,.4f}")
    print(f"  sUSDai ใน Vault  : ${balances['vault_usdai']:>15,.4f}")
    print(f"  ยอดรวมสุทธิ       : ${balances['total_usdai']:>15,.4f}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
