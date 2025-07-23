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

def main():
    logging.info("Starting scheduler - Worker server will run every 60 minutes")
    
    # Schedule the job to run every 60 minutes
    schedule.every(60).minutes.do(run_worker_server)
    
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