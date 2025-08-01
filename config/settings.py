# config/settings.py
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta

# Fyers API credentials
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")  # You can update this dynamically if needed
GRANT_TYPE = os.getenv("GRANT_TYPE")
RESPONSE_TYPE = os.getenv("RESPONSE_TYPE")

# Strategy parameters
EMA_PERIOD = os.getenv("EMA_PERIOD")
TIMEFRAME = os.getenv("TIMEFRAME")
GAP_UP_THRESHOLD = os.getenv("GAP_UP_THRESHOLD")
MIN_VOLUME = os.getenv("MIN_VOLUME")

# Trading control
MAX_TRADES = os.getenv("MAX_TRADES")
ORDER_QUANTITY = os.getenv("ORDER_QUANTITY")
SIMULATE = os.getenv("SIMULATE")  # If True, don't place real orders

# Time control
ENTRY_TIME = os.getenv("ENTRY_TIME")

# File paths
TRADE_LOG_PATH = os.getenv("TRADE_LOG_PATH")
TOKEN_FILE = os.getenv("TOKEN_FILE")

# Date range for historical data

DATE_FROM = (datetime.now() - timedelta(days=1)).date()
DATE_TO = datetime.now().date()
