import time
import os
import webbrowser

from flask import Flask, request
from threading import Thread
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

from src.tradingsetup.utlis.logger import log
from src.tradingsetup.config.settings import (
    REDIRECT_URI,
    SECRET_KEY,
    GRANT_TYPE,
    CLIENT_ID,
    RESPONSE_TYPE
)


# === Helper: Check if existing token is valid ===
def is_token_valid():
    load_dotenv(".env")
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
        # If profile fetch is successful, token is valid
        if "s" in response and response["s"] == "ok":
            return True
        return False
    except Exception:
        return False


# === Main auto login function ===
def auto_login():
    env_path = ".env"
    load_dotenv(dotenv_path=env_path)

    # 1️⃣ Check if token is still valid
    if is_token_valid():
        print("✅ Existing token is valid, skipping login.")
        log("Existing token is valid, skipping login.")
        return
    else:
        print("⚠️ Token expired or missing, starting login flow...")
        log("Token expired or missing, starting login flow...")

    # Auth params
    redirect_uri = REDIRECT_URI
    client_id = CLIENT_ID
    secret_key = SECRET_KEY
    grant_type = GRANT_TYPE
    response_type = RESPONSE_TYPE
    state = "sample"

    # Flask app to capture redirect
    app = Flask(__name__)
    auth_code = None

    @app.route("/callback")
    def callback():
        nonlocal auth_code
        auth_code = request.args.get("auth_code")
        return "Authorization Code received. You may close this tab."

    def run_flask():
        app.run(port=5000)

    # Start Flask server
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    time.sleep(2)

    # Create SessionModel
    appSession = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state,
        secret_key=secret_key,
        grant_type=grant_type
    )

    # Open login URL
    login_url = appSession.generate_authcode()
    print("Opening browser for login...")
    webbrowser.open(login_url, new=1)

    # Wait until user logs in
    while auth_code is None:
        time.sleep(1)

    # Exchange auth_code for access_token
    appSession.set_token(auth_code)
    response = appSession.generate_token()

    try:
        access_token = response["access_token"]
        set_key(env_path, "FYERS_ACCESS_TOKEN", access_token)
        print("✅ Access token saved to .env")
        log("Authentication successful.")
    except Exception as e:
        print("❌ Failed to get access token:", response)
        log(f"Authentication failed: {response}")
        exit()
