import schedule
import time
import subprocess
import logging
from datetime import datetime, timezone, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def get_gmt_plus_7_time():
    """Get current time in GMT+7"""
    utc_now = datetime.now(timezone.utc)
    gmt_plus_7 = utc_now + timedelta(hours=7)
    return gmt_plus_7

def get_local_time_for_gmt_plus_7(gmt_plus_7_hour, gmt_plus_7_minute=0):
    """Convert GMT+7 time to local time for scheduling"""
    # Get current GMT+7 time
    gmt_plus_7_now = get_gmt_plus_7_time()
    
    # Create target time in GMT+7
    target_gmt_plus_7 = gmt_plus_7_now.replace(
        hour=gmt_plus_7_hour, 
        minute=gmt_plus_7_minute, 
        second=0, 
        microsecond=0
    )
    
    # Convert to local time
    local_time = target_gmt_plus_7 - timedelta(hours=7)
    return local_time.strftime("%H:%M")

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

def run_db_deposit_withdraw_history():
    """Run the db_deposit_withdraw_history.py script"""
    try:
        logging.info("Starting db_deposit_withdraw_history.py execution...")
        result = subprocess.run(["python", "db_deposit_withdraw_history.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"db_deposit_withdraw_history.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"db_deposit_withdraw_history.py stderr:\n{result.stderr}")
            
        logging.info("db_deposit_withdraw_history.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running db_deposit_withdraw_history.py: {e}")

def run_deposit_withdraw_sheet_updater():
    """Run the deposit_withdraw_sheet_updater.py script"""
    try:
        logging.info("Starting deposit_withdraw_sheet_updater.py execution...")
        result = subprocess.run(["python", "deposit_withdraw_sheet_updater.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"deposit_withdraw_sheet_updater.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"deposit_withdraw_sheet_updater.py stderr:\n{result.stderr}")
            
        logging.info("deposit_withdraw_sheet_updater.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running deposit_withdraw_sheet_updater.py: {e}")

def main():
    # Calculate local time equivalent to 23:00 GMT+7
    local_time_23_00_gmt7 = get_local_time_for_gmt_plus_7(23, 0)
    
    logging.info("Starting scheduler - Worker server will run every 60 minutes")
    logging.info(f"All scripts will run daily at 23:00 GMT+7 (which is {local_time_23_00_gmt7} local time)")
    
    # Schedule the job to run every 60 minutes
    schedule.every(60).minutes.do(run_worker_server)
    
    # Schedule all scripts to run at 23:00 GMT+7 (converted to local time)
    schedule.every(60 * 24).minutes.do(run_db_staking_wallet)
    schedule.every(60 * 24).minutes.do(run_staking_wallet_updater)
    schedule.every(60 * 24).minutes.do(run_db_deposit_withdraw_history)
    schedule.every(60 * 24).minutes.do(run_deposit_withdraw_sheet_updater)

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