import os
import time
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

# Import your trading main
from main import main

# Load environment variables
load_dotenv()

# --- Sidebar Secrets ---
st.sidebar.title("🔑 Configuration")

# Master password input
master_password = st.sidebar.text_input(
    "Enter master password to use .env credentials", type="password"
)

# Check if password is correct
use_env_creds = master_password == "shivdatta"

if use_env_creds:
    st.sidebar.success("✅ Credentials loaded from .env (hidden & disabled)")

# Credentials inputs
CLIENT_ID = st.sidebar.text_input(
    "Client ID",
    value=os.getenv("CLIENT_ID") if use_env_creds else "",
    type="password",
    disabled=use_env_creds
)
SECRET_KEY = st.sidebar.text_input(
    "Secret Key",
    value=os.getenv("SECRET_KEY") if use_env_creds else "",
    type="password",
    disabled=use_env_creds
)
REDIRECT_URI = st.sidebar.text_input(
    "Redirect URI",
    value=os.getenv("REDIRECT_URI") if use_env_creds else "",
    disabled=use_env_creds
)
FYERS_ID = st.sidebar.text_input(
    "Fyers ID",
    value=os.getenv("FYERS_CLIENT_ID") if use_env_creds else "",
    type="password",
    disabled=use_env_creds
)


# --- Config ---
st.set_page_config(page_title="Fyers Trading Bot", layout="wide")
folder_logs = r"D:\Datascience\trading_setup\logs"
log_file = os.path.join(folder_logs, f"run_{datetime.today().date()}.log")
base_folder = r"D:\Datascience\trading_setup"
allowed_ext = [".pdf", ".txt", ".csv", ".json"]

# --- Session State ---
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False

# --- UI Header ---
st.title("⚡ Trading Setup Dashboard")

# --- Start Trading Button ---
if st.button("🚀 Start Trading Bot"):
    st.session_state.bot_started = True
    main()  # run bot in background (if blocking, you should thread this)

# --- Logs Section ---
if st.session_state.bot_started:
    st.subheader("📜 Live Logs")
    log_container = st.empty()

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = ["[INFO] No logs yet..."]

    # Keep last 200 lines
    lines = lines[-200:]
    logs_html = []
    for line in lines:
        if "[ERROR]" in line:
            line_html = f'<span style="color:#ff4d4f;">{line}</span>'
        elif "[WARNING]" in line:
            line_html = f'<span style="color:#faad14;">{line}</span>'
        elif "[INFO]" in line:
            line_html = f'<span style="color:#d9d9d9;">{line}</span>'
        else:
            line_html = line
        logs_html.append(line_html)

    log_container.markdown(
        "<div style='background-color:#0e1117; color:white; "
        "padding:10px; border-radius:10px; font-family:monospace; "
        "font-size:14px; line-height:1.4; max-height:500px; "
        "overflow-y:auto;'>"
        + "<br>".join(logs_html) +
        "</div>",
        unsafe_allow_html=True
    )

# --- File Section ---
st.subheader("📂 File Viewer")

files = [f for f in os.listdir(base_folder) if os.path.splitext(f)[1] in allowed_ext]

for file in files:
    file_path = os.path.join(base_folder, file)
    with st.expander(f"📄 {file}"):
        ext = os.path.splitext(file)[1]
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                st.text(f.read())
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                st.json(json.load(f))
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            st.dataframe(df)
        elif ext == ".pdf":
            st.write("📕 PDF viewer not added yet (can integrate pdfplumber or PyPDF2).")

# --- Auto-refresh every 2s ---
st_autorefresh(interval=3000, key="refresh")  # 2s
