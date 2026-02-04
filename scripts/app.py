import streamlit as st
import pandas as pd
import glob
import os
import pydeck as pdk
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(page_title="NMS Data Portal", layout="wide")
st.title("NMS Data Portal")

# --- 1. Smart Path Detection ---
if os.path.exists('racestudio-compatible-data'):
    log_folder = 'racestudio-compatible-data'
elif os.path.exists('../racestudio-compatible-data'):
    log_folder = '../racestudio-compatible-data'
else:
    st.error("Telemetry folder not found.")
    st.stop()

# --- 2. File Selection ---
csv_files = glob.glob(f"{log_folder}/*.csv")

if not csv_files:
    st.warning(f"No .csv logs found in {log_folder}/")
else:
    file_map = {os.path.basename(f): f for f in csv_files}
    selected_filename = st.sidebar.selectbox("Select Session Log", list(file_map.keys()))
    selected_path = file_map[selected_filename]

    # --- 3. Load & Clean Telemetry Data ---
    df = pd.read_csv(selected_path, skiprows=14)
    df = df.drop(0) 
    df = df.apply(pd.to_numeric, errors='coerce')

    # --- 4. Battery Power Calculations ---
    df['Power_kW'] = (df['External Voltage'] * df['Current']) / 1000.0
    df['dt'] = df['Time'].diff().fillna(0)
    df['Energy_Ws'] = (df['External Voltage'] * df['Current']) * df['dt']
    total_energy_wh = df['Energy_Ws'].sum() / 3600.0

    # --- 5. High-Level Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Power", f"{df['Power_kW'].max():.1f} kW")
    col2.metric("Total Energy", f"{total_energy_wh:.2f} Wh")
    col3.metric("Peak Current", f"{df['Current'].max():.1f} A")
    col4.metric("Max Speed", f"{df['GPS Speed'].max():.1f} mph")

    # --- 6. Power Analysis Chart ---
    st.subheader("Powertrain Analysis")
    st.line_chart(df, x="Time", y=["Power_kW", "Current"])

    # --- 7. Channel Comparison ---
    st.divider()
    st.subheader("Channel Comparison")
    available_channels = [c for c in df.columns if c not in ['Time', 'dt', 'Energy_Ws']]
    selected_channels = st.multiselect("Select Channels", available_channels, default=["GPS Speed", "RPM"])
    if selected_channels:
        st.line_chart(df, x="Time", y=selected_channels)

# --- 8. Track Map with Satellite View and Narrow Trace ---
    st.subheader("Track Map")
    map_data = df[['GPS Latitude', 'GPS Longitude']].dropna()
    map_data.columns = ['lat', 'lon']

    # Using pydeck for satellite view and narrow trace
    st.pydeck_chart(pdk.Deck(
        # Set background to satellite imagery
        map_style='mapbox://styles/mapbox/satellite-v9',
        initial_view_state=pdk.ViewState(
            latitude=map_data['lat'].mean(),
            longitude=map_data['lon'].mean(),
            zoom=16.5, # Zoomed in closer for track detail
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data=map_data,
                get_position='[lon, lat]',
                # RGBA: Red trace with some transparency
                get_color='[255, 75, 75, 160]', 
                get_radius=1.5, # Reduced from 2 to 1.5 for an even thinner line
            ),
        ],
    ))

    with st.expander("View Raw Data Table"):
        st.dataframe(df)
