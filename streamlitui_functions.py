import streamlit as st
from datetime import datetime
import os


def load_logs(path:str) -> str:
    # Today's date
    today = datetime.today().date()

    # Build log file path with .log extension
    log_file = os.path.join(path, f"run_{today}.log")

    # Read and print file content if it exists
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            st.write(f.read())
    else:
        st.write(f"No log file found for today: {log_file}")
