import streamlit as st
import os
import pandas as pd

base_folder = path = os.path.join(os.getcwd(),'index_stocks.xlsx')

# read the file
file = pd.read_excel(path)


print(file)