import schedule
import time
import subprocess
import logging
import sys
import argparse
import traceback
from datetime import datetime

# ==========================================
# 1. LOGGING CONFIGURATION
# ==========================================
# Configured to log both to the console and to rms_scheduler.log
log_formatter = logging.Formatter('%(asctime)s\n%(message)s\n', datefmt='%Y-%m-%d %H:%M')
logger = logging.getLogger("RMSScheduler")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("rms_scheduler.log", mode='a')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# ==========================================
# 2. JOB DEFINITION
# ==========================================
def run_rms_job():
    logger.info("Hotel RMS Started")
    
    try:
        # sys.executable ensures it uses the same Python environment running the scheduler
        # UPDATED: Changed 'rms.py' to your new filename 'rms (Garden Pod).py'
        result = subprocess.run(
            [sys.executable, "hotel rms.py"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info("Hotel RMS Finished Successfully")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"ERROR: RMS execution failed with return code {e.returncode}\n"
        error_msg += f"Standard Output:\n{e.stdout}\n"
        error_msg += f"Standard Error:\n{e.stderr}"
        logger.error(error_msg)
        
    except Exception as e:
        error_msg = "ERROR: An unexpected exception occurred.\n"
        error_msg += traceback.format_exc()
        logger.error(error_msg)

# ==========================================
# 3. MAIN SCHEDULER LOOP
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="RMS Unattended Automated Scheduler")
    parser.add_argument("--run-now", action="store_true", help="Execute the RMS script immediately, then begin scheduling.")
    args = parser.parse_args()

    if args.run_now:
        print("🚀 '--run-now' flag detected. Executing initial run...")
        run_rms_job()

    # Schedule the job daily at 06:00 AM Singapore time
    # Note: 'Asia/Singapore' timezone requires schedule >= 1.2.0
    try:
        schedule.every().day.at("06:00", "Asia/Singapore").do(run_rms_job)
        print("✅ Scheduled RMS to run daily at 06:00 AM (Asia/Singapore).")
    except schedule.ScheduleValueError:
        # Fallback if timezone parsing fails (e.g., older schedule version)
        print("⚠️ Timezone parsing failed. Defaulting to local system time. Please ensure system time is GMT+8.")
        schedule.every().day.at("06:00").do(run_rms_job)

    print("⏳ Scheduler is now running in the background. Press Ctrl+C to exit.")

    # Infinite loop to keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every 60 seconds to save CPU cycles

if __name__ == "__main__":
    main()