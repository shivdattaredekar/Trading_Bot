# src/tradingbot/tools/alerts.py

import os
import requests
import logging

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram credentials not set. Skipping.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.json()
    except Exception as e:
        logging.warning(f"Telegram send failed: {e}")

def send_discord(text: str):
    if not DISCORD_WEBHOOK_URL:
        logging.warning("Discord webhook not set. Skipping.")
        return
    payload = {"content": text}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        return r.status_code, r.text
    except Exception as e:
        logging.warning(f"Discord send failed: {e}")
