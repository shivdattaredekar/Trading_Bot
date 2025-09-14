import os
import time
import webbrowser
from threading import Thread
from flask import Flask, request
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

from src.tradingsetup.config.settings import (
    CLIENT_ID, SECRET_KEY, REDIRECT_URI, RESPONSE_TYPE, GRANT_TYPE
) 
from src.tradingsetup.utlis.logger import log

REFRESH_TOKEN_VALIDITY_DAYS = 15
GRACE_PERIOD_DAYS = 1

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
            print(f"⚠️ Refresh token is expiring soon or already expired (age: {elapsed_days:.2f} days). Manual login needed.")
            log("⚠️ Refresh token expiring soon. Manual re-login recommended.")
            return True
        return False

    def refresh_access_token(self):
        if self._is_refresh_token_expiring_soon():
            return False  # Force manual login

        refresh_token = os.getenv("FYERS_REFRESH_TOKEN")
        if not refresh_token:
            print("❌ No refresh token found, manual login required.")
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
            print("✅ Access & refresh tokens refreshed and saved.")
            log("Tokens refreshed successfully.")
            return True

        print("❌ Failed to refresh tokens:", response)
        return False

    def is_token_valid(self):
        token = os.getenv("FYERS_ACCESS_TOKEN")
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
            print("⚠️ Token invalid, trying to refresh...")
            return self.refresh_access_token()
        except Exception:
            return self.refresh_access_token()

    def auto_login(self):
        if self.is_token_valid():
            print("✅ Token valid, skipping login.")
            return

        print("⚠️ Manual login flow started.")

        app = Flask(__name__)

        @app.route("/callback")
        def callback():
            self.auth_code = request.args.get("auth_code")
            return "✅ Auth code received. Close this tab."

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
        print("🌐 Opening browser for login...")
        webbrowser.open(login_url, new=1)

        while self.auth_code is None:
            time.sleep(1)

        session.set_token(self.auth_code)
        response = session.generate_token()

        if "access_token" in response and "refresh_token" in response:
            set_key(self.env_path, "FYERS_ACCESS_TOKEN", response["access_token"])
            set_key(self.env_path, "FYERS_REFRESH_TOKEN", response["refresh_token"])
            set_key(self.env_path, "REFRESH_TOKEN_ISSUE_TIMESTAMP", str(int(time.time())))
            print("✅ Manual login successful; tokens saved.")
            log("Manual login successful.")
        else:
            print("❌ Failed to get tokens:", response)
            log(f"Authentication failed: {response}")
            exit(1)
