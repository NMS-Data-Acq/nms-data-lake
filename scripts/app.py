import streamlit as st
import pandas as pd
import glob
import os
import time
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(page_title="NMS Telemetry", layout="wide")
st.title("NMS Data Portal")

# --- 1. Smart Path Detection ---
# Streamlit Cloud runs from the repo root; local dev often runs from the script folder.
if os.path.exists('racestudio-compatible-data'):
    log_folder = 'racestudio-compatible-data'
elif os.path.exists('../racestudio-compatible-data'):
    log_folder = '../racestudio-compatible-data'
else:
    st.error("Telemetry folder 'racestudio-compatible-data' not found.")
    st.info(f"Current Dir: {os.getcwd()} | Contents: {os.listdir('.')}")
    st.stop()

# --- 2. File Selection ---
csv_files = glob.glob(f"{log_folder}/*.csv")

if not csv_files:
    st.warning(f"No .csv logs found in {log_folder}/")
else:
    # Sidebar for session picking
    file_map = {os.path.basename(f): f for f in csv_files}
    selected_filename = st.sidebar.selectbox("Select Session Log", list(file_map.keys()))
    selected_path = file_map[selected_filename]

    # --- 3. Header Parsing (Date/Time) ---
    try:
        header_df = pd.read_csv(selected_path, nrows=10, header=None)
        date_str = header_df.iloc[6, 1] # Row 7: Date
        time_str = header_df.iloc[7, 1] # Row 8: Time
        full_dt = f"{date_str} {time_str}"
        session_date = datetime.strptime(full_dt, "%A, %B %d, %Y %I:%M %p")
        st.sidebar.success(f"Session: {session_date.strftime('%Y-%m-%d %H:%M')}")
    except Exception:
        session_date = datetime.now()
        st.sidebar.info("Using current date (Header unreadable)")

    # --- 4. Load & Clean Telemetry Data ---
    # AiM CSVs have 14 lines of metadata, then headers, then a units row
    df = pd.read_csv(selected_path, skiprows=14)
    df = df.drop(0) # Remove units row (s, mph, g, etc.)
    df = df.apply(pd.to_numeric, errors='coerce')
    
    # Create an absolute timestamp column for internal tracking if needed
    df['Abs_Time'] = pd.to_datetime(session_date.timestamp() + df['Time'], unit='s')

    # --- 5. High-Level Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Speed", f"{df['GPS Speed'].max():.1f} mph")
    col2.metric("Max RPM", f"{int(df['RPM'].max())}")
    col3.metric("Avg Voltage", f"{df['External Voltage'].mean():.2f} V")
    col4.metric("Max Lateral G", f"{df['GPS LatAcc'].max():.2f} g")

    # --- 6. Telemetry Charts ---
    st.subheader("Interactive Telemetry")
    default_channels = ["GPS Speed", "RPM"]
    # Filter out non-data columns for the selector
    available_channels = [c for c in df.columns if c not in ['Time', 'Abs_Time']]
    
    selected_channels = st.multiselect("Select Data Channels", available_channels, default=default_channels)
    
    if selected_channels:
        st.line_chart(df, x="Time", y=selected_channels)

    # --- 7. Engineering Analysis (G-G Diagram) ---
    st.divider()
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.subheader("G-G Diagram (Traction Circle)")
        st.scatter_chart(df, x="GPS LatAcc", y="GPS LonAcc", color="#FF4B4B")
        st.caption("Lateral Accel (X) vs Longitudinal Accel (Y)")

    with right_col:
        st.subheader("GPS Track Map")
        # Rename columns for streamlit's native map function
        map_data = df[['GPS Latitude', 'GPS Longitude']].dropna()
        map_data.columns = ['lat', 'lon']
        st.map(map_data)

    # --- 8. Raw Data Preview ---
    with st.expander("View Raw Data Table"):
        st.dataframe(df)
