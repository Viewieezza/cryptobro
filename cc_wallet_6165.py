import os
from dotenv import load_dotenv
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from binance_get import get_asset_price, get_coinm_position_risk
import time
import base64
import json
from typing import Optional, Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cc_wallet_6165.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

class APIError(Exception):
    """Custom exception for API errors"""
    pass

class GoogleSheetsError(Exception):
    """Custom exception for Google Sheets errors"""
    pass

class CashAndCarryProcessor:
    def __init__(self):
        self.sheet = None
        self.client = None
        self.api_key = None
        self.api_secret = None
        self.wallet_name = 'Wallet 1'
        self.worksheet_title = 'Cash&Carry'
        
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
            
            # Load Binance API credentials
            self.api_key = os.getenv("API_KEY1")
            self.api_secret = os.getenv("API_SECRET1")
            
            if not self.api_key or not self.api_secret:
                raise ConfigError(
                    f"Missing Binance API credentials. "
                    f"API_KEY1: {'Set' if self.api_key else 'NOT SET'}, "
                    f"API_SECRET1: {'Set' if self.api_secret else 'NOT SET'}"
                )
            
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
            
            # Open the worksheet
            self.sheet = self.client.open_by_key(self.google_sheet_id).worksheet(self.worksheet_title)
            logger.info(f"Successfully connected to Google Sheet: {self.worksheet_title}")
            
        except gspread.exceptions.SpreadsheetNotFound:
            raise GoogleSheetsError("Google Sheet not found. Check the ID and permissions.")
        except gspread.exceptions.WorksheetNotFound:
            raise GoogleSheetsError(f"Worksheet '{self.worksheet_title}' not found.")
        except Exception as e:
            raise GoogleSheetsError(f"Failed to setup Google Sheets: {str(e)}")
    
    def update_cell_with_retry(self, row: int, col: int, value: Any, max_attempts: int = 3, sleep_time: int = 300) -> bool:
        """Update a cell with retry logic"""
        for attempt in range(1, max_attempts + 1):
            try:
                self.sheet.update_cell(row, col, value)
                logger.debug(f"Successfully updated cell ({row}, {col}) with value: {value}")
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed to update cell ({row}, {col}): {e}")
                if attempt < max_attempts:
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to update cell ({row}, {col}) after {max_attempts} attempts")
                    return False
    
    def execute_binance_api_with_retry(self, api_function, *args, max_attempts: int = 3, sleep_time: int = 300) -> Optional[Any]:
        """Execute a Binance API function with retry logic"""
        for attempt in range(1, max_attempts + 1):
            try:
                result = api_function(*args)
                logger.debug(f"Successfully executed API call: {api_function.__name__}")
                return result
            except Exception as e:
                logger.warning(f"Binance API attempt {attempt}/{max_attempts} failed: {e}")
                if attempt < max_attempts:
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to call Binance API after {max_attempts} attempts")
                    return None
    
    def get_binance_data(self) -> tuple[Optional[List], Optional[float]]:
        """Get Binance position data and BTC price"""
        try:
            # Get coinm positions
            coinm_positions = self.execute_binance_api_with_retry(
                get_coinm_position_risk, self.api_key, self.api_secret
            )
            
            if coinm_positions is None:
                raise APIError("Failed to get coinm positions")
            
            # Validate coinm positions response
            if isinstance(coinm_positions, dict) and 'error' in coinm_positions:
                raise APIError(f"API Error: {coinm_positions}")
            
            if not isinstance(coinm_positions, list):
                raise APIError(f"Unexpected data structure: {coinm_positions}")
            
            # Get BTC price
            btc_price_data = self.execute_binance_api_with_retry(get_asset_price, "BTCUSDT")
            if btc_price_data is None:
                raise APIError("Failed to get BTC price")
            
            btc_price = btc_price_data.get('price') if isinstance(btc_price_data, dict) else btc_price_data
            
            logger.info(f"Successfully retrieved Binance data. BTC Price: {btc_price}")
            return coinm_positions, btc_price
            
        except Exception as e:
            logger.error(f"Failed to get Binance data: {e}")
            raise
    
    def should_process_row(self, wallet: str, contract_symbol: str, start_date: str, end_date: str) -> bool:
        """Check if a row should be processed based on business rules"""
        if wallet != self.wallet_name:
            return False
        
        if not contract_symbol or contract_symbol.strip() == "":
            logger.debug(f"Skipping row: No contract symbol")
            return False
        
        if not start_date or start_date.strip() == "":
            logger.info(f"Skipping row: Start date (Column C) is empty for {contract_symbol}")
            return False
        
        if end_date and end_date.strip() != "":
            logger.info(f"Skipping row: End date (Column D) already filled for {contract_symbol}")
            return False
        
        return True
    
    def find_matching_position(self, contract_symbol: str, coinm_positions: List[Dict]) -> Optional[Dict]:
        """Find matching position in coinm positions"""
        for position in coinm_positions:
            if isinstance(position, dict) and position.get('symbol') == contract_symbol:
                return position
        return None
    
    def process_position_data(self, matching_position: Dict, btc_price: float) -> tuple[float, float, float]:
        """Extract and calculate position data"""
        try:
            future_price = float(matching_position.get('markPrice', 0))
            notional_value = float(matching_position.get('notionalValue', 0))
            btc_amount = -1 * notional_value
            
            return future_price, btc_amount, btc_price
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing position data: {e}")
            raise
    
    def update_sheet_row(self, row_index: int, future_price: float, btc_amount: float, btc_price: float) -> bool:
        """Update sheet row with position data"""
        try:
            # Update columns K, L, and M
            success_k = self.update_cell_with_retry(row_index, 11, future_price)  # Column K
            success_l = self.update_cell_with_retry(row_index, 12, btc_amount)    # Column L
            success_m = self.update_cell_with_retry(row_index, 13, btc_price)     # Column M
            
            if all([success_k, success_l, success_m]):
                logger.info(f"Successfully updated row {row_index}")
                return True
            else:
                logger.error(f"Failed to update some cells in row {row_index}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating sheet row {row_index}: {e}")
            return False
    
    def process_sheet_data(self, coinm_positions: List[Dict], btc_price: float) -> None:
        """Process all sheet data"""
        try:
            all_values = self.sheet.get_all_values()
            processed_count = 0
            skipped_count = 0
            
            # Process data starting from row 3
            for row_index, row in enumerate(all_values[2:], start=3):
                try:
                    # Extract row data
                    wallet = row[0] if len(row) > 0 else ""
                    contract_symbol = row[1] if len(row) > 1 else ""
                    start_date = row[2] if len(row) > 2 else ""
                    end_date = row[3] if len(row) > 3 else ""
                    
                    # Check if row should be processed
                    if not self.should_process_row(wallet, contract_symbol, start_date, end_date):
                        skipped_count += 1
                        continue
                    
                    # Find matching position
                    matching_position = self.find_matching_position(contract_symbol, coinm_positions)
                    
                    if matching_position:
                        # Process position data
                        future_price, btc_amount, btc_price = self.process_position_data(matching_position, btc_price)
                        
                        # Update sheet
                        if self.update_sheet_row(row_index, future_price, btc_amount, btc_price):
                            processed_count += 1
                            logger.info(f"Processed: Wallet={wallet}, Symbol={contract_symbol}, "
                                      f"Future Price={future_price}, BTC Amount={btc_amount}, BTC Price={btc_price}")
                        else:
                            logger.error(f"Failed to update sheet for {contract_symbol}")
                    else:
                        logger.warning(f"No position data found for {contract_symbol}")
                        skipped_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing row {row_index}: {e}")
                    continue
            
            logger.info(f"Processing complete. Processed: {processed_count}, Skipped: {skipped_count}")
            
        except Exception as e:
            logger.error(f"Error processing sheet data: {e}")
            raise
    
    def run(self) -> None:
        """Main execution method"""
        try:
            logger.info("Starting Cash & Carry processor...")
            
            # Load environment
            self.load_environment()
            logger.info("Environment loaded successfully")
            
            # Setup Google Sheets
            self.setup_google_sheets()
            logger.info("Google Sheets setup completed")
            
            # Get Binance data
            coinm_positions, btc_price = self.get_binance_data()
            logger.info("Binance data retrieved successfully")
            
            # Process sheet data
            self.process_sheet_data(coinm_positions, btc_price)
            logger.info("Sheet processing completed successfully")
            
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except GoogleSheetsError as e:
            logger.error(f"Google Sheets error: {e}")
            raise
        except APIError as e:
            logger.error(f"API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

def main():
    """Main function"""
    try:
        processor = CashAndCarryProcessor()
        processor.run()
        logger.info("Cash & Carry processor completed successfully")
    except Exception as e:
        logger.error(f"Cash & Carry processor failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()

