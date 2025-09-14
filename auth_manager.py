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


class AuthManager:
    def __init__(self, env_path=".env"):
        load_dotenv(env_path)
        self.env_path = env_path
        self.auth_code = None

    def refresh_access_token(self):
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
            print("✅ Access token refreshed and saved.")
            return True

        print("❌ Failed to refresh token:", response)
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

        print("⚠️ Starting manual login flow.")

        app = Flask(__name__)

        @app.route("/callback")
        def callback():
            self.auth_code = request.args.get("auth_code")
            return "✅ Authorization Code received. You can close this tab."

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
            print("✅ Authentication successful and tokens saved.")
            log("Authentication successful.")
        else:
            print("❌ Failed to get tokens:", response)
            log(f"Authentication failed: {response}")
            exit(1)
