import busio
import board
from digitalio import DigitalInOut, Direction
import time

# User is using GPIO 8 (Pin 24)
CS_PIN = board.D8
RESET_PIN = board.D25

def check_echo():
    print("--- Echo & CS Diagnostic ---")
    
    cs = DigitalInOut(CS_PIN)
    cs.direction = Direction.OUTPUT
    cs.value = True # Idle High
    
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    while not spi.try_lock():
        pass
    spi.configure(baudrate=100000)

    def exchange(val):
        out_b = bytearray([val])
        in_b = bytearray(1)
        spi.write_readinto(out_b, in_b)
        return in_b[0]

    print("\n1. Testing for Echo (CS is HIGH/Idle):")
    e1 = exchange(0x55)
    e2 = exchange(0xAA)
    print(f"   Sent 0x55, Received 0x{e1:02X}")
    print(f"   Sent 0xAA, Received 0x{e2:02X}")
    
    if e1 == 0x55 and e2 == 0xAA:
        print("   [!] INTERNAL ECHO DETECTED. MISO and MOSI are likely shorted together.")
        print("       Check your wiring for a bridge between Pin 19 and 21.")
    
    print("\n2. Testing Radio Version (CS is LOW/Active):")
    cs.value = False
    time.sleep(0.01)
    # Read Reg 0x10 (Version)
    # Send Reg, then send 0x00 to read back.
    exchange(0x10 & 0x7F)
    ver = exchange(0x00)
    cs.value = True
    
    print(f"   Radio Version Register returned: 0x{ver:02X}")
    
    if ver == 0x24:
        print("\n!!! SUCCESS !!! RADIO FOUND (RFM69)")
    elif ver == 0x12:
        print("\n!!! SUCCESS !!! RADIO FOUND (RFM9x LoRa)")
    elif ver == 0x00:
        print("\n[!] Radio is silent (0x00). Check Power and RESET pin.")
    else:
        print("\n[!] Unexpected value. If it matches the last byte sent, CS is not working.")

    spi.unlock()
    spi.deinit()

if __name__ == "__main__":
    check_echo()
