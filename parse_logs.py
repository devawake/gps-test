import pynmea2
import csv
import sys
import os
from datetime import datetime

def parse_log(filepath):
    output_csv = filepath.replace(".txt", ".csv")
    # Using a dict to group data by GPS timestamp
    grouped_data = {}
    
    print(f"Parsing {filepath} and grouping by timestamp...")
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
                
            try:
                parts = line.split(',', 1)
                sys_ts = float(parts[0])
                nmea = parts[1]
                
                if not nmea.startswith('$G'):
                    continue
                    
                msg = pynmea2.parse(nmea)
                
                # We use the GPS timestamp (if available) as the key to group RMC/GGA/VTG
                # If no timestamp (like GSV), we use the system second
                gps_time = str(getattr(msg, 'timestamp', int(sys_ts)))
                
                if gps_time not in grouped_data:
                    grouped_data[gps_time] = {
                        "sys_time": datetime.fromtimestamp(sys_ts).strftime('%Y-%m-%d %H:%M:%S'),
                        "gps_time": gps_time,
                        "lat": "N/A",
                        "lon": "N/A",
                        "alt_m": "N/A",
                        "sats_used": "0",
                        "speed_kn": "0.0",
                        "course": "0.0",
                        "fix": "No"
                    }
                
                entry = grouped_data[gps_time]

                if isinstance(msg, pynmea2.types.talker.GGA):
                    entry["sats_used"] = msg.num_sats
                    if msg.gps_qual > 0:
                        entry["lat"] = f"{msg.latitude:.6f}"
                        entry["lon"] = f"{msg.longitude:.6f}"
                        entry["alt_m"] = msg.altitude
                        entry["fix"] = "Yes"
                        
                elif isinstance(msg, pynmea2.types.talker.RMC):
                    if msg.status == 'A':
                        entry["lat"] = f"{msg.latitude:.6f}"
                        entry["lon"] = f"{msg.longitude:.6f}"
                        entry["speed_kn"] = f"{msg.spd_over_grnd:.2f}"
                        entry["course"] = f"{msg.true_course or 0.0:.1f}"
                        entry["fix"] = "Yes"

            except Exception:
                continue
                
    # Sort by system time
    sorted_rows = sorted(grouped_data.values(), key=lambda x: x['sys_time'])

    if sorted_rows:
        keys = sorted_rows[0].keys()
        with open(output_csv, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(sorted_rows)
        print(f"Successfully processed {len(sorted_rows)} unique time points to {output_csv}")
    else:
        print("No valid GPS data found in log.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parse_log(sys.argv[1])
    else:
        log_dir = "logs"
        if os.path.exists(log_dir):
            files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".txt")]
            if not files:
                print("No log files found in 'logs/' directory.")
            else:
                latest_file = max(files, key=os.path.getctime)
                parse_log(latest_file)
        else:
            print("Usage: python parse_logs.py [path_to_log_file]")
