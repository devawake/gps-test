import board
import busio
import digitalio
import time

def test():
    print("Testing SPI with Adafruit Blinka...")
    try:
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        cs = digitalio.DigitalInOut(board.D8)
        cs.direction = digitalio.Direction.OUTPUT
        cs.value = True
        
        reset = digitalio.DigitalInOut(board.D25)
        reset.direction = digitalio.Direction.OUTPUT
        
        # Manual Reset
        print("Resetting radio...")
        reset.value = True
        time.sleep(0.1)
        reset.value = False
        time.sleep(0.1)
        
        def read_reg(reg):
            cs.value = False
            # Read: Address with bit 7 = 0
            out_buf = bytearray([reg & 0x7F, 0x00])
            in_buf = bytearray(2)
            spi.try_lock()
            spi.configure(baudrate=100000, polarity=0, phase=0)
            spi.write_readinto(out_buf, in_buf)
            spi.unlock()
            cs.value = True
            return in_buf[1]

        for i in range(5):
            val = read_reg(0x10)
            print(f"Attempt {i+1}: Version = {hex(val)}")
            time.sleep(0.1)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
