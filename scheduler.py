import schedule
import time
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_worker_server():
    """Run the main worker server"""
    try:
        logging.info("Starting worker server execution...")
        result = subprocess.run(["python", "main.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"Worker server output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"Worker server stderr:\n{result.stderr}")
            
        logging.info("Worker server execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running worker server: {e}")

def run_db_staking_wallet():
    """Run the db_staking_wallet.py script"""
    try:
        logging.info("Starting db_staking_wallet.py execution...")
        result = subprocess.run(["python", "db_staking_wallet.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"db_staking_wallet.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"db_staking_wallet.py stderr:\n{result.stderr}")
            
        logging.info("db_staking_wallet.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running db_staking_wallet.py: {e}")

def run_staking_wallet_updater():
    """Run the staking_wallet_updater.py script"""
    try:
        logging.info("Starting staking_wallet_updater.py execution...")
        result = subprocess.run(["python", "staking_wallet_updater.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"staking_wallet_updater.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"staking_wallet_updater.py stderr:\n{result.stderr}")
            
        logging.info("staking_wallet_updater.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running staking_wallet_updater.py: {e}")

def main():
    logging.info("Starting scheduler - Worker server will run every 60 minutes")
    logging.info("db_staking_wallet.py and staking_wallet_updater.py will run daily at 23:00 GMT+7")
    
    # Schedule the job to run every 60 minutes
    schedule.every(60).minutes.do(run_worker_server)
    
    # Schedule db_staking_wallet.py and staking_wallet_updater.py to run at 23:00 GMT+7 daily
    schedule.every().day.at("23:00").do(run_db_staking_wallet)
    schedule.every().day.at("23:00").do(run_staking_wallet_updater)
    
    # Run immediately on startup
    logging.info("Running initial execution...")
    run_worker_server()
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for pending jobs
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    main() 