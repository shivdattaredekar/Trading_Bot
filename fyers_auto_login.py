
from flask import Flask, request
from threading import Thread
from fyers_apiv3 import fyersModel
import webbrowser
import time
from dotenv import load_dotenv, set_key
import os
from .utlis.logger import log
from .config.settings import *


# Save access token to a file for later use
def auto_login():
    # === Load .env ===
    env_path = ".env"
    load_dotenv(dotenv_path=env_path)

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
    appSession = fyersModel.SessionModel(client_id=client_id,
                                         redirect_uri=redirect_uri,
                                         response_type=response_type,
                                         state=state,
                                         secret_key=secret_key,
                                         grant_type=grant_type)

    login_url = appSession.generate_authcode()
    print("Opening browser for login...")
    webbrowser.open(login_url, new=1)

    while auth_code is None:
        time.sleep(1)

    appSession.set_token(auth_code)
    response = appSession.generate_token()

    try:
        access_token = response["access_token"]
        set_key(env_path, "FYERS_ACCESS_TOKEN", access_token)
        print("✅ Access token saved to .env")
        log("Authentication successful.")
    except Exception as e:
        print("❌ Failed to get access token:", response)
        exit()



"""

# Auth params
redirect_uri = "http://127.0.0.1:5000/callback"
client_id = "MX3ZI638YI-100"
secret_key = "2IC9MIKXVJ"
grant_type = "authorization_code"
response_type = "code"
state = "sample"

# Flask app to capture redirect
app = Flask(__name__)
auth_code = None

@app.route("/callback")
def callback():
    global auth_code
    auth_code = request.args.get("auth_code")
    return "Authorization Code received. You may close this tab."

def run_flask():
    app.run(port=5000)

# Start Flask server in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Wait a bit to make sure Flask is ready
time.sleep(2)

# Generate login URL and open it
appSession = fyersModel.SessionModel(client_id=client_id,
                                     redirect_uri=redirect_uri,
                                     response_type=response_type,
                                     state=state,
                                     secret_key=secret_key,
                                     grant_type=grant_type)

login_url = appSession.generate_authcode()
print("Opening browser for login...")
webbrowser.open(login_url, new=1)

# Wait until auth_code is received
while auth_code is None:
    time.sleep(1)

# Set token and generate access token
appSession.set_token(auth_code)
response = appSession.generate_token()

try:
    access_token = response["access_token"]
    print(f"Access Token: {access_token}")
except Exception as e:
    print("Error:", response)
    exit()

# === Load or create .env ===
env_path = ".env"
load_dotenv(dotenv_path=env_path)

set_key(env_path, "FYERS_ACCESS_TOKEN", access_token)

# Create Fyers client
fyers = fyersModel.FyersModel(token=access_token, is_async=False, client_id=client_id, log_path="")

# Fetch and print account details
print(f'Customer Profile:\n{fyers.get_profile()["data"]}\n')
print(f'Customer Account Info:\n{fyers.funds()["fund_limit"]}\n')
print(f'Customer Holdings:\n{fyers.holdings()["overall"]}\n')

"""
