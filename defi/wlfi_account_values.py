#!/usr/bin/env python3
"""
World Liberty Financial — ดึง Account Values จาก on-chain

Contract: 0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D (Ethereum Mainnet)
Function: getAccountValues((address,uint256)) → (int256 supplyValue, int256 borrowValue)

อ่าน portfolio value ของ wallet บน World Liberty Financial protocol
ค่า return เป็น 36 decimals (dYdX-style margin protocol)
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
WALLET = os.getenv("WALLET_ADDRESS", "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7")
WLFI_CONTRACT = "0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D"
SUB_ACCOUNT_ID = "0x4747474747474747474747474747474747474747474747474747474747474747"
RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 15
VALUE_DECIMALS = 36  # dYdX-style margin protocol uses 36 decimals for USD values


def get_account_values():
    """
    เรียก getAccountValues((address,uint256)) จาก WLFI contract
    Returns: dict with supply_value_usd and borrow_value_usd, or None
    """
    try:
        from web3 import Web3
        from eth_abi import encode, decode

        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            logging.error("เชื่อม RPC ไม่ได้")
            return None

        contract_addr = Web3.to_checksum_address(WLFI_CONTRACT)

        # subAccountId: bytes32 → uint256
        sub_id = int(SUB_ACCOUNT_ID[2:], 16)

        # getAccountValues((address,uint256)) → selector 0x124f914c
        selector = Web3.keccak(text="getAccountValues((address,uint256))")[:4]
        encoded = encode(["(address,uint256)"], [(WALLET, sub_id)])
        calldata = selector + encoded

        result = w3.eth.call({
            "to": contract_addr,
            "data": "0x" + calldata.hex()
        })

        # Decode: returns (int256, int256) — supplyValue, borrowValue
        supply_raw = int.from_bytes(result[0:32], "big", signed=True)
        borrow_raw = int.from_bytes(result[32:64], "big", signed=True)

        supply_usd = supply_raw / (10 ** VALUE_DECIMALS)
        borrow_usd = borrow_raw / (10 ** VALUE_DECIMALS)
        net_usd = supply_usd - abs(borrow_usd)

        return {
            "supply_value_raw": supply_raw,
            "borrow_value_raw": borrow_raw,
            "supply_value_usd": supply_usd,
            "borrow_value_usd": borrow_usd,
            "net_value_usd": net_usd,
        }

    except ImportError:
        logging.error("web3 / eth_abi ไม่ได้ติดตั้ง — pip install web3 eth_abi")
        return None
    except Exception as e:
        logging.error(f"get_account_values error: {e}")
        return None


def get_account_balances():
    """
    เรียก getAccountBalances((address,uint256)) → ดู balance แยกตาม market
    Returns: raw result bytes หรือ None
    """
    try:
        from web3 import Web3
        from eth_abi import encode

        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
        if not w3.is_connected():
            logging.error("เชื่อม RPC ไม่ได้")
            return None

        contract_addr = Web3.to_checksum_address(WLFI_CONTRACT)
        sub_id = int(SUB_ACCOUNT_ID[2:], 16)

        # getAccountBalances((address,uint256)) → selector 0x6a8194e7
        selector = bytes.fromhex("6a8194e7")
        encoded = encode(["(address,uint256)"], [(WALLET, sub_id)])
        calldata = selector + encoded

        result = w3.eth.call({
            "to": contract_addr,
            "data": "0x" + calldata.hex()
        })

        return result

    except Exception as e:
        logging.error(f"get_account_balances error: {e}")
        return None


def main():
    print("=" * 60)
    print("World Liberty Financial — Account Values")
    print("=" * 60)
    print(f"Contract : {WLFI_CONTRACT}")
    print(f"Wallet   : {WALLET}")
    print(f"SubAcct  : {SUB_ACCOUNT_ID[:18]}...{SUB_ACCOUNT_ID[-8:]}")
    print(f"RPC      : {RPC[:50]}...")
    print()

    # --- Account Values ---
    values = get_account_values()
    if values is None:
        print("❌ ไม่สามารถดึง Account Values ได้")
        return

    print("📊 Account Values (USD)")
    print("-" * 40)
    print(f"  Supply Value : ${values['supply_value_usd']:>15,.2f}")
    print(f"  Borrow Value : ${values['borrow_value_usd']:>15,.2f}")
    print(f"  Net Value    : ${values['net_value_usd']:>15,.2f}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
