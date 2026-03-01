import os
from dotenv import load_dotenv

load_dotenv()

RPC = os.getenv("ETH_RPC_URL") or os.getenv("ETHEREUM_RPC_URL") or "https://ethereum.publicnode.com"
RPC_TIMEOUT = 5
WALLET = "0x68Bc6dCb7793369a59289ddc5479F6DF417975E7"
MORPHO_CONTRACT = "0xf42bca228D9bd3e2F8EE65Fec3d21De1063882d4"

try:
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": RPC_TIMEOUT}))
    if not w3.is_connected():
        print("Not connected to RPC")
    else:
        wallet = Web3.to_checksum_address(WALLET)
        contract_addr = Web3.to_checksum_address(MORPHO_CONTRACT)
        abi = [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "shares", "type": "uint256"}], "name": "convertToAssets", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}
        ]
        c = w3.eth.contract(address=contract_addr, abi=abi)
        decimals = c.functions.decimals().call()
        print(f"Decimals: {decimals}")
        
        balance_raw = c.functions.balanceOf(wallet).call()
        print(f"balanceOf (raw): {balance_raw}")
        
        assets_raw = c.functions.convertToAssets(balance_raw).call()
        print(f"convertToAssets (raw): {assets_raw}")
        
        balance_18 = assets_raw / (10 ** 18)
        balance_6 = assets_raw / (10 ** 6)
        print(f"Balance if 18 decimals: {balance_18:,.2f}")
        print(f"Balance if 6 decimals: {balance_6:,.2f}")
except Exception as e:
    print(f"Error: {e}")
