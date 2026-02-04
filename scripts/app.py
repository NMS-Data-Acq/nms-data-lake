import streamlit as st
import pandas as pd
import glob
import os
import pydeck as pdk
import numpy as np

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

# --- 2. File Selection (Clean Filenames) ---
csv_paths = glob.glob(f"{log_folder}/*.csv")
if not csv_paths:
    st.warning("No .csv logs found.")
    st.stop()

file_mapping = {os.path.basename(p): p for p in csv_paths}
selected_filename = st.sidebar.selectbox("Select Session Log", sorted(file_mapping.keys()))
selected_path = file_mapping[selected_filename]

# --- 3. Unit Selection ---
unit_system = st.sidebar.radio("Unit System", ["Imperial (mph)", "Metric (km/h)"])

# --- 4. Data Loading ---
# low_memory=False handles the large variety of columns in Race Studio exports
df = pd.read_csv(selected_path, skiprows=14, low_memory=False)
df = df.drop(0).apply(pd.to_numeric, errors='coerce')

# --- 5. Unit Conversions ---
if unit_system == "Imperial (mph)":
    df['DisplaySpeed'] = df['GPS Speed'] * 0.621371
    speed_label = "mph"
else:
    df['DisplaySpeed'] = df['GPS Speed']
    speed_label = "km/h"

# --- 6. Explicit Powertrain Mapping ---
# We prioritize 'Pack' names found in 3.csv to avoid grabbing the 12V LV rail
hv_volt_col = next((c for c in df.columns if 'Pack Voltage' in c), 
                   next((c for c in df.columns if 'Voltage' in c and 'External' not in c), None))

hv_curr_col = next((c for c in df.columns if 'Pack Current' in c), 
                   next((c for c in df.columns if 'Current' in c), None))

if hv_volt_col and hv_curr_col:
    # Calculate Power: P = (|V| * I) / 1000 for kW
    # We use .abs() because Pack Voltage in your CSV shows as negative potential
    df['Power_kW'] = (df[hv_volt_col].abs() * df[hv_curr_col]) / 1000.0
    
    # Energy integration (Watt-hours)
    df['dt'] = df['Time'].diff().fillna(0)
    df['Energy_Ws'] = (df[hv_volt_col].abs() * df[hv_curr_col]) * df['dt']
    total_energy_wh = df['Energy_Ws'].sum() / 3600.0
else:
    df['Power_kW'] = 0
    total_energy_wh = 0

# --- 7. Dashboard Header Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Max Speed", f"{df['DisplaySpeed'].max():.1f} {speed_label}")
col2.metric("Max Power", f"{df['Power_kW'].max():.1f} kW")
col3.metric("Total Energy", f"{total_energy_wh:.2f} Wh")
# This ensures the metric shows the 300V range, not the 12V range
col4.metric("Avg HV Voltage", f"{df[hv_volt_col].abs().mean():.1f} V" if hv_volt_col else "N/A")

# --- 8. Powertrain Visualization ---
st.subheader("Powertrain Analysis")
if hv_volt_col and hv_curr_col:
    # Plotting Power and Current together
    st.line_chart(df, x="Time", y=["Power_kW", hv_curr_col])
else:
    st.error("Could not find 'Pack Voltage' or 'Pack Current' in CSV headers.")

# --- 9. Interactive Channel Comparison ---
st.divider()
available_channels = [c for c in df.columns if c not in ['Time', 'dt', 'Energy_Ws', 'Power_kW', 'DisplaySpeed']]
selected_channels = st.multiselect("Select Channels to Graph", available_channels + ["DisplaySpeed"], default=["DisplaySpeed"])
if selected_channels:
    st.line_chart(df, x="Time", y=selected_channels)

# --- 10. Satellite Track Map ---
st.subheader("Track Map")
if 'GPS Latitude' in df and 'GPS Longitude' in df:
    map_data = df[['GPS Latitude', 'GPS Longitude']].dropna()
    map_data.columns = ['lat', 'lon']
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/satellite-v9',
        initial_view_state=pdk.ViewState(latitude=map_data['lat'].mean(), longitude=map_data['lon'].mean(), zoom=16),
        layers=[pdk.Layer('ScatterplotLayer', data=map_data, get_position='[lon, lat]', get_color='[255, 75, 75, 160]', get_radius=0.5)],
    ))
