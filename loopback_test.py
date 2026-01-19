import busio
import board
import time

print("--- SPI Loopback Test ---")
print("Connect Pin 19 (MOSI) to Pin 21 (MISO) with a single wire.")

try:
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    while not spi.try_lock():
        pass
    
    # 50kHz is very slow and stable
    spi.configure(baudrate=50000)
    
    test_bytes = bytearray([0xAA, 0x55, 0x10, 0x24])
    result = bytearray(len(test_bytes))
    
    spi.write_readinto(test_bytes, result)
    
    print(f"Sent:     {[hex(b) for b in test_bytes]}")
    print(f"Received: {[hex(b) for b in result]}")
    
    if test_bytes == result:
        print("\nSUCCESS: SPI Loopback works! The Pi hardware and software are OK.")
    else:
        print("\nFAILURE: Received data does not match. Check if you are on Pin 19 and 21.")

finally:
    try:
        spi.unlock()
        spi.deinit()
    except: pass
