#!/usr/bin/env python3
"""
RFM69HCW Radio Receiver Script
===============================
Run this on one Pi to receive test messages.
Run radio_tx.py on the other Pi to send them.

Usage: python3 radio_rx.py
"""

import time
import board
import busio
import digitalio
import adafruit_rfm69

# ========================================
# CONFIGURATION - Modify as needed
# ========================================

RADIO_FREQ_MHZ = 433.0      # Must match transmitter! (433.0 EU, 915.0 US)
TX_POWER = 20               # Transmit power for replies (-2 to 20)
NODE_ID = 2                 # This node's ID (should be DEST_ID on TX)
LISTEN_TO = 1               # Node to listen for (NODE_ID on TX)

# Encryption key (16 bytes) - Must match transmitter!
# Set to None for no encryption
ENCRYPTION_KEY = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

# Pin configuration
CS_PIN = board.D8           # GPIO8 - Chip Select
RESET_PIN = board.D25       # GPIO25 - Reset

# Reply settings
SEND_REPLY = True           # Set to True to send acknowledgment replies
RECEIVE_TIMEOUT = 5.0       # Seconds to wait before showing "waiting" message

# ========================================


def setup_radio():
    """Initialize the RFM69 radio."""
    print("🔧 Initializing radio...")
    
    # Setup SPI
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    
    # Setup pins
    cs = digitalio.DigitalInOut(CS_PIN)
    reset = digitalio.DigitalInOut(RESET_PIN)
    
    # Initialize radio
    rfm69 = adafruit_rfm69.RFM69(spi, cs, reset, RADIO_FREQ_MHZ)
    
    # Configure radio
    rfm69.tx_power = TX_POWER
    rfm69.node = NODE_ID
    rfm69.destination = LISTEN_TO
    
    if ENCRYPTION_KEY:
        rfm69.encryption_key = ENCRYPTION_KEY
        print("   🔐 Encryption enabled")
    
    print(f"   📻 Frequency: {RADIO_FREQ_MHZ} MHz")
    print(f"   🏷️  Node ID: {NODE_ID}, listening for Node {LISTEN_TO}")
    print(f"   📨 Reply mode: {'ON' if SEND_REPLY else 'OFF'}")
    
    return rfm69


def main():
    print("=" * 50)
    print("   RFM69HCW Radio Receiver")
    print("=" * 50)
    
    try:
        rfm69 = setup_radio()
    except Exception as e:
        print(f"\n❌ Failed to initialize radio: {e}")
        print("   Run 'python3 radio_check.py' to diagnose issues.")
        return
    
    print("\n✅ Radio ready! Waiting for messages...")
    print("   Press Ctrl+C to stop\n")
    print("-" * 50)
    
    msg_count = 0
    last_activity = time.monotonic()
    
    try:
        while True:
            # Listen for incoming packet
            packet = rfm69.receive(timeout=1.0)
            
            if packet is not None:
                msg_count += 1
                last_activity = time.monotonic()
                
                # Get signal strength
                rssi = rfm69.last_rssi
                
                # Try to decode as text
                try:
                    message = packet.decode("utf-8")
                except:
                    message = str(packet)
                
                # Display received message
                print(f"\n📥 Message #{msg_count} received!")
                print(f"   📝 Content: '{message}'")
                print(f"   📶 RSSI: {rssi} dBm", end="")
                
                # Signal strength indicator
                if rssi > -50:
                    print(" (Excellent 📶📶📶📶)")
                elif rssi > -70:
                    print(" (Good 📶📶📶)")
                elif rssi > -90:
                    print(" (Fair 📶📶)")
                else:
                    print(" (Weak 📶)")
                
                print(f"   ⏱️  Time: {time.strftime('%H:%M:%S')}")
                
                # Send acknowledgment reply
                if SEND_REPLY:
                    reply = f"ACK from Node {NODE_ID} - Got msg #{msg_count}"
                    print(f"   📤 Sending reply: '{reply}'")
                    rfm69.send(
                        bytes(reply, "utf-8"),
                        destination=LISTEN_TO,
                        node=NODE_ID
                    )
                    print("   ✅ Reply sent!")
                
            else:
                # No message received - show periodic status
                elapsed = time.monotonic() - last_activity
                if elapsed > RECEIVE_TIMEOUT:
                    print(f"\r⏳ Waiting for messages... ({int(elapsed)}s since last)", end="", flush=True)
                    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print(f"   Stopped! Received {msg_count} messages.")
        print("=" * 50)


if __name__ == "__main__":
    main()
