import os
from dotenv import load_dotenv
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import time
import base64
import json
from typing import Optional, Dict, Any
from datetime import datetime
import re

# Try to import playwright (for JavaScript rendering)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

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
        self.url = 'https://www.asterdex.com/en/earn/alp'
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
    
    def get_page_html_with_playwright(self) -> str:
        """Get page HTML using Playwright (for JavaScript rendering)"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ScrapingError("Playwright is not installed. Please install it with: pip install playwright && playwright install chromium")
        
        try:
            logger.info("Using Playwright to render JavaScript...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to page and wait for network to be idle
                page.goto(self.url, wait_until='networkidle', timeout=60000)
                
                # Wait for content to load (look for ALP or price-related elements)
                try:
                    # Wait for either price element or stats element to appear
                    page.wait_for_selector('text=/ALP|TVL|APY/i', timeout=15000)
                except:
                    logger.warning("Timeout waiting for ALP content, waiting additional time...")
                
                # Additional wait for dynamic content and API calls
                page.wait_for_timeout(3000)
                
                html = page.content()
                browser.close()
                
                logger.info("Successfully rendered page with Playwright")
                return html
        except Exception as e:
            raise ScrapingError(f"Playwright error: {str(e)}")
    
    def scrape_alp_data(self, html_content: str = None) -> Dict[str, Any]:
        """Scrape ALP price, TVL, and APY from AsterDex website"""
        try:
            # Use Playwright to render JavaScript if HTML not provided
            if not html_content:
                if not PLAYWRIGHT_AVAILABLE:
                    raise ScrapingError(
                        "Playwright is not installed. Please install it with:\n"
                        "  pip install playwright\n"
                        "  playwright install chromium"
                    )
                
                html_content = self.get_page_html_with_playwright()
                logger.info("Successfully fetched page using Playwright")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize result
            result = {
                'price': None,
                'tvl': None,
                'apy': None
            }
            
            # Debug: Save HTML for inspection if needed
            page_text = soup.get_text()
            logger.info(f"Page text length: {len(page_text)}")
            logger.info(f"Page text preview (first 3000 chars): {page_text[:3000]}")
            
            # Also check raw HTML for debugging
            if 'ALP' in html_content or 'TVL' in html_content or 'APY' in html_content:
                logger.info("Found ALP/TVL/APY keywords in HTML content")
            else:
                logger.warning("ALP/TVL/APY keywords not found in HTML content")
            
            # Method 1: Search for price pattern in entire page text first (most flexible)
            # Look for "1 ALP = X.XXXX USD" or "ALP = X.XXXX USD" patterns
            price_patterns = [
                r'1\s+ALP\s*=\s*([\d.]+)\s*USD',
                r'ALP\s*=\s*([\d.]+)\s*USD',
                r'1\s*ALP\s*=\s*\$?([\d.]+)',
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, page_text, re.IGNORECASE)
                if price_match:
                    try:
                        price_value = float(price_match.group(1))
                        if 0.01 < price_value < 1000000:  # Reasonable price range
                            result['price'] = price_value
                            logger.info(f"Found ALP price using pattern '{pattern}': {result['price']}")
                            break
                    except ValueError:
                        continue
            
            # Method 2: Find price from specific div with class containing keywords
            if not result['price']:
                def has_price_classes(class_attr):
                    if not class_attr:
                        return False
                    class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
                    # More flexible: check if it has any of the key classes
                    return ('text-interactive-primary' in class_str or 'text-t-link' in class_str) and 'text-body1' in class_str
                
                price_divs = soup.find_all('div', class_=has_price_classes)
                for price_div in price_divs:
                    price_text = price_div.get_text(strip=True)
                    price_match = re.search(r'1\s+ALP\s*=\s*([\d.]+)\s*USD', price_text, re.IGNORECASE)
                    if price_match:
                        try:
                            result['price'] = float(price_match.group(1))
                            logger.info(f"Found ALP price from div: {result['price']}")
                            break
                        except ValueError:
                            continue
            
            # Method 3: Find TVL and APY - search in entire page text first
            # Look for "TVL $XX.XXM" or "TVL $XX.XXK" patterns
            tvl_patterns = [
                r'TVL\s*\$?([\d.]+)([MK]?)',
                r'Total\s+Value\s+Locked[:\s]*\$?([\d.]+)([MK]?)',
            ]
            
            for pattern in tvl_patterns:
                tvl_match = re.search(pattern, page_text, re.IGNORECASE)
                if tvl_match:
                    try:
                        tvl_value = float(tvl_match.group(1))
                        multiplier = (tvl_match.group(2) if len(tvl_match.groups()) > 1 else '').upper()
                        if multiplier == 'M':
                            result['tvl'] = tvl_value * 1_000_000
                        elif multiplier == 'K':
                            result['tvl'] = tvl_value * 1_000
                        else:
                            result['tvl'] = tvl_value
                        logger.info(f"Found TVL using pattern '{pattern}': ${result['tvl']:,.2f}")
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Look for APY pattern
            apy_patterns = [
                r'APY\s*([\d.]+)%',
                r'Annual\s+Percentage\s+Yield[:\s]*([\d.]+)%',
            ]
            
            for pattern in apy_patterns:
                apy_match = re.search(pattern, page_text, re.IGNORECASE)
                if apy_match:
                    try:
                        result['apy'] = float(apy_match.group(1))
                        logger.info(f"Found APY using pattern '{pattern}': {result['apy']}%")
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Method 4: Try to find from specific div structure (if page is rendered)
            if not result['tvl'] or not result['apy']:
                def has_stats_classes(class_attr):
                    if not class_attr:
                        return False
                    class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
                    # More flexible: check for key classes
                    return 'flex' in class_str and 'text-t-primary' in class_str and 'text-body1' in class_str
                
                stats_divs = soup.find_all('div', class_=has_stats_classes)
                for stats_div in stats_divs:
                    stats_text = stats_div.get_text(strip=True)
                    
                    # Extract TVL if not found yet
                    if not result['tvl']:
                        tvl_match = re.search(r'TVL\s*\$?([\d.]+)([MK]?)', stats_text, re.IGNORECASE)
                        if tvl_match:
                            try:
                                tvl_value = float(tvl_match.group(1))
                                multiplier = tvl_match.group(2).upper() if len(tvl_match.groups()) > 1 else ''
                                if multiplier == 'M':
                                    result['tvl'] = tvl_value * 1_000_000
                                elif multiplier == 'K':
                                    result['tvl'] = tvl_value * 1_000
                                else:
                                    result['tvl'] = tvl_value
                                logger.info(f"Found TVL from div: ${result['tvl']:,.2f}")
                            except (ValueError, IndexError):
                                pass
                    
                    # Extract APY if not found yet
                    if not result['apy']:
                        apy_match = re.search(r'APY\s*([\d.]+)%', stats_text, re.IGNORECASE)
                        if apy_match:
                            try:
                                result['apy'] = float(apy_match.group(1))
                                logger.info(f"Found APY from div: {result['apy']}%")
                            except (ValueError, IndexError):
                                pass
                    
                    if result['tvl'] and result['apy']:
                        break
            
            # Method 5: Look in script tags for JSON data (common in React apps)
            if not result['price'] or not result['tvl'] or not result['apy']:
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        script_text = script.string
                        # Look for price in various JSON formats
                        price_matches = re.findall(r'["\']?price["\']?\s*[:=]\s*([\d.]+)', script_text, re.IGNORECASE)
                        if price_matches and not result['price']:
                            try:
                                potential_price = float(price_matches[0])
                                if 0.01 < potential_price < 1000000:
                                    result['price'] = potential_price
                                    logger.info(f"Found ALP price in script: {result['price']}")
                            except (ValueError, IndexError):
                                pass
                        
                        # Look for ALP-specific patterns
                        alp_price_match = re.search(r'ALP.*?([\d.]+).*?USD', script_text, re.IGNORECASE)
                        if alp_price_match and not result['price']:
                            try:
                                potential_price = float(re.search(r'[\d.]+', alp_price_match.group(0)).group(0))
                                if 0.01 < potential_price < 1000000:
                                    result['price'] = potential_price
                                    logger.info(f"Found ALP price in script (pattern): {result['price']}")
                            except (ValueError, AttributeError):
                                pass
            
            # Validate that we found at least the price
            if not result['price']:
                # Log more debug info
                logger.warning("Could not find ALP price. Attempting to find any price-related text...")
                # Look for any text containing numbers that might be prices
                potential_prices = re.findall(r'[\d]+\.[\d]{2,4}', page_text)
                if potential_prices:
                    logger.warning(f"Found potential price-like numbers: {potential_prices[:10]}")
                logger.warning(f"Page title: {soup.title.string if soup.title else 'No title'}")
                raise ScrapingError("Could not extract ALP price from the webpage. The page may require JavaScript rendering.")
            
            logger.info(f"Successfully scraped ALP data: Price={result['price']}, TVL={result['tvl']}, APY={result['apy']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise ScrapingError(f"Failed to fetch webpage: {str(e)}")
        except Exception as e:
            logger.error(f"Error scraping ALP data: {e}")
            raise ScrapingError(f"Scraping error: {str(e)}")
    
    def find_alp_contract_address(self, html_content: str) -> Optional[str]:
        """Find ALP contract address from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text()
            
            # Look for Ethereum address pattern (0x followed by 40 hex characters)
            eth_address_pattern = r'0x[a-fA-F0-9]{40}'
            addresses = re.findall(eth_address_pattern, page_text)
            
            # Also check in script tags and data attributes
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    addresses.extend(re.findall(eth_address_pattern, script.string))
            
            # Filter addresses that might be ALP contract
            # Look for common contract-related keywords near the address
            for addr in addresses:
                # Check if address appears near ALP-related text
                addr_index = page_text.find(addr)
                if addr_index != -1:
                    context = page_text[max(0, addr_index-50):addr_index+90].lower()
                    if any(keyword in context for keyword in ['alp', 'contract', 'token', 'address']):
                        logger.info(f"Found potential ALP contract address: {addr}")
                        return addr
            
            if addresses:
                logger.info(f"Found Ethereum address (using first one): {addresses[0]}")
                return addresses[0]
            
            return None
        except Exception as e:
            logger.warning(f"Error finding ALP contract address: {e}")
            return None
    
    def get_token_balance(self, contract_address: str, wallet_address: str) -> Optional[float]:
        """Get ALP token balance using Etherscan API or web3"""
        if not wallet_address:
            logger.warning("Wallet address not provided, skipping token balance")
            return None
        
        if not contract_address:
            logger.warning("ALP contract address not provided, skipping token balance")
            return None
        
        try:
            # Method 2: Try web3 (if available)
            try:
                from web3 import Web3
                rpc_url = os.getenv("BSC_RPC_URL", "https://binance.llamarpc.com")
                return self._get_token_balance_web3(contract_address, wallet_address, rpc_url)
            except ImportError:
                logger.warning("web3 not installed, cannot use web3 method")
            
            # Method 3: Try public API (no API key required)
            return self._get_token_balance_public_api(contract_address, wallet_address)
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return None
    
    def _get_token_balance_etherscan(self, contract_address: str, wallet_address: str, api_key: str) -> Optional[float]:
        """Get token balance using Etherscan API"""
        try:
            url = "https://api.etherscan.io/api"
            params = {
                'module': 'account',
                'action': 'tokenbalance',
                'contractaddress': contract_address,
                'address': wallet_address,
                'tag': 'latest',
                'apikey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and data.get('message') == 'OK':
                    # Token balance is returned in smallest unit (wei), need to divide by 10^18
                    balance_wei = int(data.get('result', '0'))
                    balance = balance_wei / 10**18
                    logger.info(f"Got token balance from Etherscan: {balance}")
                    return balance
            
            logger.warning(f"Etherscan API error: {data.get('message', 'Unknown error')}")
            return None
        except Exception as e:
            logger.error(f"Etherscan API error: {e}")
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
    
    def _get_token_balance_public_api(self, contract_address: str, wallet_address: str) -> Optional[float]:
        """Get token balance using public API (no API key required)"""
        try:
            # Try ethplorer.io (free tier)
            url = f"https://api.ethplorer.io/getAddressInfo/{wallet_address}"
            params = {'apiKey': 'freekey'}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tokens = data.get('tokens', [])
                for token in tokens:
                    if token.get('tokenInfo', {}).get('address', '').lower() == contract_address.lower():
                        balance = float(token.get('balance', 0)) / 10**int(token.get('tokenInfo', {}).get('decimals', 18))
                        logger.info(f"Got token balance from ethplorer: {balance}")
                        return balance
            
            return None
        except Exception as e:
            logger.error(f"Public API error: {e}")
            return None
    
    def update_google_sheet(self, data: Dict[str, Any]) -> bool:
        """Update Google Sheet with ALP price, TVL, APY, and ALP Amount"""
        try:
            now = datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            date = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H:%M:%S')
            
            # Format values for display
            price = data.get('price', '')
            tvl = data.get('tvl', '')
            apy = data.get('apy', '')
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
            
            # Append new row (Column G is index 6)
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
            
            # Get HTML content using Playwright
            if not PLAYWRIGHT_AVAILABLE:
                raise ScrapingError(
                    "Playwright is not installed. Please install it with:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium"
                )
            
            html_content = self.get_page_html_with_playwright()
            logger.info("Successfully fetched page using Playwright")
            
            # Scrape ALP data (price, TVL, APY) from HTML
            data = self.scrape_alp_data(html_content=html_content)
            if not data.get('price'):
                raise ScrapingError("Failed to scrape ALP price")
            
            # Get ALP contract address
            if not self.alp_contract_address:
                logger.info("ALP contract address not set, trying to find from page...")
                self.alp_contract_address = self.find_alp_contract_address(html_content)
                if self.alp_contract_address:
                    logger.info(f"Found ALP contract address: {self.alp_contract_address}")
                else:
                    logger.warning("Could not find ALP contract address from page")
            
            # Get ALP token balance
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

