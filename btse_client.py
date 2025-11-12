import os
import time
import hmac
import hashlib
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTSEError(Exception):
    """Custom exception for BTSE API errors"""
    pass

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

class BTSEClient:
    """BTSE API client for fetching earn/invest data"""
    
    def __init__(self):
        self.api_key = None
        self.api_secret = None
        self.base_url = 'https://api.btse.com/spot'
        
    def load_environment(self) -> None:
        """Load and validate environment variables"""
        try:
            load_dotenv()
            
            # Load BTSE API credentials
            self.api_key = os.getenv("BTSE_API_KEY")
            self.api_secret = os.getenv("BTSE_SECRET_KEY")
            
            if not self.api_key or not self.api_secret:
                raise ConfigError(
                    f"Missing BTSE API credentials. "
                    f"BTSE_API_KEY: {'Set' if self.api_key else 'NOT SET'}, "
                    f"BTSE_API_SECRET: {'Set' if self.api_secret else 'NOT SET'}"
                )
                
            logger.info("BTSE API credentials loaded successfully")
                
        except Exception as e:
            logger.error(f"Failed to load environment: {e}")
            raise
    
    def _generate_signature(self, method: str, endpoint: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> tuple:
        """Generate HMAC signature for BTSE API authentication"""
        try:
            nonce = str(int(time.time() * 1000))
            
            # For BTSE API, the signature format is: endpoint + nonce + body
            message = endpoint + nonce
            
            if body:
                message += json.dumps(body, separators=(',', ':'))
            
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha384
            ).hexdigest()
            
            return nonce, signature
        except Exception as e:
            logger.error(f"Error generating signature: {e}")
            raise BTSEError(f"Failed to generate signature: {e}")
    
    def _get_headers(self, method: str, endpoint: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict[str, str]:
        """Generate headers for BTSE API requests"""
        try:
            nonce, signature = self._generate_signature(method, endpoint, params, body)
            
            headers = {
                'request-api': self.api_key,
                'request-nonce': nonce,
                'request-sign': signature,
                'Content-Type': 'application/json'
            }
            return headers
        except Exception as e:
            logger.error(f"Error generating headers: {e}")
            raise BTSEError(f"Failed to generate headers: {e}")
    
    def _make_request(self, url: str, endpoint: str, method: str = 'GET', params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to BTSE API"""
        try:
            headers = self._get_headers(method, endpoint, params, data)
            
            # Log response details
            logger.info(f"API Request: {method} {url}")
            if params:
                logger.info(f"Params: {params}")
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise BTSEError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise BTSEError(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise BTSEError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise BTSEError(f"Failed to parse response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise BTSEError(f"Unexpected error: {e}")
    
    def get_earn_products(self) -> List[Dict[str, Any]]:
        """Fetch available earn products from BTSE"""
        try:
            endpoint = '/api/v3.3/invest/products'
            url = self.base_url + endpoint
            
            logger.info("Fetching earn products...")
            response = self._make_request(url, endpoint)
            
            if isinstance(response, list):
                products = response
            elif isinstance(response, dict) and 'data' in response:
                products = response['data']
            else:
                products = [response] if response else []
            
            logger.info(f"Successfully fetched {len(products)} earn products")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching earn products: {e}")
            raise
    
    def get_earn_positions(self) -> List[Dict[str, Any]]:
        """Fetch user's earn positions/investments"""
        try:
            # Try multiple possible endpoints for positions
            endpoints_to_try = [
                '/api/v3.3/invest/orders',
                '/api/v3.3/invest/positions', 
                '/api/v3.3/invest/active',
                '/api/v3.3/invest/current'
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    url = self.base_url + endpoint
                    logger.info(f"Trying endpoint: {endpoint}")
                    response = self._make_request(url, endpoint)
                    
                    if isinstance(response, list):
                        positions = response
                    elif isinstance(response, dict) and 'data' in response:
                        positions = response['data']
                    else:
                        positions = [response] if response else []
                    
                    logger.info(f"Successfully fetched {len(positions)} earn positions from {endpoint}")
                    return positions
                    
                except BTSEError as e:
                    if "not allowed for current API Key" in str(e):
                        logger.warning(f"API key lacks permissions for {endpoint}")
                        continue
                    else:
                        raise
            
            # If all endpoints failed due to permissions
            logger.warning("All position endpoints require additional API key permissions")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching earn positions: {e}")
            raise
    
    def get_earn_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch user's earn transaction history"""
        try:
            endpoint = '/api/v3.3/invest/history'
            url = self.base_url + endpoint
            params = {'limit': limit}
            
            logger.info(f"Fetching earn history (limit: {limit})...")
            response = self._make_request(url, endpoint, params=params)
            
            if isinstance(response, list):
                history = response
            elif isinstance(response, dict) and 'data' in response:
                history = response['data']
            else:
                history = [response] if response else []
            
            logger.info(f"Successfully fetched {len(history)} earn history records")
            return history
            
        except Exception as e:
            logger.error(f"Error fetching earn history: {e}")
            raise
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Fetch account balance information"""
        try:
            endpoint = '/api/v3.3/user/account'
            url = self.base_url + endpoint
            
            logger.info("Fetching account balance...")
            response = self._make_request(url, endpoint)
            
            logger.info("Successfully fetched account balance")
            return response
            
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            raise
    
    def check_api_permissions(self) -> Dict[str, bool]:
        """Check what endpoints your API key has access to"""
        permissions = {
            'products': False,
            'positions': False,
            'history': False,
            'account': False
        }
        
        # Test products endpoint
        try:
            self.get_earn_products()
            permissions['products'] = True
            logger.info("✅ API key has access to products endpoint")
        except Exception as e:
            logger.warning(f"❌ API key lacks access to products endpoint: {e}")
        
        # Test positions endpoint
        try:
            positions = self.get_earn_positions()
            if positions is not None:
                permissions['positions'] = True
                logger.info("✅ API key has access to positions endpoint")
        except Exception as e:
            logger.warning(f"❌ API key lacks access to positions endpoint: {e}")
        
        # Test history endpoint
        try:
            self.get_earn_history(limit=1)
            permissions['history'] = True
            logger.info("✅ API key has access to history endpoint")
        except Exception as e:
            logger.warning(f"❌ API key lacks access to history endpoint: {e}")
        
        # Test account endpoint
        try:
            self.get_account_balance()
            permissions['account'] = True
            logger.info("✅ API key has access to account endpoint")
        except Exception as e:
            logger.warning(f"❌ API key lacks access to account endpoint: {e}")
        
        return permissions
    
    def get_all_earn_data(self) -> Dict[str, Any]:
        """Fetch all earn-related data in one call"""
        try:
            logger.info("Fetching all earn data...")
            
            data = {
                'products': self.get_earn_products(),
                'timestamp': time.time()
            }
            
            # Try to fetch user-specific data, but don't fail if permissions are insufficient
            try:
                data['positions'] = self.get_earn_positions()
            except BTSEError as e:
                if "not allowed for current API Key" in str(e):
                    logger.warning("API key lacks permissions for positions endpoint")
                    data['positions'] = []
                else:
                    raise
            
            try:
                data['history'] = self.get_earn_history()
            except BTSEError as e:
                if "not allowed for current API Key" in str(e):
                    logger.warning("API key lacks permissions for history endpoint")
                    data['history'] = []
                else:
                    raise
            
            try:
                data['account_balance'] = self.get_account_balance()
            except BTSEError as e:
                if "not allowed for current API Key" in str(e) or "404" in str(e):
                    logger.warning("API key lacks permissions for account balance endpoint or endpoint not found")
                    data['account_balance'] = {}
                else:
                    raise
            
            logger.info("Successfully fetched all available earn data")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching all earn data: {e}")
            raise

def test_btse_client():
    """Test function to verify BTSE client functionality"""
    try:
        # Initialize client
        client = BTSEClient()
        client.load_environment()
        
        print("=" * 50)
        print("BTSE Client Test")
        print("=" * 50)
        
        # Test earn products
        print("\n1. Testing earn products...")
        products = client.get_earn_products()
        print(f"Found {len(products)} earn products")
        if products:
            print("Sample product:", json.dumps(products[0], indent=2))
        
        # Test earn positions
        print("\n2. Testing earn positions...")
        positions = client.get_earn_positions()
        print(f"Found {len(positions)} earn positions")
        if positions:
            print("Sample position:", json.dumps(positions[0], indent=2))
        
        # Test earn history
        print("\n3. Testing earn history...")
        history = client.get_earn_history(limit=5)
        print(f"Found {len(history)} history records")
        if history:
            print("Sample history record:", json.dumps(history[0], indent=2))
        
        # Test account balance
        print("\n4. Testing account balance...")
        balance = client.get_account_balance()
        print("Account balance:", json.dumps(balance, indent=2))
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"Test failed: {e}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_btse_client()
