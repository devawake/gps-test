import busio
import board
from digitalio import DigitalInOut, Direction
import time

# Pin configuration
CS_PIN = board.D5
RESET_PIN = board.D25

print(f"Starting Radio Diagnostic...")
print(f"Target Pins: CS=GPIO5, RESET=GPIO25")

# Initialize Pins
reset = DigitalInOut(RESET_PIN)
reset.direction = Direction.OUTPUT
cs = DigitalInOut(CS_PIN)
cs.direction = Direction.OUTPUT
cs.value = True

# Perform Reset
print("Resetting radio...")
reset.value = True
time.sleep(0.1)
reset.value = False
time.sleep(0.1)

# Initialize SPI
try:
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    while not spi.try_lock():
        pass
    spi.configure(baudrate=1000000) # 1MHz
    print("SPI Bus initialized and locked.")
except Exception as e:
    print(f"Failed to initialize SPI: {e}")
    exit()

def read_register(reg):
    # For RFM69, to read: bit 7 is 0.
    # Buffer: [Address, 0x00]
    out_buf = bytearray([reg & 0x7F, 0x00])
    in_buf = bytearray(2)
    cs.value = False
    spi.write_readinto(out_buf, in_buf)
    cs.value = True
    return in_buf[1]

try:
    # Try reading Version register for RFM69 (0x10)
    rfm69_ver = read_register(0x10)
    print(f"Register 0x10 (RFM69 Version) returned: 0x{rfm69_ver:02X}")
    
    # Try reading Version register for RFM9x (0x42)
    rfm9x_ver = read_register(0x42)
    print(f"Register 0x42 (RFM9x Version) returned: 0x{rfm9x_ver:02X}")

    if rfm69_ver == 0x24:
        print("SUCCESS: Found RFM69 (Version 0x24)")
    elif rfm9x_ver == 0x12:
        print("SUCCESS: Found RFM9x LoRa (Version 0x12)")
    elif rfm69_ver == 0x00 or rfm69_ver == 0xFF:
        print("FAILURE: Connection issue. All bits are High or Low. Check CS, SCK, MISO, MOSI and Power.")
    else:
        print("UNKNOWN: Received unexpected version. Maybe wiring is noisy or chip is different.")

finally:
    spi.unlock()
    spi.deinit()
