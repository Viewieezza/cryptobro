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

def run_alp_price_scraper():
    """Run the alp_price_scraper.py script"""
    try:
        logging.info("Starting alp_price_scraper.py execution...")
        result = subprocess.run(["python", "alp_price_scraper.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"alp_price_scraper.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"alp_price_scraper.py stderr:\n{result.stderr}")
            
        logging.info("alp_price_scraper.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running alp_price_scraper.py: {e}")

def run_edgex_google_sheet():
    """Run the edgex_google_sheet.py script"""
    try:
        logging.info("Starting edgex_google_sheet.py execution...")
        result = subprocess.run(["python", "edgex_google_sheet.py"], capture_output=True, text=True)
        
        if result.stdout:
            logging.info(f"edgex_google_sheet.py output:\n{result.stdout}")
        
        if result.stderr:
            logging.warning(f"edgex_google_sheet.py stderr:\n{result.stderr}")
            
        logging.info("edgex_google_sheet.py execution completed successfully")
        
    except Exception as e:
        logging.error(f"Error running edgex_google_sheet.py: {e}")

def run_update_llp_sheet():
    """Run the update_llp_sheet.py script"""
    try:
        logging.info("Starting update_llp_sheet.py execution...")
        result = subprocess.run(["python", "update_llp_sheet.py"], capture_output=True, text=True)

        if result.stdout:
            logging.info(f"update_llp_sheet.py output:\n{result.stdout}")

        if result.stderr:
            logging.warning(f"update_llp_sheet.py stderr:\n{result.stderr}")

        logging.info("update_llp_sheet.py execution completed successfully")

    except Exception as e:
        logging.error(f"Error running update_llp_sheet.py: {e}")


def run_update_worldlib_sheet():
    """Run the update_worldlib_sheet.py script (WLFI → Google Sheet Worldlib)"""
    try:
        logging.info("Starting update_worldlib_sheet.py execution...")
        result = subprocess.run(["python", "update_worldlib_sheet.py"], capture_output=True, text=True)
        if result.stdout:
            logging.info(f"update_worldlib_sheet.py output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"update_worldlib_sheet.py stderr:\n{result.stderr}")
        logging.info("update_worldlib_sheet.py execution completed successfully")
    except Exception as e:
        logging.error(f"Error running update_worldlib_sheet.py: {e}")


def run_update_sky_money_sheet():
    """Run the update_sky_money_sheet.py script (Sky Money stUSDT → Google Sheet 'Sky Money')"""
    try:
        logging.info("Starting update_sky_money_sheet.py execution...")
        result = subprocess.run(["python", "update_sky_money_sheet.py"], capture_output=True, text=True)
        if result.stdout:
            logging.info(f"update_sky_money_sheet.py output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"update_sky_money_sheet.py stderr:\n{result.stderr}")
        logging.info("update_sky_money_sheet.py execution completed successfully")
    except Exception as e:
        logging.error(f"Error running update_sky_money_sheet.py: {e}")


def run_update_morpho_sheet():
    """Run the update_morpho_sheet.py script (Morpho → Google Sheet 'Morpho'). Writes only A–D and F; does not touch E, G–K."""
    try:
        logging.info("Starting update_morpho_sheet.py execution...")
        result = subprocess.run(["python", "update_morpho_sheet.py"], capture_output=True, text=True)
        if result.stdout:
            logging.info(f"update_morpho_sheet.py output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"update_morpho_sheet.py stderr:\n{result.stderr}")
        logging.info("update_morpho_sheet.py execution completed successfully")
    except Exception as e:
        logging.error(f"Error running update_morpho_sheet.py: {e}")


def run_update_gs_sheet():
    """Run the update_gs_sheet.py script (GS → Google Sheet worksheet 'nvodyo8iy'). เริ่มเที่ยงคืน GMT+7. Writes only A–D and F."""
    try:
        logging.info("Starting update_gs_sheet.py execution...")
        result = subprocess.run(["python", "update_gs_sheet.py"], capture_output=True, text=True)
        if result.stdout:
            logging.info(f"update_gs_sheet.py output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"update_gs_sheet.py stderr:\n{result.stderr}")
        logging.info("update_gs_sheet.py execution completed successfully")
    except Exception as e:
        logging.error(f"Error running update_gs_sheet.py: {e}")


def main():
    # Calculate local time equivalent to 23:00 GMT+7
    local_time_23_00_gmt7 = get_local_time_for_gmt_plus_7(23, 0)

    # Calculate local time equivalent to 08:00 GMT+7
    local_time_08_00_gmt7 = get_local_time_for_gmt_plus_7(8, 0)
    
    # Calculate local time equivalent to 00:00 GMT+7
    local_time_00_00_gmt7 = get_local_time_for_gmt_plus_7(0, 0)
    
    # Calculate local time equivalent to 05:00 GMT+7 (ตี 5)
    local_time_05_00_gmt7 = get_local_time_for_gmt_plus_7(5, 0)
    # 06:00 GMT+7 สำหรับ Worldlib sheet
    local_time_06_00_gmt7 = get_local_time_for_gmt_plus_7(6, 0)

    logging.info("Starting scheduler - Worker server will run every 60 minutes")
    logging.info(f"All scripts will run daily at 23:00 GMT+7 (which is {local_time_23_00_gmt7} local time)")
    logging.info(f"ALP price scraper and EdgeX Google Sheet will run daily at 00:00 GMT+7 (which is {local_time_00_00_gmt7} local time)")
    logging.info(f"update_llp_sheet.py will run daily at 05:00 GMT+7 (which is {local_time_05_00_gmt7} local time)")
    logging.info(f"update_worldlib_sheet.py will run daily at 08:00 GMT+7 (which is {local_time_08_00_gmt7} local time)")
    logging.info(f"update_sky_money_sheet.py will run daily at 00:00 GMT+7 (which is {local_time_00_00_gmt7} local time)")
    logging.info(f"update_morpho_sheet.py will run daily at 00:00 GMT+7 (which is {local_time_00_00_gmt7} local time)")
    logging.info(f"update_gs_sheet.py (nvodyo8iy) will run daily at 00:00 GMT+7 (which is {local_time_00_00_gmt7} local time)")
    
    # Schedule the job to run every 60 minutes
    schedule.every(60).minutes.do(run_worker_server)
    
    # Schedule all scripts to run at 23:00 GMT+7 (converted to local time)
    schedule.every().day.at(local_time_23_00_gmt7).do(run_db_staking_wallet)
    schedule.every().day.at(local_time_23_00_gmt7).do(run_staking_wallet_updater)
    schedule.every().day.at(local_time_23_00_gmt7).do(run_db_deposit_withdraw_history)
    schedule.every().day.at(local_time_23_00_gmt7).do(run_deposit_withdraw_sheet_updater)
    
    # Schedule ALP price scraper to run daily at 00:00 GMT+7
    schedule.every().day.at(local_time_00_00_gmt7).do(run_alp_price_scraper)
    # Schedule Sky Money stUSDT sheet update to run daily at 00:00 GMT+7
    schedule.every().day.at(local_time_00_00_gmt7).do(run_update_sky_money_sheet)
    # Schedule Morpho sheet update at 00:00 GMT+7 (only A–D and F; does not touch other columns)
    schedule.every().day.at(local_time_00_00_gmt7).do(run_update_morpho_sheet)
    # Schedule GS → sheet nvodyo8iy เริ่มเที่ยงคืน GMT+7 (only A–D and F)
    schedule.every().day.at(local_time_00_00_gmt7).do(run_update_gs_sheet)
    
    # Schedule EdgeX Google Sheet to run daily at 08:00 GMT+7
    schedule.every().day.at(local_time_08_00_gmt7).do(run_edgex_google_sheet)
    
    # Schedule update_llp_sheet.py to run daily at 05:00 GMT+7 (ตี 5)
    schedule.every().day.at(local_time_05_00_gmt7).do(run_update_llp_sheet)
    # Schedule WLFI → Worldlib sheet รายวัน 05:00 GMT+7
    schedule.every().day.at(local_time_08_00_gmt7).do(run_update_worldlib_sheet)

    # Run immediately on startup
    logging.info("Running initial execution...")
    run_worker_server()
    run_alp_price_scraper()
    run_edgex_google_sheet()
    
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