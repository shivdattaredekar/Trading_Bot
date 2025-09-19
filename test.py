import streamlit as st
import os

# --- Side bar ---
st.sidebar.title("📊 Files")

folder = r"D:\Datascience\trading_setup"

# Get list of files with specific extension
allowed_ext = ['.pdf','.txt','.csv','.json']

files = [f for f in os.listdir(folder) if os.path.splitext(f)[1] in allowed_ext]

# Display files with clickable links
for file in files:
    file_path = os.path.join(folder, file)

    # Show the content after clicking the link
    if st.sidebar.button(f"Show {file}"):
        with open(file_path, 'r') as f:
            content = f.read()
            st.code(content)


