import serial
import pynmea2
import time
import smbus2
import os

# Configuration
GPS_PORT = "/dev/serial0"
BAUD_RATES = [9600, 38400, 115200]
I2C_BUS = 1
MAG_ADDRESS = 0x0D  # QMC5883L

def setup_magnetometer():
    try:
        bus = smbus2.SMBus(I2C_BUS)
        # Initialize QMC5883L
        bus.write_byte_data(MAG_ADDRESS, 0x09, 0x1D)
        bus.write_byte_data(MAG_ADDRESS, 0x0B, 0x01)
        return bus
    except Exception:
        return None

def read_magnetometer(bus):
    if bus is None:
        return "N/A"
    try:
        data = bus.read_i2c_block_data(MAG_ADDRESS, 0x00, 6)
        x = (data[1] << 8) | data[0]
        y = (data[3] << 8) | data[2]
        z = (data[5] << 8) | data[4]
        if x > 32767: x -= 65536
        if y > 32767: y -= 65536
        if z > 32767: z -= 65536
        return f"X:{x:6} Y:{y:6} Z:{z:6}"
    except Exception:
        return "Error"

def get_heading_str(course):
    if course == "N/A" or not course: return "---"
    try:
        deg = float(course)
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        return dirs[int((deg + 22.5) % 360 / 45)]
    except: return "---"

def main():
    print("--- Rocket GPS & Sensor Acquisition ---")
    mag_bus = setup_magnetometer()
    
    # Try different baud rates to find GPS
    ser = None
    for baud in BAUD_RATES:
        print(f"Checking baud rate {baud}...", end=" ", flush=True)
        try:
            temp_ser = serial.Serial(GPS_PORT, baudrate=baud, timeout=1)
            temp_ser.reset_input_buffer()
            data = temp_ser.read(100)
            if data and b'$G' in data:
                print(f"[OK] Found GPS!")
                temp_ser.timeout = 0.5
                ser = temp_ser
                break
            temp_ser.close()
            print("No signal.")
        except Exception:
            print("Port error.")

    if not ser:
        print("\n[!!] Could not connect to GPS module.")
        return

    # State variables
    latest_gps = {
        "time": "N/A", "sats": "0", "sats_view": "0",
        "alt": "N/A", "lat": "N/A", "lon": "N/A",
        "speed": "N/A", "course": "N/A",
        "fix_qual": 0, "last_seen": 0, "raw": ""
    }

    # Logging setup
    log_dir = "logs"
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, f"gps_{time.strftime('%Y%p%d_%H%M%S')}.txt")
    log_file = open(log_filename, "a")
    
    start_time = time.time()
    last_ui_update = 0

    try:
        while True:
            line = ser.readline().decode('ascii', errors='replace').strip()
            mag_str = read_magnetometer(mag_bus)
            
            if line:
                latest_gps["raw"] = line[:60]
                log_file.write(f"{time.time()},{line}\n")
                log_file.flush()

                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        latest_gps["last_seen"] = time.time()
                        if hasattr(msg, 'timestamp') and msg.timestamp:
                            latest_gps["time"] = str(msg.timestamp)

                        if isinstance(msg, pynmea2.types.talker.GGA):
                            latest_gps["sats"] = msg.num_sats
                            latest_gps["fix_qual"] = msg.gps_qual
                            if msg.gps_qual > 0:
                                latest_gps["lat"], latest_gps["lon"] = f"{msg.latitude:.6f}", f"{msg.longitude:.6f}"
                                latest_gps["alt"] = f"{msg.altitude} {msg.altitude_units}"
                        
                        elif isinstance(msg, pynmea2.types.talker.RMC) and msg.status == 'A':
                            latest_gps["lat"], latest_gps["lon"] = f"{msg.latitude:.6f}", f"{msg.longitude:.6f}"
                            latest_gps["speed"] = f"{msg.spd_over_grnd:.1f}"
                            latest_gps["course"] = f"{msg.true_course:.1f}" if msg.true_course else "0.0"

                        elif isinstance(msg, pynmea2.types.talker.GSV):
                            latest_gps["sats_view"] = msg.num_sv_in_view
                    except: pass

            # Update UI at 5Hz
            if time.time() - last_ui_update > 0.2:
                last_ui_update = time.time()
                alive = (time.time() - latest_gps["last_seen"]) < 2.0
                
                if not alive: status = "\033[1;91mOFFLINE\033[0m"
                elif latest_gps["fix_qual"] == 0: status = "\033[1;93mSEARCHING\033[0m"
                else: status = "\033[1;92mLOCKED\033[0m"

                uptime = int(time.time() - start_time)
                heading = get_heading_str(latest_gps["course"])

                print("\033[H", end="") 
                print("\033[1;36m" + "═"*50 + "\033[0m")
                print(f" \033[1mROCKET TELEMETRY\033[0m | UP: {uptime}s | STATUS: {status}")
                print("\033[1;36m" + "═"*50 + "\033[0m")
                print(f" TIME: {latest_gps['time']:15} | SATS: {latest_gps['sats']} (In View: {latest_gps['sats_view']})")
                print(f" MAG:  {mag_str}")
                print("\033[34m" + "─"*50 + "\033[0m")
                print(f" LAT:  {latest_gps['lat']:15} | LON: {latest_gps['lon']}")
                print(f" ALT:  {latest_gps['alt']:15}")
                print("\033[34m" + "─"*50 + "\033[0m")
                print(f" SPD:  {latest_gps['speed']:8} kn | CRS: {latest_gps['course']}° ({heading})")
                print("\033[1;36m" + "═"*50 + "\033[0m")
                print(f" \033[90mRAW: {latest_gps['raw'][:43]}\033[0m")
                print(f" \033[90mLOG: {os.path.basename(log_filename)}\033[0m")
                print(" \033[1;31m[Ctrl+C] TO EXIT\033[0m")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if ser: ser.close()
        if 'log_file' in locals(): log_file.close()

if __name__ == "__main__":
    main()
