import pynmea2
import csv
import sys
import os
from datetime import datetime

def parse_log(filepath):
    output_csv = filepath.replace(".txt", ".csv")
    data_rows = []
    
    print(f"Parsing {filepath}...")
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
                
            try:
                # Format is [timestamp],[nmea_sentence]
                parts = line.split(',', 1)
                sys_ts = float(parts[0])
                nmea = parts[1]
                
                if not nmea.startswith('$G'):
                    continue
                    
                msg = pynmea2.parse(nmea)
                
                row = {
                    "sys_time": datetime.fromtimestamp(sys_ts).strftime('%Y-%m-%d %H:%M:%S.%f'),
                    "gps_time": "N/A",
                    "lat": "N/A",
                    "lon": "N/A",
                    "alt": "N/A",
                    "sats": "0",
                    "speed": "0",
                    "type": msg.sentence_type
                }
                
                if hasattr(msg, 'timestamp') and msg.timestamp:
                    row["gps_time"] = str(msg.timestamp)
                
                if isinstance(msg, pynmea2.types.talker.GGA):
                    if msg.gps_qual > 0:
                        row["lat"] = f"{msg.latitude:.6f}"
                        row["lon"] = f"{msg.longitude:.6f}"
                        row["alt"] = msg.altitude
                        row["sats"] = msg.num_sats
                        data_rows.append(row)
                        
                elif isinstance(msg, pynmea2.types.talker.RMC):
                    if msg.status == 'A':
                        row["lat"] = f"{msg.latitude:.6f}"
                        row["lon"] = f"{msg.longitude:.6f}"
                        row["speed"] = msg.spd_over_grnd
                        data_rows.append(row)
                        
            except Exception:
                continue
                
    if data_rows:
        keys = data_rows[0].keys()
        with open(output_csv, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data_rows)
        print(f"Successfully parsed {len(data_rows)} data points to {output_csv}")
    else:
        print("No valid GPS fixes found in log.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parse_log(sys.argv[1])
    else:
        # If no file provided, check logs directory
        log_dir = "logs"
        if os.path.exists(log_dir):
            files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".txt")]
            if not files:
                print("No log files found in 'logs/' directory.")
            else:
                # Parse the most recent one
                latest_file = max(files, key=os.path.getctime)
                parse_log(latest_file)
        else:
            print("Usage: python parse_logs.py [path_to_log_file]")
