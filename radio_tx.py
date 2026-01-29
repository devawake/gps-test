#!/usr/bin/env python3
"""
RFM69HCW Radio Transmitter Script
==================================
Run this on one Pi to send test messages.
Run radio_rx.py on the other Pi to receive them.

Usage: python3 radio_tx.py

If you get initialization errors after running radio_diag.py,
try rebooting the Pi first to release the SPI bus.
"""

import time
import sys

# ========================================
# CONFIGURATION - Modify as needed
# ========================================

RADIO_FREQ_MHZ = 433.0      # Must match receiver! (433.0 EU, 915.0 US)
TX_POWER = 20               # Transmit power in dBm (-2 to 20)
NODE_ID = 1                 # This node's ID
DEST_ID = 2                 # Destination node ID

# Encryption key (16 bytes) - Must match receiver!
# Set to None for no encryption
ENCRYPTION_KEY = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

# Message settings
SEND_INTERVAL = 2.0         # Seconds between messages

# ========================================


# def cleanup_gpio():
#     """Try to cleanup any existing GPIO usage."""
#     try:
#         import RPi.GPIO as GPIO
#         GPIO.setwarnings(False)
#         GPIO.cleanup()
#         print("   🧹 Cleaned up previous GPIO state")
#     except:
#         pass


def setup_radio():
    """Initialize the RFM69 radio with deep diagnostics."""
    print("🔧 Initializing radio...")
    
    # 1. System-level checks
    import os
    import subprocess
    
    # Check for spidev
    spi_devs = [f for f in os.listdir('/dev') if f.startswith('spidev')]
    print(f"   📂 SPI Devices: {spi_devs}")
    
    # Check for pigpiod conflict
    try:
        pg_check = subprocess.check_output(["pgrep", "pigpiod"]).decode().strip()
        print(f"   ⚠️  Warning: pigpiod is running (PID {pg_check}). This can interfere with GPIO!")
    except:
        pass

    # 2. Imports
    try:
        import board
        import busio
        import digitalio
        import adafruit_rfm69
        import RPi.GPIO as GPIO
    except ImportError as e:
        print(f"   ❌ Missing library: {e}")
        sys.exit(1)
    
    # Pin configuration
    CS_PIN = board.D8           # GPIO8 - Chip Select
    RESET_PIN = board.D25       # GPIO25 - Reset
    
    try:
        # 3. Setup SPI (standard SPI0)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        
        # 4. Setup Reset Pin
        # We'll use the library's pin object
        reset = digitalio.DigitalInOut(RESET_PIN)
        reset.direction = digitalio.Direction.OUTPUT
        
        # 5. Hardware Reset (Datasheet process)
        print("   🔄 Resetting radio hardware...")
        reset.value = True
        time.sleep(0.1)
        reset.value = False
        time.sleep(0.2)  # Wait for radio to wake up
        
        # 6. Setup CS Pin
        cs = digitalio.DigitalInOut(CS_PIN)
        cs.direction = digitalio.Direction.OUTPUT
        cs.value = True
        
        # 7. MANUAL DIAGNOSTIC CHECK
        # Try to read the version register manually before the library starts
        print("   � Performing manual version check (1MHz)...")
        version = 0x00
        while not spi.try_lock():
            pass
        try:
            spi.configure(baudrate=1000000, polarity=0, phase=0)
            cs.value = False
            # Read Reg 0x10: Send 0x10, then read response
            spi.write(bytearray([0x10 & 0x7F]))
            result = bytearray(1)
            spi.readinto(result)
            version = result[0]
            cs.value = True
        finally:
            spi.unlock()
            
        print(f"   📖 Manual read of Reg 0x10: {hex(version)}")
        
        if version != 0x24:
            print(f"   ⚠️  Manual check failed! Expected 0x24, got {hex(version)}.")
            if version == 0x00:
                print("      (Probable MISO connection issue or CS conflict)")
            elif version == 0xFF:
                print("      (Probable MOSI/SCK connection issue)")
        
        # 8. Initialize library
        print("   🚀 Initializing RFM69 library...")
        # We pass reset=None because we already handled it manually and stably
        rfm69 = adafruit_rfm69.RFM69(spi, cs, None, RADIO_FREQ_MHZ, baudrate=1000000)
        
        # Configure radio
        rfm69.tx_power = TX_POWER
        rfm69.node = NODE_ID
        rfm69.destination = DEST_ID
        
        if ENCRYPTION_KEY:
            rfm69.encryption_key = ENCRYPTION_KEY
            print("   🔐 Encryption enabled")
        
        print(f"   📻 Frequency: {RADIO_FREQ_MHZ} MHz")
        print(f"   🏷️  Node ID: {NODE_ID} -> Target ID: {DEST_ID}")
        
        return rfm69
        
    except RuntimeError as e:
        print(f"\n   ❌ Radio initialization error: {e}")
        return None
    except Exception as e:
        print(f"\n   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 50)
    print("   RFM69HCW Radio Transmitter")
    print("=" * 50)
    
    rfm69 = setup_radio()
    if rfm69 is None:
        print("\n❌ Failed to initialize radio.")
        sys.exit(1)
    
    print(f"\n✅ Radio ready! Sending messages every {SEND_INTERVAL}s")
    print("   Press Ctrl+C to stop\n")
    print("-" * 50)
    
    msg_count = 0
    
    try:
        while True:
            msg_count += 1
            
            # Create message with timestamp and counter
            message = f"Hello from Node {NODE_ID}! Msg #{msg_count}"
            
            print(f"\n📤 Sending message #{msg_count}...")
            print(f"   Message: '{message}'")
            
            # Send the message
            start_time = time.monotonic()
            rfm69.send(
                bytes(message, "utf-8"),
                destination=DEST_ID,
                node=NODE_ID,
                identifier=msg_count % 256,
                flags=0
            )
            send_time = (time.monotonic() - start_time) * 1000
            
            print(f"   ✅ Sent! (took {send_time:.1f}ms)")
            
            # Check for acknowledgment/reply
            print("   👂 Listening for reply...")
            reply = rfm69.receive(timeout=1.0)
            
            if reply is not None:
                # Try to decode as text
                try:
                    reply_text = reply.decode("utf-8")
                except:
                    reply_text = str(reply)
                
                print(f"   📥 Reply received: '{reply_text}'")
                print(f"   📶 RSSI: {rfm69.last_rssi} dBm")
            else:
                print("   ⏳ No reply (this is normal if receiver isn't set up to reply)")
            
            # Wait before next message
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print(f"   Stopped! Sent {msg_count} messages.")
        print("=" * 50)


if __name__ == "__main__":
    main()
