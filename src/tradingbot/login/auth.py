from fyers_apiv3 import fyersModel  # type: ignore
from tradingbot.utils.logger import log
from tradingbot.login.authentication import auto_login
from tradingbot.config import CLIENT_ID
import os
from dotenv import load_dotenv


def login_and_create_fyers():
    """
    Single source of truth:
    - validate existing token if present
    - else auto-login
    - return a validated fyers instance
    """

    log("🔐 Authenticating with Fyers...")

    # Load env fresh (important)
    load_dotenv(override=True)
    token = os.getenv("FYERS_ACCESS_TOKEN")

    # --------------------------------------------------
    # 1️⃣ Try existing token (returning user)
    # --------------------------------------------------
    if token:
        fyers = fyersModel.FyersModel(
            client_id=CLIENT_ID,
            token=token,
            log_path=None
        )

        profile = fyers.get_profile()
        if profile.get("code") == 200:
            log("🟢 Existing access token valid — reusing session")
            return fyers
        else:
            log("⚠️ Existing token invalid — re-login required")

    # --------------------------------------------------
    # 2️⃣ Fresh login
    # --------------------------------------------------
    token = auto_login()
    if not token:
        raise RuntimeError("Auto login failed — no token returned")

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=token,
        log_path=None
    )

    profile = fyers.get_profile()
    if profile.get("code") != 200:
        log(f"❌ Fyers validation failed: {profile}")
        raise RuntimeError("Fyers token invalid after login")

    log("🟢 Fyers authenticated & validated successfully")
    return fyers
