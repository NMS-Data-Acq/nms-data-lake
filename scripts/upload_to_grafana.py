import pandas as pd
import requests
import os
import time

# Credentials from GitHub Secrets
URL = os.getenv("GRAFANA_URL")
USER_ID = os.getenv("GRAFANA_USER")
TOKEN = os.getenv("GRAFANA_TOKEN")

def upload_csv():
    # 1. Load data, skipping the AiM metadata block
    # Row 14 is the channel names, Row 15 is the units. We skip units.
    df = pd.read_csv('data/race_data.csv', skiprows=14)
    df = df.drop(0) # Drops the units row (e.g., "s", "mph", "g")
    
    # 2. Get the session date from the header for absolute time calculation
    # In a real scenario, you'd parse row 6 "Date" and row 7 "Time" 
    # For now, we'll use current time as the base
    base_time = time.time()

    lines = []
    for _, row in df.iterrows():
        # Convert relative 'Time' (seconds) to absolute nanoseconds
        ts_ns = int((base_time + float(row['Time'])) * 1e9)
        
        # Build Line Protocol
        # Measurement: fsae_telemetry
        # Fields: Speed, Accel, RPM, Battery Voltage, etc.
        line = (
            f"fsae_telemetry "
            f"gps_speed={row['GPS Speed']},"
            f"rpm={row['RPM']},"
            f"lat_acc={row['GPS LatAcc']},"
            f"lon_acc={row['GPS LonAcc']},"
            f"voltage={row['External Voltage']} "
            f"{ts_ns}"
        )
        lines.append(line)

    # 3. Batch push to Grafana Cloud
    payload = "\n".join(lines)
    response = requests.post(
        URL,
        data=payload,
        headers={'Content-Type': 'text/plain'},
        auth=(USER_ID, TOKEN)
    )
    
    print(f"Upload Status: {response.status_code}")

if __name__ == "__main__":
    upload_csv()
