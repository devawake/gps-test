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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("--- Rocket GPS & Sensor Acquisition ---")
    mag_bus = setup_magnetometer()
    if mag_bus:
        print("[OK] Magnetometer detected.")
    else:
        print("[!!] Magnetometer NOT found on I2C.")

    # Try different baud rates
    ser = None
    for baud in BAUD_RATES:
        print(f"Checking baud rate {baud}...", end=" ", flush=True)
        try:
            # Short timeout for scanning
            temp_ser = serial.Serial(GPS_PORT, baudrate=baud, timeout=1)
            
            # Flush buffers
            temp_ser.reset_input_buffer()
            
            # Read a chunk of data
            data = temp_ser.read(100) # Read up to 100 bytes
            
            if not data:
                print("No data received.")
                temp_ser.close()
                continue
            
            # Convert to string to check for NMEA markers
            decoded_data = data.decode('ascii', errors='replace')
            if '$G' in decoded_data:
                print(f"[OK] Valid NMEA data found!")
                # Re-open with a slightly longer timeout for stable reading
                temp_ser.timeout = 0.5
                ser = temp_ser
                break
            else:
                print(f"Data received but not NMEA: {repr(decoded_data[:20])}...")
                temp_ser.close()
                
        except Exception as e:
            print(f"Error: {e}")

    if not ser:
        print("\n" + "="*40)
        print("DIAGNOSTICS & TROUBLESHOOTING:")
        print("1. WIRING: Ensure GPS 'T' is connected to Pi GPIO 15 (RX).")
        print("2. WIRING: Ensure GPS 'R' is connected to Pi GPIO 14 (TX).")
        print("3. POWER: Check if the LED on the GPS module is on.")
        print("4. CONFIG: Did you run 'sudo raspi-config' and DISABLE the Serial Console?")
        print("   (Check /boot/firmware/cmdline.txt - it should NOT contain 'console=serial0')")
        print("5. PINOUT: Verify you are using Physical Pins 8 and 10.")
        print("="*40)
        return

    print("\nStarting live view... (Ctrl+C to quit)")
    time.sleep(1)

    # State variables
    latest_gps = {
        "time": "N/A",
        "sats": "0",
        "sats_in_view": "0",
        "alt": "N/A",
        "lat": "N/A",
        "lon": "N/A",
        "speed": "N/A",
        "course": "N/A",
        "fix_quality": 0,
        "last_seen": 0,
        "raw": ""
    }

    # Logging setup
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, f"gps_log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    log_file = open(log_filename, "a")
    print(f"[INFO] Logging to {log_filename}")
    
    last_ui_update = 0

    try:
        while True:
            # Short serial timeout ensures we can catch KeyboardInterrupt frequently
            line = ser.readline().decode('ascii', errors='replace').strip()
            mag_str = read_magnetometer(mag_bus)
            
            if line:
                latest_gps["raw"] = line[:60] # Store preview
                # Log raw data with local system time
                log_file.write(f"{time.time()},{line}\n")
                log_file.flush()

                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        latest_gps["last_seen"] = time.time()
                        
                        # Use timestamp from GPS if available
                        if hasattr(msg, 'timestamp') and msg.timestamp:
                            latest_gps["time"] = str(msg.timestamp)

                        if isinstance(msg, pynmea2.types.talker.GGA):
                            latest_gps["sats"] = getattr(msg, 'num_sats', latest_gps["sats"])
                            latest_gps["fix_quality"] = msg.gps_qual
                            # Only update position if we have a fix (quality > 0)
                            if msg.gps_qual > 0:
                                latest_gps["lat"] = f"{msg.latitude:.6f}"
                                latest_gps["lon"] = f"{msg.longitude:.6f}"
                                latest_gps["alt"] = f"{msg.altitude} {msg.altitude_units}"
                        
                        elif isinstance(msg, pynmea2.types.talker.RMC):
                            # Status 'A' means Active (valid), 'V' means Void (invalid)
                            if msg.status == 'A':
                                latest_gps["lat"] = f"{msg.latitude:.6f}"
                                latest_gps["lon"] = f"{msg.longitude:.6f}"
                                latest_gps["speed"] = f"{msg.spd_over_grnd:.1f}"
                                latest_gps["course"] = f"{msg.true_course:.1f}" if msg.true_course else "0.0"

                        elif isinstance(msg, pynmea2.types.talker.GSV):
                            latest_gps["sats_in_view"] = getattr(msg, 'num_sv_in_view', latest_gps["sats_in_view"])
                    
                    except (pynmea2.ParseError, AttributeError, ValueError):
                        pass

            # Update UI at ~5Hz to keep it readable and responsive
            if time.time() - last_ui_update > 0.2:
                last_ui_update = time.time()
                
                # Connection status check
                gps_alive = (time.time() - latest_gps["last_seen"]) < 2.0
                if not gps_alive:
                    status_text = "\033[91m[ OFFLINE ]\033[0m"
                elif latest_gps["fix_quality"] == 0:
                    status_text = "\033[93m[ SEARCHING ]\033[0m"
                else:
                    status_text = "\033[92m[ LOCKED ]\033[0m"

                # Clear screen (Move cursor to top-left)
                print("\033[H", end="") 
                print("========================================")
                print(f" ROCKET TELEMETRY     STATUS: {status_text}")
                print("========================================")
                print(f" GPS TIME:   {latest_gps['time']:15}")
                print(f" SATELLITES: {latest_gps['sats']} (In View: {latest_gps['sats_in_view']})")
                print(f" MAG DATA:   {mag_str}")
                print("----------------------------------------")
                print(f" LATITUDE:   {latest_gps['lat']:15}")
                print(f" LONGITUDE:  {latest_gps['lon']:15}")
                print(f" ALTITUDE:   {latest_gps['alt']:15}")
                print("----------------------------------------")
                print(f" SPEED:      {latest_gps['speed']:7} kn | CRS: {latest_gps['course']}°")
                print("----------------------------------------")
                print(f" RAW: {latest_gps['raw'][:34]:34}")
                print("========================================")
                print(f" LOGGING TO: {log_filename}")
                print(" [Ctrl+C] to Exit")

    except KeyboardInterrupt:
        print("\nStopping telemetry...")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        if ser: ser.close()
        if mag_bus: mag_bus.close()
        if 'log_file' in locals(): log_file.close()

if __name__ == "__main__":
    main()
