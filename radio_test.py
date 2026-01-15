import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_rfm69

# --- CONFIGURATION ---
# Set the frequency to match your hardware (433.0 or 915.0)
FREQUENCY = 915.0

# Pin configuration for Raspberry Pi
# Default wiring for Adafruit RFM69HCW Breakout:
# RFM69 CS  -> Pi GPIO 5
# RFM69 RST -> Pi GPIO 25
CS = DigitalInOut(board.D5)
RESET = DigitalInOut(board.D25)

# SPI Bus setup
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize RFM69 radio
try:
    rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, FREQUENCY)
    print(f"RFM69 radio initialized on {FREQUENCY}MHz")
except Exception as e:
    print(f"Failed to initialize RFM69: {e}")
    print("Check your wiring and ensure SPI is enabled in raspi-config.")
    exit()

# Optional: Set high power for HCW modules (True for HCW, False for non-H)
rfm69.high_power = True

def run_sender():
    print("Starting Sender Mode...")
    counter = 0
    while True:
        message = f"Hello from Pi! Count: {counter}"
        print(f"Sending: {message}")
        rfm69.send(bytes(message, "utf-8"))
        counter += 1
        time.sleep(2)

def run_receiver():
    print("Starting Receiver Mode (Waiting for messages)...")
    while True:
        packet = rfm69.receive(timeout=5.0)
        if packet is None:
            print("Waiting...")
        else:
            try:
                message = str(packet, "utf-8")
                print(f"Received (RSSI {rfm69.last_rssi}dBm): {message}")
            except Exception:
                print(f"Received raw bytes: {packet}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 radio_test.py [send|receive]")
    elif sys.argv[1].lower() == "send":
        run_sender()
    elif sys.argv[1].lower() == "receive":
        run_receiver()
    else:
        print("Invalid argument. Use 'send' or 'receive'.")
