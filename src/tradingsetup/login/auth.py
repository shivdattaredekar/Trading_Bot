from fyers_apiv3 import fyersModel
from tradingsetup.config.settings import CLIENT_ID, FYERS_ACCESS_TOKEN
from tradingsetup.utlis.logger import log

# Function to create an authenticated Fyers instance
def get_fyers_instance():
    # Create and return the FyersModel instance
    log("Creating FyersModel instance with access token...")

    try:
        access_token = FYERS_ACCESS_TOKEN 
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=access_token, log_path=None)
        log("Authenticated Fyers instance created.")
        return fyers
    except Exception as e:
        log(f"Error creating Fyers instance: {e}")
        raise RuntimeError("Failed to create Fyers instance. Please check your credentials and network connection.")