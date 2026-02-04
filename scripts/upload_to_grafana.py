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
    # 1. Find the CSV file dynamically
    csv_files = glob.glob('data/*.csv')
    
    if not csv_files:
        print("No CSV files found in the data/ directory.")
        return

    for file_path in csv_files:
        print(f"Processing {file_path}...")
        
        # 2. Load data, skipping the AiM metadata block
        # skiprows=14 puts us at the header names
        df = pd.read_csv(file_path, skiprows=14)
        df = df.drop(0) # Drops the units row (s, mph, g, etc.)
        
        base_time = time.time()
        lines = []
        
        for _, row in df.iterrows():
            try:
                # Convert relative 'Time' to absolute nanoseconds
                ts_ns = int((base_time + float(row['Time'])) * 1e9)
                
                # Format Line Protocol
                # We use .get() or handle spaces in column names carefully
                line = (
                    f"fsae_telemetry,vehicle=BillieJean "
                    f"gps_speed={float(row['GPS Speed'])},"
                    f"rpm={float(row['RPM'])},"
                    f"lat_acc={float(row['GPS LatAcc'])},"
                    f"lon_acc={float(row['GPS LonAcc'])},"
                    f"voltage={float(row['External Voltage'])} "
                    f"{ts_ns}"
                )
                lines.append(line)
            except (ValueError, KeyError) as e:
                continue # Skip rows with bad data or missing columns

        # 3. Push to Grafana Cloud
        payload = "\n".join(lines)
        response = requests.post(
            URL,
            data=payload,
            headers={'Content-Type': 'text/plain'},
            auth=(USER_ID, TOKEN)
        )
        
        print(f"Uploaded {file_path} - Status: {response.status_code}")

if __name__ == "__main__":
    upload_csv()
