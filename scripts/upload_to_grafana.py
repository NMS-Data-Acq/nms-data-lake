import pandas as pd
import requests
import os
import time
import glob

# Credentials from GitHub Secrets
URL = os.getenv("GRAFANA_URL")
USER_ID = os.getenv("GRAFANA_USER")
TOKEN = os.getenv("GRAFANA_TOKEN")

def upload_csv():
    # Find any CSV file in the data folder
    csv_files = glob.glob('racestudio-compatible-data/*.csv')
    
    if not csv_files:
        print("Error: No CSV files found in the data/ directory.")
        # List files to help with debugging in the Action logs
        print(f"Current directory contents: {os.listdir('.')}")
        if os.path.exists('data'):
            print(f"Data directory contents: {os.listdir('data')}")
        return

    for file_path in csv_files:
        print(f"Processing: {file_path}")
        
        # Load data, skipping the metadata header (14 rows)
        df = pd.read_csv(file_path, skiprows=14)
        df = df.drop(0) # Remove the units row (s, mph, g, etc.)

        # Use the current time as a base for the relative timestamps in the CSV
        base_time = int(time.time())

        lines = []
        for _, row in df.iterrows():
            try:
                # Convert relative 'Time' (seconds) to absolute nanoseconds
                # Ensure we handle column names with quotes if present
                ts_ns = int((base_time + float(row['Time'])) * 1e9)
                
                # Format: measurement,tag field=val timestamp
                line = (
                    f"fsae_telemetry,vehicle=BillieJean "
                    f"gps_speed={float(row['GPS Speed'])},"
                    f"rpm={float(row['RPM'])},"
                    f"voltage={float(row['External Voltage'])} "
                    f"{ts_ns}"
                )
                lines.append(line)
            except Exception as e:
                continue # Skip rows that might have corrupted data

        # Push to Grafana Cloud
        payload = "\n".join(lines)
        response = requests.post(
            URL,
            data=payload,
            headers={'Content-Type': 'text/plain'},
            auth=(USER_ID, TOKEN)
        )
        
        print(f"Uploaded {file_path} - Status Code: {response.status_code}")

if __name__ == "__main__":
    upload_csv()
