import busio
import board
from digitalio import DigitalInOut, Direction
import time

def test_pin(cs_pin_obj, pin_name, reset_pin_obj):
    print(f"\n--- Testing {pin_name} ---")
    
    # Setup CS
    cs = DigitalInOut(cs_pin_obj)
    cs.direction = Direction.OUTPUT
    cs.value = True
    
    # Setup Reset
    reset = DigitalInOut(reset_pin_obj)
    reset.direction = Direction.OUTPUT
    reset.value = False
    
    # Attempt Reset
    reset.value = True
    time.sleep(0.1)
    reset.value = False
    time.sleep(0.1)

    try:
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        while not spi.try_lock():
            pass
        spi.configure(baudrate=100000)
        
        # Read Reg 0x10
        out_buf = bytearray([0x10, 0x00])
        in_buf = bytearray(2)
        
        cs.value = False
        spi.write_readinto(out_buf, in_buf)
        cs.value = True
        
        print(f"Result on {pin_name}: Sent [0x10, 0x00], Received [0x{in_buf[0]:02X}, 0x{in_buf[1]:02X}]")
        
        if in_buf[1] == 0x24:
            print(f"!!! SUCCESS !!! FOUND RFM69 ON {pin_name}")
            return True
        return False
    except Exception as e:
        print(f"Error testing {pin_name}: {e}")
        return False
    finally:
        try:
            spi.unlock()
            spi.deinit()
        except: pass

print("Scanning common CS pins...")
found = test_pin(board.D8, "GPIO 8 (Pin 24)", board.D25)
if not found:
    found = test_pin(board.D5, "GPIO 5 (Pin 29)", board.D25)
if not found:
    found = test_pin(board.D7, "GPIO 7 (Pin 26)", board.D25)

if not found:
    print("\nNo radio found on any pin. Please perform the Loopback Test (MISO to MOSI) to verify the Pi.")
