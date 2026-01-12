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
        print(f"Checking baud rate {baud}...")
        try:
            temp_ser = serial.Serial(GPS_PORT, baudrate=baud, timeout=2)
            # Wait for some data
            start_time = time.time()
            valid_nmea = False
            while time.time() - start_time < 3:
                line = temp_ser.readline().decode('ascii', errors='replace')
                if '$G' in line:
                    valid_nmea = True
                    break
            
            if valid_nmea:
                print(f"[OK] Valid NMEA data found at {baud} baud.")
                ser = temp_ser
                break
            else:
                temp_ser.close()
        except Exception as e:
            print(f"Failed to open {GPS_PORT} at {baud}: {e}")

    if not ser:
        print("[ERROR] Could not find GPS data on any standard baud rate.")
        print("Ensure UART is enabled in raspi-config and wiring is correct.")
        return

    print("\nStarting live view... (Ctrl+C to quit)")
    time.sleep(1)

    try:
        while True:
            line = ser.readline().decode('ascii', errors='replace').strip()
            mag_str = read_magnetometer(mag_bus)
            
            if line.startswith('$G'):
                try:
                    msg = pynmea2.parse(line)
                    if isinstance(msg, (pynmea2.types.talker.GGA, pynmea2.types.talker.RMC)):
                        # clear_screen() # Uncomment for a cleaner persistent look
                        timestamp = getattr(msg, 'timestamp', 'N/A')
                        
                        if isinstance(msg, pynmea2.types.talker.GGA):
                            print(f"[{timestamp}] SATS: {msg.num_sats} | ALT: {msg.altitude} {msg.altitude_units} | MAG: {mag_str}")
                            print(f"      POS: {msg.latitude}, {msg.longitude}")
                        
                        elif isinstance(msg, pynmea2.types.talker.RMC):
                            print(f"[{timestamp}] SPD: {msg.speed} kn | CRS: {msg.true_course} | MAG: {mag_str}")
                
                except pynmea2.ParseError:
                    pass
            
            # If no GPS line but we want to see Mag
            elif not line:
                # print(f"Waiting for GPS... | MAG: {mag_str}", end='\r')
                pass

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if ser: ser.close()
        if mag_bus: mag_bus.close()

if __name__ == "__main__":
    main()
