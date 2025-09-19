from fyers_apiv3 import fyersModel
from tradingsetup.config.settings import CLIENT_ID, FYERS_ACCESS_TOKEN
from tradingsetup.utlis.logger import log


# Check if the Access token is valid or not

def is_access_token_valid():
    # Create a FyersModel instance with the provided credentials
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FYERS_ACCESS_TOKEN, log_path=None)

    # Check if the access token is valid
    response = fyers.get_profile()
    if response['code'] == 200:
        log("Access token is valid.")
        return True
    else:
        log("Access token is not valid.")
        return False


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