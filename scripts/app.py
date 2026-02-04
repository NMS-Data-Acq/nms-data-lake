import streamlit as st
import pandas as pd
import glob
import os

st.set_page_config(page_title="NMS Telemetry", layout="wide")

st.title("NMS Data Portal")

# 1. Look for the folder in the parent directory (..)
# This works specifically because the script is inside 'scripts/'
log_folder = os.path.join('..', 'racestudio-compatible-data')
csv_files = glob.glob(f"{log_folder}/*.csv")

if not csv_files:
    st.error(f"No logs found in {log_folder}/")
    # Debugging: show what the app actually sees
    st.write("Current Dir:", os.getcwd())
    st.write("Parent Contents:", os.listdir('..'))
else:
    # Clean up filenames for the selectbox display
    file_map = {os.path.basename(f): f for f in csv_files}
    selected_filename = st.sidebar.selectbox("Select Session Log", list(file_map.keys()))
    selected_path = file_map[selected_filename]
    
    # 3. Load data
    df = pd.read_csv(selected_path, skiprows=14)
    df = df.drop(0) 
    df = df.apply(pd.to_numeric, errors='coerce')

    # 4. Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Max Speed", f"{df['GPS Speed'].max():.1f} mph")
    col2.metric("Max RPM", int(df['RPM'].max()))
    col3.metric("Avg Voltage", f"{df['External Voltage'].mean():.2f} V")

    st.subheader("Telemetry Overview")
    channels = st.multiselect("Select Channels", df.columns[1:], default=["GPS Speed", "RPM"])
    st.line_chart(df, x="Time", y=channels)
