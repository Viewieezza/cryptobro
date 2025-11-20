import os
from dotenv import load_dotenv
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import time
import base64
import json
from typing import Optional, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('alp_price_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass

class GoogleSheetsError(Exception):
    """Custom exception for Google Sheets errors"""
    pass

class ALPPriceScraper:
    def __init__(self):
        self.sheet = None
        self.client = None
        self.api_endpoint = 'https://www.asterdex.com/bapi/futures/v1/public/future/symbol/history-price'
        self.worksheet_title = 'ALP Price'
        self.alp_contract_address = None
        self.wallet_address = None
        
    def load_environment(self) -> None:
        """Load and validate environment variables"""
        try:
            load_dotenv()
            
            # Load Google credentials
            credentials_base64 = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_base64:
                raise ConfigError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set")
            
            # Load Google Sheet ID
            self.google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
            if not self.google_sheet_id:
                raise ConfigError("Environment variable GOOGLE_SHEET_ID is not set")
            
            # Load ALP contract address (optional, will try to find from page if not set)
            self.alp_contract_address = os.getenv("ALP_CONTRACT_ADDRESS")
            
            # Load wallet address (required for token balance)
            self.wallet_address = os.getenv("WALLET_ADDRESS")
            
            # Decode Google credentials
            try:
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                self.google_credentials = json.loads(credentials_json)
            except Exception as e:
                raise ConfigError(f"Error decoding Google credentials: {str(e)}")
                
        except Exception as e:
            logger.error(f"Failed to load environment: {e}")
            raise
    
    def setup_google_sheets(self) -> None:
        """Setup Google Sheets connection"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                self.google_credentials, scope
            )
            self.client = gspread.authorize(creds)
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.google_sheet_id)
            
            # Try to get the worksheet, create if it doesn't exist
            try:
                self.sheet = spreadsheet.worksheet(self.worksheet_title)
                logger.info(f"Found existing worksheet: {self.worksheet_title}")
            except gspread.exceptions.WorksheetNotFound:
                # Create new worksheet
                self.sheet = spreadsheet.add_worksheet(
                    title=self.worksheet_title,
                    rows=1000,
                    cols=10
                )
                # Set headers
                self.sheet.append_row(['Timestamp', 'ALP Price (USD)', 'TVL', 'APY (%)', 'Date', 'Time', 'ALP Amount'])
                logger.info(f"Created new worksheet: {self.worksheet_title}")
            else:
                # Check if headers exist, if not add them
                existing_data = self.sheet.get_all_values()
                if not existing_data or len(existing_data) == 0:
                    self.sheet.append_row(['Timestamp', 'ALP Price (USD)', 'TVL', 'APY (%)', 'Date', 'Time', 'ALP Amount'])
            
            logger.info(f"Successfully connected to Google Sheet: {self.worksheet_title}")
            
        except gspread.exceptions.SpreadsheetNotFound:
            raise GoogleSheetsError("Google Sheet not found. Check the ID and permissions.")
        except Exception as e:
            raise GoogleSheetsError(f"Failed to setup Google Sheets: {str(e)}")
    
    def get_alp_price_from_api(self) -> Dict[str, Any]:
        """Get ALP price from API directly"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Referer": "https://www.asterdex.com/",
                "Origin": "https://www.asterdex.com"
            }
            
            # Parameters for ALP price history
            params = {
                "dataSize": 4320,
                "channel": "BSC",
                "currency": "alb"  # ALP token
            }
            
            logger.info(f"Calling API: {self.api_endpoint}")
            logger.info(f"Parameters: {params}")
            
            response = requests.post(self.api_endpoint, headers=headers, json=params, timeout=10)
            
            if response.status_code != 200:
                error_msg = f"API returned status {response.status_code}: {response.text[:500]}"
                logger.error(error_msg)
                raise ScrapingError(error_msg)
            
            data = response.json()
            
            # Check if API call was successful
            if not data.get("success", False) or data.get("code") != "000000":
                error_msg = f"API error: {data.get('message', 'Unknown error')}"
                logger.error(error_msg)
                raise ScrapingError(error_msg)
            
            price_history = data.get("data", [])
            
            if not price_history:
                raise ScrapingError("No price history data returned from API")
            
            # Find the latest price (entry with maximum time)
            latest_entry = max(price_history, key=lambda x: x.get("time", 0))
            latest_price = latest_entry.get("price")
            latest_time = latest_entry.get("time")
            
            if latest_price is None:
                raise ScrapingError("Could not extract price from API response")
            
            logger.info(f"Latest ALP price: {latest_price} (time: {latest_time})")
            
            return {
                'price': latest_price,
                'time': latest_time,
                'price_history': price_history
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise ScrapingError(f"Failed to fetch price from API: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting ALP price: {e}")
            raise ScrapingError(f"Error getting ALP price: {str(e)}")
    
    def calculate_apy_from_history(self, price_history: list, period_days: int = 60) -> Optional[float]:
        """Calculate APY from price history using simple return annualized
        
        Based on testing, the website shows APY around 14.26% which is closest
        to a 60-day simple return calculation (gives ~14.44%).
        
        Args:
            price_history: List of price entries with 'price' and 'time' keys
            period_days: Number of days to look back (default 60 days based on website calculation)
        
        Returns:
            APY as percentage (e.g., 14.44 for 14.44%)
        """
        if not price_history or len(price_history) < 2:
            logger.warning("Not enough price history to calculate APY")
            return None
        
        try:
            # Sort by time (oldest to newest)
            sorted_history = sorted(price_history, key=lambda x: x.get("time", 0))
            
            newest = sorted_history[-1]
            newest_price = newest.get("price")
            newest_time = newest.get("time")
            
            if not newest_price or not newest_time:
                return None
            
            # Find price from period_days ago
            target_time = newest_time - (period_days * 24 * 60 * 60 * 1000)
            
            # Find closest entry to target time
            closest_entry = min(
                sorted_history,
                key=lambda x: abs(x.get("time", 0) - target_time)
            )
            
            closest_price = closest_entry.get("price")
            closest_time = closest_entry.get("time")
            
            if not closest_price or not closest_time:
                return None
            
            # Calculate time difference in days
            time_diff_ms = newest_time - closest_time
            time_diff_days = time_diff_ms / (1000 * 60 * 60 * 24)
            
            if time_diff_days <= 0:
                logger.warning(f"Invalid time difference: {time_diff_days} days")
                return None
            
            # Calculate APY using simple return annualized:
            # APY = ((new_price - old_price) / old_price) * (365 / days) * 100
            # This matches the website's calculation method (approximately 60 days)
            price_return = (newest_price - closest_price) / closest_price
            days_in_year = 365.0
            apy = price_return * (days_in_year / time_diff_days) * 100
            
            logger.info(f"Calculated APY: {apy:.2f}% (from {time_diff_days:.1f} days, "
                       f"price: ${closest_price:.8f} -> ${newest_price:.8f})")
            
            return apy
            
        except Exception as e:
            logger.error(f"Error calculating APY: {e}")
            return None
    
    def get_total_supply(self, contract_address: str) -> Optional[float]:
        """Get ALP token total supply using web3"""
        if not contract_address:
            logger.warning("ALP contract address not provided, skipping total supply")
            return None
        
        try:
            # Try web3 (if available)
            try:
                from web3 import Web3
                rpc_url = os.getenv("BSC_RPC_URL", "https://binance.llamarpc.com")
                return self._get_total_supply_web3(contract_address, rpc_url)
            except ImportError:
                logger.warning("web3 not installed, cannot get total supply")
                return None
            
        except Exception as e:
            logger.error(f"Error getting total supply: {e}")
            return None
    
    def _get_total_supply_web3(self, contract_address: str, rpc_url: str) -> Optional[float]:
        """Get token total supply using web3"""
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # ERC20 totalSupply ABI
            abi = [{
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }]
            
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            total_supply_wei = contract.functions.totalSupply().call()
            total_supply = total_supply_wei / 10**18
            
            logger.info(f"Got total supply from web3: {total_supply}")
            return total_supply
        except Exception as e:
            logger.error(f"web3 error getting total supply: {e}")
            return None
    
    def get_token_balance(self, contract_address: str, wallet_address: str) -> Optional[float]:
        """Get ALP token balance using web3"""
        if not wallet_address:
            logger.warning("Wallet address not provided, skipping token balance")
            return None
        
        if not contract_address:
            logger.warning("ALP contract address not provided, skipping token balance")
            return None
        
        try:
            # Try web3 (if available)
            try:
                from web3 import Web3
                rpc_url = os.getenv("BSC_RPC_URL", "https://binance.llamarpc.com")
                return self._get_token_balance_web3(contract_address, wallet_address, rpc_url)
            except ImportError:
                logger.warning("web3 not installed, cannot use web3 method")
                return None
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return None
    
    def _get_token_balance_web3(self, contract_address: str, wallet_address: str, rpc_url: str) -> Optional[float]:
        """Get token balance using web3"""
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # ERC20 balanceOf ABI
            abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            balance_wei = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            balance = balance_wei / 10**18
            
            logger.info(f"Got token balance from web3: {balance}")
            return balance
        except Exception as e:
            logger.error(f"web3 error: {e}")
            return None
    
    def update_google_sheet(self, data: Dict[str, Any]) -> bool:
        """Update Google Sheet with ALP price and ALP Amount"""
        try:
            now = datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            date = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H:%M:%S')
            
            # Format values for display
            price = data.get('price', '')
            tvl = data.get('tvl', '')  # Not available from API, keep for compatibility
            apy = data.get('apy', '')  # Not available from API, keep for compatibility
            alp_amount = data.get('alp_amount', '')
            
            # Format TVL if it exists
            if tvl:
                if tvl >= 1_000_000:
                    tvl_display = f"${tvl/1_000_000:.2f}M"
                elif tvl >= 1_000:
                    tvl_display = f"${tvl/1_000:.2f}K"
                else:
                    tvl_display = f"${tvl:.2f}"
            else:
                tvl_display = ''
            
            # Format APY if it exists
            apy_display = f"{apy}%" if apy else ''
            
            # Format ALP amount if it exists
            alp_amount_display = f"{alp_amount:.6f}" if alp_amount else ''
            
            # Append new row
            row_data = [timestamp, price, tvl_display, apy_display, date, time_str, alp_amount_display]
            self.sheet.append_row(row_data)
            
            logger.info(f"Successfully updated Google Sheet: Price={price}, TVL={tvl_display}, APY={apy_display}, ALP Amount={alp_amount_display} at {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating Google Sheet: {e}")
            raise GoogleSheetsError(f"Failed to update sheet: {str(e)}")
    
    def run(self) -> None:
        """Main execution method"""
        try:
            logger.info("Starting ALP price scraper...")
            
            # Load environment
            self.load_environment()
            logger.info("Environment loaded successfully")
            
            # Setup Google Sheets
            self.setup_google_sheets()
            logger.info("Google Sheets setup completed")
            
            # Get ALP price from API
            api_data = self.get_alp_price_from_api()
            if not api_data.get('price'):
                raise ScrapingError("Failed to get ALP price from API")
            
            # Calculate APY from price history
            # Based on testing, website uses ~60 days for APY calculation (gives ~14.26%)
            price_history = api_data.get('price_history', [])
            apy = None
            if price_history:
                # Use 60 days period (matches website's calculation method)
                apy = self.calculate_apy_from_history(price_history, period_days=60)
                if apy is None:
                    # Fallback: try with available data if 60 days not available
                    sorted_history = sorted(price_history, key=lambda x: x.get("time", 0))
                    if len(sorted_history) >= 2:
                        oldest_time = sorted_history[0].get("time", 0)
                        newest_time = sorted_history[-1].get("time", 0)
                        available_days = (newest_time - oldest_time) / (1000 * 60 * 60 * 24)
                        if available_days > 0:
                            # Use minimum of 60 days or available days
                            period = min(60, int(available_days))
                            apy = self.calculate_apy_from_history(price_history, period_days=period)
            
            # Calculate TVL = total_supply × price
            tvl = None
            if self.alp_contract_address:
                logger.info(f"Getting ALP total supply for TVL calculation...")
                total_supply = self.get_total_supply(self.alp_contract_address)
                if total_supply is not None and api_data.get('price'):
                    tvl = total_supply * api_data['price']
                    logger.info(f"Calculated TVL: ${tvl:,.2f} (Total Supply: {total_supply:,.2f} × Price: ${api_data['price']:.8f})")
                else:
                    logger.warning("Could not calculate TVL (missing total supply or price)")
            
            # Prepare data for sheet update
            data = {
                'price': api_data['price'],
                'tvl': tvl,  # Calculated from total supply × price
                'apy': apy,  # Calculated from price history
            }
            
            # Get ALP token balance if contract and wallet addresses are provided
            if self.alp_contract_address and self.wallet_address:
                logger.info(f"Getting ALP token balance for wallet: {self.wallet_address}")
                alp_balance = self.get_token_balance(self.alp_contract_address, self.wallet_address)
                if alp_balance is not None:
                    data['alp_amount'] = alp_balance
                    logger.info(f"ALP token balance: {alp_balance}")
                else:
                    logger.warning("Could not get ALP token balance")
                    data['alp_amount'] = None
            else:
                logger.warning("Missing contract address or wallet address, skipping token balance")
                data['alp_amount'] = None
            
            # Update Google Sheet
            self.update_google_sheet(data)
            logger.info("ALP data recorded successfully")
            
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except GoogleSheetsError as e:
            logger.error(f"Google Sheets error: {e}")
            raise
        except ScrapingError as e:
            logger.error(f"Scraping error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

def main():
    """Main function"""
    try:
        scraper = ALPPriceScraper()
        scraper.run()
        logger.info("ALP price scraper completed successfully")
    except Exception as e:
        logger.error(f"ALP price scraper failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
