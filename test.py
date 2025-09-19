import json
import requests
import pyotp
import hashlib
from urllib import parse
import sys
#from src.tradingsetup.config.settings import (CLIENT_ID,PIN,SECRET_KEY,)


# This script will only work if TOTP is enabled. 
# You can enable TOTP using this link: https://myaccount.fyers.in/ManageAccount >> External 2FA TOTP >> click on "Enable".

# Client Information (ENTER YOUR OWN INFO HERE! Data varies from users and app types)
CLIENT_ID = "XR04750"       # Your Fyers Client ID
PIN = "1995"               # User pin for Fyers account
APP_ID = "MX3ZI638YI"        # App ID from MyAPI dashboard (https://myapi.fyers.in/dashboard). The format is appId-appType. 
# Example: YIXXXXXSE-100. In this code, YIXXXXXSE is the APP_ID and 100 is the APP_TYPE
APP_TYPE = "100"
APP_SECRET = "2IC9MIKXVJ"   # App Secret from myapi dashboard (https://myapi.fyers.in/dashboard)
TOTP_SECRET_KEY = "Z4SMDAFYBQA6QMMNKC6KPFVFDENDTFHH"  # TOTP secret key, copy the secret while enabling TOTP.

REDIRECT_URI = "http://127.0.0.1:5000/callback"  # Redirect URL from the app

# NOTE: Do not share these secrets with anyone.


# API endpoints
BASE_URL = "https://api-t2.fyers.in/vagator/v2"
BASE_URL_2 = "https://api-t1.fyers.in/api/v3"
URL_VERIFY_CLIENT_ID = BASE_URL + "/send_login_otp"
URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
URL_VERIFY_PIN = BASE_URL + "/verify_pin"
URL_TOKEN = BASE_URL_2 + "/token"
URL_VALIDATE_AUTH_CODE = BASE_URL_2 + "/validate-authcode"

SUCCESS = 1
ERROR = -1

def verify_client_id(client_id):
    try:
        payload = {
            "fy_id": client_id,
            "app_id": "2"
        }

        result_string = requests.post(url=URL_VERIFY_CLIENT_ID, json=payload)
        # print("result_string : ", result_string.text)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        request_key = result["request_key"]

        return [SUCCESS, request_key]
    
    except Exception as e:
        return [ERROR, e]
    

def generate_totp(secret):
    try:
        generated_totp = pyotp.TOTP(secret).now()
        return [SUCCESS, generated_totp]
    
    except Exception as e:
        return [ERROR, e]


def verify_totp(request_key, totp):
    try:
        payload = {
            "request_key": request_key,
            "otp": totp
        }

        result_string = requests.post(url=URL_VERIFY_TOTP, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        request_key = result["request_key"]

        return [SUCCESS, request_key]
    
    except Exception as e:
        return [ERROR, e]


def verify_PIN(request_key, pin):
    try:
        payload = {
            "request_key": request_key,
            "identity_type": "pin",
            "identifier": pin
        }

        result_string = requests.post(url=URL_VERIFY_PIN, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]
    
        result = json.loads(result_string.text)
        access_token = result["data"]["access_token"]

        return [SUCCESS, access_token]
    
    except Exception as e:
        return [ERROR, e]


def token(client_id, app_id, redirect_uri, app_type, access_token):
    try:
        payload = {
            "fyers_id": client_id,
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "appType": app_type,
            "code_challenge": "",
            "state": "sample_state",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True
        }
        headers={'Authorization': f'Bearer {access_token}'}

        result_string = requests.post(
            url=URL_TOKEN, json=payload, headers=headers
        )

        if result_string.status_code != 308:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        url = result["Url"]
        auth_code = parse.parse_qs(parse.urlparse(url).query)['auth_code'][0]

        return [SUCCESS, auth_code]
    
    except Exception as e:
        return [ERROR, e]


def sha256_hash(appId, appType, appSecret):
    message = f"{appId}-{appType}:{appSecret}"
    message = message.encode()
    sha256_hash = hashlib.sha256(message).hexdigest()
    return sha256_hash


def validate_authcode(auth_code):
    try:
        app_id_hash = sha256_hash(appId=APP_ID, appType=APP_TYPE, appSecret=APP_SECRET)
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code,
        }

        result_string = requests.post(url=URL_VALIDATE_AUTH_CODE, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        access_token = result["access_token"]

        return [SUCCESS, access_token]
    
    except Exception as e:
        return [ERROR, e]


def main():
    # Step 1 - Retrieve request_key from verify_client_id Function
    verify_client_id_result = verify_client_id(client_id=CLIENT_ID)
    if verify_client_id_result[0] != SUCCESS:
        print(f"verify_client_id failure - {verify_client_id_result[1]}")
        sys.exit()
    else:
        print("verify_client_id success")

    # Step 2 - Generate totp
    generate_totp_result = generate_totp(secret=TOTP_SECRET_KEY)
    if generate_totp_result[0] != SUCCESS:
        print(f"generate_totp failure - {generate_totp_result[1]}")
        sys.exit()
    else:
        print("generate_totp success")

    # Step 3 - Verify totp and get request key from verify_totp Function.
    request_key = verify_client_id_result[1]
    totp = generate_totp_result[1]
    verify_totp_result = verify_totp(request_key=request_key, totp=totp)
    if verify_totp_result[0] != SUCCESS:
        print(f"verify_totp_result failure - {verify_totp_result[1]}")
        sys.exit()
    else:
        print("verify_totp_result success")
    
    # Step 4 - Verify pin and send back access token
    request_key_2 = verify_totp_result[1]
    verify_pin_result = verify_PIN(request_key=request_key_2, pin=PIN)
    if verify_pin_result[0] != SUCCESS:
        print(f"verify_pin_result failure - {verify_pin_result[1]}")
        sys.exit()
    else:
        print("verify_pin_result success")
    
    # Step 5 - Get auth code for API V3 App from trade access token
    token_result = token(
        client_id=CLIENT_ID, app_id=APP_ID, redirect_uri=REDIRECT_URI, app_type=APP_TYPE,
        access_token=verify_pin_result[1]
    )
    if token_result[0] != SUCCESS:
        print(f"token_result failure - {token_result[1]}")
        sys.exit()
    else:
        print("token_result success")

    # Step 6 - Get API V3 access token from validating auth code
    auth_code = token_result[1]
    validate_authcode_result = validate_authcode(auth_code=auth_code)
    if token_result[0] != SUCCESS:
        print(f"validate_authcode failure - {validate_authcode_result[1]}")
        sys.exit()
    else:
        print("validate_authcode success")
    
    access_token = APP_ID + "-" + APP_TYPE + ":" + validate_authcode_result[1]

    print(f"\naccess_token - {access_token}\n")

if __name__ == "__main__":
    main()





"""
import os

from src.tradingsetup.config.settings import FYERS_ACCESS_TOKEN, FYERS_REFRESH_TOKEN


import os
import time
import webbrowser
from threading import Thread
from flask import Flask, request
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

from src.tradingsetup.config.settings import (
    CLIENT_ID, SECRET_KEY, REDIRECT_URI, RESPONSE_TYPE, GRANT_TYPE, FYERS_ACCESS_TOKEN,
    FYERS_REFRESH_TOKEN
) 
from src.tradingsetup.utlis.logger import log

REFRESH_TOKEN_VALIDITY_DAYS = 15
GRACE_PERIOD_DAYS = 1

import requests
import json
from src.tradingsetup.config.settings import APP_URL, GRANT_TYPE2, PIN, REFRESH_TOKEN, CLIENT_ID, SECRET_KEY, APP_URL_V2
import hashlib  

url = APP_URL
input_string = f"{CLIENT_ID}:{SECRET_KEY}"
appidhash = hashlib.sha256(input_string.encode()).hexdigest()

from flask import Flask, request
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, Request
from threading import Thread


app = FastAPI()
auth_code_container = {"auth_code": None}

@app.get("/callback")
async def callback(request: Request):
    auth_code = request.query_params.get("auth_code")
    auth_code_container["auth_code"] = auth_code
    print(f"[DEBUG] Auth code received: {auth_code}")
    return {"message": "Auth code received successfully. You can close this tab."}

def run_fastapi():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")


def auto_login(self):
    log("Manual login flow started.")

    # Start FastAPI in a separate thread
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    time.sleep(2)  # Give the server a moment to start

    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        response_type=RESPONSE_TYPE,
        state="sample",
        secret_key=SECRET_KEY,
        grant_type=GRANT_TYPE
    )

    login_url = session.generate_authcode()
    log(f"Opening browser for login at {login_url}")
    webbrowser.open(login_url, new=1)

    # Wait for auth code to be captured
    while auth_code_container["auth_code"] is None:
        time.sleep(1)

    auth_code = auth_code_container["auth_code"]
    session.set_token(auth_code)
    response = session.generate_token()

    if "access_token" in response and "refresh_token" in response:
        set_key(self.env_path, "FYERS_ACCESS_TOKEN", response["access_token"])
        set_key(self.env_path, "FYERS_REFRESH_TOKEN", response["refresh_token"])
        set_key(self.env_path, "REFRESH_TOKEN_ISSUE_TIMESTAMP", str(int(time.time())))
        log("Manual login successful; tokens saved.")
    else:
        log("Failed to get tokens:", response)
        exit(1)

"""

"""
class AuthManager:
    def __init__(self, env_path=".env"):
        load_dotenv(env_path)
        self.env_path = env_path
        self.auth_code = None

    def _is_refresh_token_expiring_soon(self):
        issue_timestamp = os.getenv("REFRESH_TOKEN_ISSUE_TIMESTAMP")
        if not issue_timestamp:
            return True  # No timestamp means we should do manual login

        issue_time = int(issue_timestamp)
        current_time = int(time.time())
        elapsed_days = (current_time - issue_time) / (24 * 3600)

        if elapsed_days >= (REFRESH_TOKEN_VALIDITY_DAYS - GRACE_PERIOD_DAYS):
            log(f"Refresh token is expiring soon or already expired (age: {elapsed_days:.2f} days). Manual login needed.")
            log("Refresh token expiring soon. Manual re-login recommended.")
            return True
        return False

    def refresh_access_token(self):
        if self._is_refresh_token_expiring_soon():
            return False  # Force manual login

        refresh_token = FYERS_REFRESH_TOKEN
        if not refresh_token:
            log("No refresh token found, manual login required.")
            return False

        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            secret_key=SECRET_KEY,
            grant_type="refresh_token",
            redirect_uri=REDIRECT_URI,
            response_type="code",
            state="sample"
        )
        session.set_token(refresh_token)
        response = session.generate_token()

        if "access_token" in response and "refresh_token" in response:
            set_key(self.env_path, "FYERS_ACCESS_TOKEN", response["access_token"])
            set_key(self.env_path, "FYERS_REFRESH_TOKEN", response["refresh_token"])
            set_key(self.env_path, "REFRESH_TOKEN_ISSUE_TIMESTAMP", str(int(time.time())))
            log("Access & refresh tokens refreshed and saved.")
            log("Tokens refreshed successfully.")
            return True

        log("Failed to refresh tokens:")
        print("Failed to refresh tokens:", response)
        return False

    def is_token_valid(self):
        token = FYERS_ACCESS_TOKEN
        if not token:
            return False

        try:
            fyers = fyersModel.FyersModel(
                client_id=CLIENT_ID,
                token=token,
                log_path=""
            )
            response = fyers.get_profile()
            if "s" in response and response["s"] == "ok":
                return True
            log("Token invalid, trying to refresh...")
            return self.refresh_access_token()
        except Exception:
            return self.refresh_access_token()

    def auto_login(self):
        if self.is_token_valid():
            log("Token valid, skipping login.")
            return

        log("Manual login flow started.")

        app = Flask(__name__)

        @app.route("/callback")
        def callback():
            self.auth_code = request.args.get("auth_code")
            return "Auth code received. Close this tab."

        def run_flask():
            app.run(port=5000)

        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)

        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            response_type=RESPONSE_TYPE,
            state="sample",
            secret_key=SECRET_KEY,
            grant_type=GRANT_TYPE
        )

        login_url = session.generate_authcode()
        log("Opening browser for login...")
        webbrowser.open(login_url, new=1)

        while self.auth_code is None:
            time.sleep(1)

        session.set_token(self.auth_code)
        response = session.generate_token()

        if "access_token" in response and "refresh_token" in response:
            set_key(self.env_path, "FYERS_ACCESS_TOKEN", response["access_token"])
            set_key(self.env_path, "FYERS_REFRESH_TOKEN", response["refresh_token"])
            set_key(self.env_path, "REFRESH_TOKEN_ISSUE_TIMESTAMP", str(int(time.time())))
            log("Manual login successful; tokens saved.")
            log("Manual login successful.")
        else:
            log("Failed to get tokens:", response)
            log(f"Authentication failed: {response}")
            exit(1)



a = AuthManager()

a.refresh_access_token()



"""






"""import requests
import json
from src.tradingsetup.config.settings import APP_URL, GRANT_TYPE2, PIN, REFRESH_TOKEN, CLIENT_ID, SECRET_KEY, APP_URL_V2
import hashlib  

url = APP_URL
input_string = f"{CLIENT_ID}:{SECRET_KEY}"
appidhash = hashlib.sha256(input_string.encode()).hexdigest()


print("APP_URL:", url, type(url))
print("GRANT_TYPE2:", GRANT_TYPE2, type(GRANT_TYPE2))
print("PIN:", PIN, type(PIN))
print("REFRESH_TOKEN:", REFRESH_TOKEN, type(REFRESH_TOKEN))
print("CLIENT_ID:", CLIENT_ID, type(CLIENT_ID))
print("SECRET_KEY:", SECRET_KEY, type(SECRET_KEY))
print("appidhash", appidhash, type(appidhash))



headers = {
    "Content-Type": "application/json"
}

payload = {
    "grant_type": GRANT_TYPE2,
    "appIdHash": appidhash,
    "refresh_token": REFRESH_TOKEN,
    "pin": PIN
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
except Exception as e:
    print(e)

# Print the response
print("Status Code:", response.status_code)
print("Response JSON:", response.json())"""