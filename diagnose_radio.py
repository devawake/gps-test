import busio
import board
from digitalio import DigitalInOut, Direction
import time

# --- CONFIGURATION ---
# The user said they changed CS to GPIO 8 (Pin 24)
CS_PIN = board.D8 
RESET_PIN = board.D25
# ---------------------

def run_diag():
    print(f"--- Advanced Radio Diagnostic ---")
    print(f"Testing with CS=GPIO8 (Pin 24), RESET=GPIO25 (Pin 22)")
    
    # Initialize Pins
    reset = DigitalInOut(RESET_PIN)
    reset.direction = Direction.OUTPUT
    cs = DigitalInOut(CS_PIN)
    cs.direction = Direction.OUTPUT
    cs.value = True # Idle High

    # Hard Reset Sequence
    print("Performing hardware reset (Active High)...")
    reset.value = True
    time.sleep(0.2)
    reset.value = False
    time.sleep(0.2)

    # SPI Bus Initialization
    try:
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        while not spi.try_lock():
            pass
        print("SPI Bus initialized.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize SPI: {e}")
        return

    def spi_read(reg, speed=100000):
        spi.configure(baudrate=speed)
        # RFM69 Read: Bit 7 is 0. 
        # We send 2 bytes, we expect 2 bytes back.
        out_buf = bytearray([reg & 0x7F, 0x00])
        in_buf = bytearray(2)
        
        cs.value = False
        time.sleep(0.001) # Tiny delay for safety
        spi.write_readinto(out_buf, in_buf)
        cs.value = True
        return in_buf

    try:
        # Test 1: RFM69 Version (Expected 0x24)
        raw = spi_read(0x10)
        print(f"Read Reg 0x10 (at 100kHz): Sent [0x10, 0x00], Received [0x{raw[0]:02X}, 0x{raw[1]:02X}]")
        
        if raw[1] == 0xFF and raw[0] == 0xFF:
            print("\n[!] WARNING: Both bytes are 0xFF. This usually means MISO is disconnected or stuck High.")
        elif raw[1] == 0x00 and raw[0] == 0x00:
            print("\n[!] WARNING: Both bytes are 0x00. This usually means MISO is stuck Low or CS is not triggering.")
        
        # Test 2: Try higher speed
        raw_fast = spi_read(0x10, speed=1000000)
        print(f"Read Reg 0x10 (at 1MHz):   Sent [0x10, 0x00], Received [0x{raw_fast[0]:02X}, 0x{raw_fast[1]:02X}]")

        # Test 3: RFM9x Version (If it's a LoRa module)
        raw_lora = spi_read(0x42)
        print(f"Read Reg 0x42 (LoRa Check): Sent [0x42, 0x00], Received [0x{raw_lora[0]:02X}, 0x{raw_lora[1]:02X}]")

        print("\n--- Summary ---")
        if raw[1] == 0x24:
            print("FOUND: RFM69 Radio!")
        elif raw_lora[1] == 0x12:
            print("FOUND: RFM9x (LoRa) Radio!")
        else:
            print("No radio detected. Please check:")
            print("1. Is Pin 19 (MOSI) and Pin 21 (MISO) swapped?")
            print("2. Is Pin 24 (GPIO8) actually connected to the Radio CS pin?")
            print("3. Is the Radio VIN connected to 3.3V (Pin 1) and GND to (Pin 6)?")

    finally:
        spi.unlock()
        spi.deinit()

if __name__ == "__main__":
    run_diag()
