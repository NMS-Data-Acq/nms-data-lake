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
    # 1. Use the new path you set
    target_dir = 'racestudio-compatible-data'
    csv_files = glob.glob(f'{target_dir}/*.csv')
    
    if not csv_files:
        print(f"❌ Error: No CSV files found in {target_dir}")
        print(f"Current Working Directory: {os.getcwd()}")
        print(f"Root contents: {os.listdir('.')}")
        if os.path.exists(target_dir):
            print(f"Folder contents: {os.listdir(target_dir)}")
        return

    for file_path in csv_files:
        print(f"🚀 Processing: {file_path}")
        
        # 2. Load data, skipping the metadata header (14 rows)
        try:
            df = pd.read_csv(file_path, skiprows=14)
            df = df.drop(0) # Remove the units row
        except Exception as e:
            print(f"❌ Failed to parse {file_path}: {e}")
            continue

        base_time = int(time.time())
        lines = []
        
        for _, row in df.iterrows():
            try:
                # Relative time to nanoseconds
                ts_ns = int((base_time + float(row['Time'])) * 1e9)
                
                # Line Protocol for Billie Jean
                line = (
                    f"fsae_telemetry,vehicle=BillieJean "
                    f"gps_speed={float(row['GPS Speed'])},"
                    f"rpm={float(row['RPM'])},"
                    f"voltage={float(row['External Voltage'])} "
                    f"{ts_ns}"
                )
                lines.append(line)
            except Exception:
                continue 

        # 3. Push to Grafana Cloud
        if lines:
            payload = "\n".join(lines)
            response = requests.post(
                URL,
                data=payload,
                headers={'Content-Type': 'text/plain'},
                auth=(USER_ID, TOKEN)
            )
            print(f"✅ Uploaded {file_path} - Status: {response.status_code}")
        else:
            print(f"⚠️ No valid telemetry rows in {file_path}")

if __name__ == "__main__":
    upload_csv()
