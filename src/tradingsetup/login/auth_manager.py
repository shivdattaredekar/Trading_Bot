import os
import time
import webbrowser
import hashlib
import requests
import json
from threading import Thread
from flask import Flask, request
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

from src.tradingsetup.config.settings import (
    CLIENT_ID, SECRET_KEY, REDIRECT_URI, RESPONSE_TYPE, GRANT_TYPE, FYERS_ACCESS_TOKEN,
    FYERS_REFRESH_TOKEN, APP_URL, GRANT_TYPE2, PIN, APP_URL_V2
) 
from src.tradingsetup.utlis.logger import log

REFRESH_TOKEN_VALIDITY_DAYS = 15
GRACE_PERIOD_DAYS = 1

class AuthManager:
    def __init__(self, env_path=".env"):
        load_dotenv(env_path)
        self.env_path = env_path
        self.auth_code = None
        self.client_id = CLIENT_ID
        self.url = APP_URL
        self.secret_key = SECRET_KEY
        self.pin = PIN

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
        input_string = f"{self.client_id}:{self.secret_key}"
        appidhash = hashlib.sha256(input_string.encode()).hexdigest()

        if self._is_refresh_token_expiring_soon():
            return False  # Force manual login

        refresh_token = FYERS_REFRESH_TOKEN
        if not refresh_token:
            log("No refresh token found, manual login required.")
            return False

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "grant_type": 'refresh_token',
            "appIdHash": appidhash,
            "refresh_token": refresh_token,
            "pin": self.pin
        }

        try:
            response = requests.post(self.url, headers=headers, data=json.dumps(payload))
        except Exception as e:
            print(e)


        if "access_token" in response:
            set_key(self.env_path, "FYERS_ACCESS_TOKEN", response["access_token"])
            log("Access token refreshed and saved.")
            return True

        log("Failed to refresh access token")
        print("Failed to access token:", response)
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
            print(f"Received auth_code: {self.auth_code}")
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
