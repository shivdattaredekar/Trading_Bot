import webbrowser
import time
import requests
import json
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
import hashlib

# Replace these with your app details
CLIENT_ID = "MX3ZI638YI-100"
SECRET_KEY = "2IC9MIKXVJ"
REDIRECT_URI = "http://127.0.0.1:5000/callback"
RESPONSE_TYPE = "code"
GRANT_TYPE = "authorization_code"

# Step 1: Generate auth code URL
def get_auth_code_url():
    return f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=sample_state"

# Step 2: Generate access token
def generate_access_token(auth_code):
    headers = {
        "Content-Type": "application/json"
    }

    appp_sec_id = f'{CLIENT_ID}:{SECRET_KEY}'
    appIdHash = hashlib.sha256(appp_sec_id.encode()).hexdigest()

    payload = {
        "grant_type": "authorization_code",
        "appIdHash": appIdHash,
        "code": auth_code,
        'secret_key':SECRET_KEY,
        'redirect_url': REDIRECT_URI
    }
    response = requests.post('https://api.fyers.in/api/v3/token', headers=headers, json=payload)
    
    # 👇 Add these lines to debug
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)
    try:
        return response.json()["access_token"]
    except Exception as e:
        print("Key 'access_token' not found in response.")
        return None





# Main
if __name__ == "__main__":
    print("Opening Fyers Auth URL...")
    webbrowser.open(get_auth_code_url())
    auth_code = input("Paste the code from redirect URL: ").strip()
    
    print("Generating access token...")
    access_token = generate_access_token(auth_code)

    session = fyersModel.SessionModel()
    session.set_token(access_token)
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=access_token, log_path=".")

   