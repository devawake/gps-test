import busio
import board
from digitalio import DigitalInOut
import time

# Use GPIO 8 (Pin 24)
CS_PIN = board.D8

print("--- Final Radio Identification Test ---")
print("Note: Reset wire should be DISCONNECTED for this test.")

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(CS_PIN)
cs.direction = Direction.OUTPUT
cs.value = True

try:
    while not spi.try_lock():
        pass
    spi.configure(baudrate=100000)
    
    # Try reading the version 10 times
    for i in range(5):
        cs.value = False
        out_buf = bytearray([0x10, 0x00])
        in_buf = bytearray(2)
        spi.write_readinto(out_buf, in_buf)
        cs.value = True
        
        print(f"Attempt {i+1}: Received 0x{in_buf[1]:02X}")
        if in_buf[1] == 0x24:
            print("\nSUCCESS! Radio Found.")
            break
        time.sleep(0.5)
    else:
        print("\nStill 0xFF. Please swap MISO/MOSI wires and try once more.")

finally:
    spi.unlock()
    spi.deinit()
