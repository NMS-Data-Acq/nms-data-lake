import pandas as pd
import requests
import os
import time
import glob
from datetime import datetime

URL = os.getenv("GRAFANA_URL")
USER_ID = os.getenv("GRAFANA_USER")
TOKEN = os.getenv("GRAFANA_TOKEN")

def get_base_time(file_path):
    """Parses rows 7 and 8 of the AiM CSV to get the absolute session start time."""
    try:
        # Read just the header metadata
        header_df = pd.read_csv(file_path, nrows=10, header=None)
        date_str = header_df.iloc[6, 1] # Row 7: "Saturday, September 14, 2024"
        time_str = header_df.iloc[7, 1] # Row 8: "10:40 AM"
        
        # Combine and parse into datetime object
        full_dt_str = f"{date_str} {time_str}"
        # Format matching: Saturday, September 14, 2024 10:40 AM
        dt_obj = datetime.strptime(full_dt_str, "%A, %B %d, %Y %I:%M %p")
        return int(dt_obj.timestamp())
    except Exception as e:
        print(f"Could not parse session date/time from header: {e}. Using current time.")
        return int(time.time())

def upload_csv():
    csv_files = glob.glob('racestudio-compatible-data/*.csv')
    
    if not csv_files:
        print("No CSV files found.")
        return

    for file_path in csv_files:
        print(f"Processing: {file_path}")
        
        # Get the actual start time from rows 7 & 8
        base_time_seconds = get_base_time(file_path)
        
        try:
            df = pd.read_csv(file_path, skiprows=14)
            df = df.drop(0) # Remove units row
            
            lines = []
            for _, row in df.iterrows():
                try:
                    # Add relative 'Time' to the absolute 'base_time'
                    ts_ns = int((base_time_seconds + float(row['Time'])) * 1e9)
                    
                    line = (
                        f"fsae_telemetry,vehicle=BillieJean "
                        f"gps_speed={float(row['GPS Speed'])},"
                        f"rpm={float(row['RPM'])},"
                        f"voltage={float(row['External Voltage'])} "
                        f"{ts_ns}"
                    )
                    lines.append(line)
                except:
                    continue 

            if lines:
                payload = "\n".join(lines)
                response = requests.post(
                    URL,
                    data=payload,
                    headers={'Content-Type': 'text/plain'},
                    auth=(USER_ID, TOKEN)
                )
                print(f"Uploaded {file_path} - Status: {response.status_code}")
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")

if __name__ == "__main__":
    upload_csv()
