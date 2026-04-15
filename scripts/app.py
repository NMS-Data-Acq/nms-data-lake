import streamlit as st
import pandas as pd
import glob
import os
import pydeck as pdk
import numpy as np
import altair as alt

# --- Page Configuration ---
st.set_page_config(page_title="NMS Dashboard", layout="wide")
st.title("NMS Dashboard")

# --- 1. Smart Path Detection ---
if os.path.exists('racestudio-compatible-data'):
    log_folder = 'racestudio-compatible-data'
elif os.path.exists('../racestudio-compatible-data'):
    log_folder = '../racestudio-compatible-data'
else:
    st.error("Telemetry folder not found.")
    st.stop()

# --- 2. Sidebar: File & Global Controls ---
csv_paths = glob.glob(f"{log_folder}/*.csv")
if not csv_paths:
    st.warning("No .csv logs found.")
    st.stop()

file_mapping = {os.path.basename(p): p for p in csv_paths}
selected_filename = st.sidebar.selectbox("Select Session Log", sorted(file_mapping.keys()))
selected_path = file_mapping[selected_filename]

unit_system = st.sidebar.radio("Unit System", ["Imperial (mph)", "Metric (km/h)"])

# NEW: Toggle which modules are visible
st.sidebar.divider()
st.sidebar.subheader("Visible Modules")
show_aero = st.sidebar.checkbox("Aero Analytics", value = True)
show_chassis = st.sidebar.checkbox("Chassis Analytics", value = True)
show_CDI = st.sidebar.checkbox("CDI Analytics", value = True)
show_electronics = st.sidebar.checkbox("Electronics Analytics", value = True)
show_powertrain = st.sidebar.checkbox("Powertrain Analytics", value=True)
show_suspension = st.sidebar.checkbox("Suspension Analytics", value = True)
show_map = st.sidebar.checkbox("Track Map", value=True) 
show_telemetry = st.sidebar.checkbox("Individual Channels", value=True)

# --- 3. Data Loading ---
df = pd.read_csv(selected_path, skiprows=14, low_memory=False)
df = df.drop(0).apply(pd.to_numeric, errors='coerce')

# --- 4. Unit Conversions ---
if unit_system == "Imperial (mph)":
    df['DisplaySpeed'] = df['GPS Speed'] * 0.621371
    speed_label = "mph"
else:
    df['DisplaySpeed'] = df['GPS Speed']
    speed_label = "km/h"

# --- 5. Aero Calculations ---

# --- 6. Chassis Calculations ---


# --- 7. CDI Calculations ---
# Brake Temperature sensor mapping (label -> column)
BRAKE_TEMP_SENSORS = {
    "FL (RTD3)": "D4 RTD3 Temperat",
    "FR (RTD2)": "D3 RTD2 Temperat",
    "RL (RTD1)": "D2 RTD1 Temperat",
    "RR (RTD5)": "D2 RTD5 Temperat",
}
BRAKE_TEMP_COLORS = {
    "FL (RTD3)": "#EF553B",   # red
    "FR (RTD2)": "#00CC96",   # green
    "RL (RTD1)": "#636EFA",   # blue
    "RR (RTD5)": "#FFA15A",   # orange
}
BRAKE_TEMP_SENTINEL = -999  # values at or below this are disconnected sensors

# Brake Pressure sensor mapping
BRAKE_PRESSURE_SENSORS = {
    "Front (BrakeSensor1)": "BrakeSensor1",
    "Rear  (BrakeSensor2)": "BrakeSensor2",
}
BRAKE_PRESSURE_COLORS = {
    "Front (BrakeSensor1)": "#AB63FA",   # purple
    "Rear  (BrakeSensor2)": "#19D3F3",   # cyan
}
# --- CDI Analytics Module ---
# --- CDI Analytics Module ---
if show_CDI:

    st.divider()
    st.subheader("CDI Analytics")

    # --- Time Window Slider ---
    t_min = float(df['Time'].min())
    t_max = float(df['Time'].max())
    t_start, t_end = st.slider(
        "Time Window (seconds)",
        min_value=t_min,
        max_value=t_max,
        value=(t_min, t_max),
        step=0.05,
        format="%.1f s",
        key="cdi_time_slider"
    )
    cdi_df = df[(df['Time'] >= t_start) & (df['Time'] <= t_end)].copy()

    # ── Panel 1: Brake Temperatures ───────────────────────────────────────
    st.markdown("#### Brake Temperatures")

    temp_view = st.multiselect(
        "Select Sensors",
        options=list(BRAKE_TEMP_SENSORS.keys()),
        default=list(BRAKE_TEMP_SENSORS.keys()),
        key="cdi_temp_view"
    )

    sensors_to_plot = [(label, BRAKE_TEMP_SENSORS[label]) for label in temp_view]
    
    if not sensors_to_plot:
        st.info("Select at least one sensor to display.")

    # Build a long-format dataframe for Altair
    temp_frames = []
    any_temp_data = False
    for label, col in sensors_to_plot:
        series = cdi_df[['Time', col]].copy()
        series[col] = series[col].where(series[col] > BRAKE_TEMP_SENTINEL)
        if series[col].notna().any():
            any_temp_data = True
            series = series.rename(columns={col: 'Temperature'})
            series['Sensor'] = label
            temp_frames.append(series[['Time', 'Temperature', 'Sensor']])
        else:
            st.warning(f"⚠️ {label}: No valid data (sensor may be disconnected).")

    if any_temp_data:
        temp_long = pd.concat(temp_frames, ignore_index=True)
        color_scale = alt.Scale(
            domain=list(BRAKE_TEMP_COLORS.keys()),
            range=list(BRAKE_TEMP_COLORS.values())
        )
        chart_temp = alt.Chart(temp_long).mark_line().encode(
            x=alt.X('Time:Q', title='Time (s)'),
            y=alt.Y('Temperature:Q', title='Temperature (°C)'),
            color=alt.Color('Sensor:N', scale=color_scale),
            tooltip=['Sensor:N', alt.Tooltip('Time:Q', format='.2f'), alt.Tooltip('Temperature:Q', format='.1f')]
        ).properties(height=350).interactive()
        st.altair_chart(chart_temp, use_container_width=True)
    else:
        st.error("No brake temperature data available in this session.")

    # ── Panel 2: Brake Pressures ──────────────────────────────────────────
    st.markdown("#### Brake Pressures")

    pressure_view = st.multiselect(
        "Select Sensors",
        options=list(BRAKE_PRESSURE_SENSORS.keys()),
        default=list(BRAKE_PRESSURE_SENSORS.keys()),
        key="cdi_pressure_view"
    )
    
    sensors_to_plot_p = [(label, BRAKE_PRESSURE_SENSORS[label]) for label in pressure_view]
    
    if not sensors_to_plot_p:
        st.info("Select at least one sensor to display.")

    pres_frames = []
    for label, col in sensors_to_plot_p:
        series = cdi_df[['Time', col]].copy()
        series = series.rename(columns={col: 'Pressure'})
        series['Sensor'] = label
        pres_frames.append(series[['Time', 'Pressure', 'Sensor']])

    pres_long = pd.concat(pres_frames, ignore_index=True)
    color_scale_p = alt.Scale(
        domain=list(BRAKE_PRESSURE_COLORS.keys()),
        range=list(BRAKE_PRESSURE_COLORS.values())
    )
    chart_pres = alt.Chart(pres_long).mark_line().encode(
        x=alt.X('Time:Q', title='Time (s)'),
        y=alt.Y('Pressure:Q', title='Brake Pressure'),
        color=alt.Color('Sensor:N', scale=color_scale_p),
        tooltip=['Sensor:N', alt.Tooltip('Time:Q', format='.2f'), alt.Tooltip('Pressure:Q', format='.3f')]
    ).properties(height=350).interactive()
    st.altair_chart(chart_pres, use_container_width=True)

    # ── Car Speed (reference) ─────────────────────────────────────────────
    st.markdown(f"#### Car Speed ({speed_label})")
    spd_df = cdi_df[['Time', 'DisplaySpeed']].copy().rename(columns={'DisplaySpeed': 'Speed'})
    chart_spd = alt.Chart(spd_df).mark_line(color='#FFD700').encode(
        x=alt.X('Time:Q', title='Time (s)'),
        y=alt.Y('Speed:Q', title=f'Speed ({speed_label})'),
        tooltip=[alt.Tooltip('Time:Q', format='.2f'), alt.Tooltip('Speed:Q', format='.1f')]
    ).properties(height=300).interactive()
    st.altair_chart(chart_spd, use_container_width=True)

# --- 9. Electronics Calculations ---

# --- 10. Powertrain & Regen Calculations ---
hv_volt_col = next((c for c in df.columns if 'Pack Voltage' in c), None)
hv_curr_col = next((c for c in df.columns if 'Pack Current' in c), None)

if hv_volt_col and hv_curr_col:
    df['Power_kW'] = (df[hv_volt_col].abs() * df[hv_curr_col]) / 1000.0
    df['dt'] = df['Time'].diff().fillna(0)
    
    discharge_mask = df['Power_kW'] > 0
    regen_mask = df['Power_kW'] < 0
    
    spent_wh = (df.loc[discharge_mask, 'Power_kW'] * df.loc[discharge_mask, 'dt']).sum() * (1000/3600)
    recovered_wh = (df.loc[regen_mask, 'Power_kW'].abs() * df.loc[regen_mask, 'dt']).sum() * (1000/3600)
    
    regen_efficiency = (recovered_wh / spent_wh * 100) if spent_wh > 0 else 0
    net_energy_wh = spent_wh - recovered_wh
else:
    spent_wh = recovered_wh = regen_efficiency = net_energy_wh = 0

# --- 11. Top Level Metrics (for Powertrain or for all?)--- 
col1, col2, col3, col4 = st.columns(4) 
col1.metric("Max Power", f"{df['Power_kW'].max() if hv_volt_col else 0:.1f} kW")
col2.metric("Net Energy", f"{net_energy_wh:.1f} Wh")
col3.metric("Regen Recovery", f"{regen_efficiency:.1f} %")
col4.metric("Max Speed", f"{df['DisplaySpeed'].max():.1f} {speed_label}")

# --- 12. Modular Powertrain Charts ---
if show_powertrain:
    st.divider()
    st.subheader("Powertrain Analytics")
    if hv_volt_col and hv_curr_col:
        # Separate charts so they aren't overlaid/stacked on one axis
        st.write("**Battery Power (kW)**")
        st.line_chart(df, x="Time", y="Power_kW")
        
        st.write(f"**Battery Current (A) - Sensor: {hv_curr_col}**")
        st.line_chart(df, x="Time", y=hv_curr_col)
    else:
        st.error("HV Pack sensors not found in this file.")

# --- 13. Modular Telemetry Channels (One Chart Per Channel) ---
if show_telemetry:
    st.divider()
    st.subheader("Individual Channel Analysis")
    ignore_cols = ['Time', 'dt', 'Power_kW', 'DisplaySpeed']
    available_channels = [c for c in df.columns if c not in ignore_cols]
    
    selected_channels = st.multiselect("Select Channels to Display", 
                                       available_channels + ["DisplaySpeed"], 
                                       default=["DisplaySpeed"])
    
    # This loop creates a NEW chart for every single item selected
    for channel in selected_channels:
        st.write(f"**{channel}**")
        st.line_chart(df, x="Time", y=channel)

# --- 14. Suspension Calculations ---


# --- 15. Modular Satellite Track Map ---
if show_map:
    st.divider()
    st.subheader("Track Map")
    if 'GPS Latitude' in df and 'GPS Longitude' in df:
        map_data = df[['GPS Latitude', 'GPS Longitude']].dropna()
        map_data.columns = ['lat', 'lon']
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/satellite-v9',
            initial_view_state=pdk.ViewState(latitude=map_data['lat'].mean(), longitude=map_data['lon'].mean(), zoom=16),
            layers=[pdk.Layer('ScatterplotLayer', data=map_data, get_position='[lon, lat]', get_color='[255, 75, 75, 160]', get_radius=1.5)],
        ))

# --- 16. Raw Data Preview ---
with st.expander("View Raw Data"):
    st.dataframe(df)
