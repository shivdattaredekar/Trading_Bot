import logging
import os
import sys
from datetime import datetime

# Ensure stdout uses UTF-8 encoding
#sys.stdout.reconfigure(encoding='utf-8')

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure the logger
log_file = f"logs/run_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # ✅ FIXED HERE
        logging.StreamHandler(sys.stdout)
    ]
)

def log(message, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    elif level == "debug":
        logging.debug(message)
    else:
        logging.info(message)
