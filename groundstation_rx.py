#!/usr/bin/env python3
"""
Ground Station Receiver Script (Pi 4B)
=======================================
This script runs on the ground station (Pi 4B) and listens for
messages from the rocket avionics.

Wiring (per Wiring.md):
    VIN  -> Pin 1  (3.3V)
    GND  -> Pin 6  (GND)
    G0   -> Pin 18 (GPIO24) - Interrupt
    SCK  -> Pin 23 (GPIO11) - SPI Clock
    MISO -> Pin 21 (GPIO9)  - SPI MISO
    MOSI -> Pin 19 (GPIO10) - SPI MOSI
    CS   -> Pin 24 (GPIO8)  - SPI CE0
    RST  -> Pin 22 (GPIO25) - Reset
"""

import time
import board
import busio
import digitalio
import adafruit_rfm69

# ============================================
# CONFIGURATION - MUST MATCH ON BOTH RADIOS!
# ============================================
RADIO_FREQ_MHZ = 433.0  # 433 MHz
NODE_ID = 2             # This node (ground station)
ENCRYPTION_KEY = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

# Receiver settings
RX_TIMEOUT = 5.0        # Seconds to wait for a packet


def setup_radio():
    """Initialize the RFM69 radio module."""
    print("=" * 50)
    print("GROUND STATION RECEIVER (Pi 4B)")
    print("=" * 50)
    print("\n[1/4] Setting up SPI bus...")
    
    # Initialize SPI
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    
    print("[2/4] Configuring GPIO pins...")
    
    # Chip Select (CS) pin
    cs = digitalio.DigitalInOut(board.CE0)
    cs.direction = digitalio.Direction.OUTPUT
    cs.value = True
    
    # Reset pin
    reset = digitalio.DigitalInOut(board.D25)
    reset.direction = digitalio.Direction.OUTPUT
    
    print("[3/4] Initializing RFM69 radio...")
    
    try:
        rfm69 = adafruit_rfm69.RFM69(spi, cs, reset, RADIO_FREQ_MHZ)
        print(f"      ✓ Radio initialized at {RADIO_FREQ_MHZ} MHz")
    except RuntimeError as e:
        print(f"      ✗ Failed to initialize radio: {e}")
        print("\n[TROUBLESHOOTING]")
        print("  1. Check wiring matches Wiring.md")
        print("  2. Ensure SPI is enabled (sudo raspi-config)")
        print("  3. Verify 3.3V power (NOT 5V!)")
        return None
    
    print("[4/4] Configuring radio settings...")
    
    # Set encryption key (must match transmitter!)
    rfm69.encryption_key = ENCRYPTION_KEY
    print("      ✓ Encryption key set")
    
    # Set node address
    rfm69.node = NODE_ID
    print(f"      ✓ Node ID: {NODE_ID}")
    
    print("\n" + "=" * 50)
    print("RADIO READY - Listening for packets...")
    print("=" * 50 + "\n")
    
    return rfm69


def main():
    """Main receive loop."""
    rfm69 = setup_radio()
    if rfm69 is None:
        return
    
    packets_received = 0
    start_time = time.time()
    
    print("Waiting for messages from avionics...")
    print("Press Ctrl+C to stop listening\n")
    print("-" * 50)
    
    try:
        while True:
            # Wait for a packet with timeout
            packet = rfm69.receive(timeout=RX_TIMEOUT)
            
            if packet is not None:
                packets_received += 1
                
                # Try to decode the message
                try:
                    message = packet.decode("utf-8")
                except UnicodeDecodeError:
                    message = f"<raw bytes: {packet.hex()}>"
                
                # Get signal strength (RSSI)
                rssi = rfm69.last_rssi
                
                # Display received message
                timestamp = time.strftime("%H:%M:%S")
                print(f"[RX] {timestamp} | RSSI: {rssi} dBm")
                print(f"     Message: {message}")
                print(f"     Packets received: {packets_received}")
                print("-" * 50)
            else:
                # No packet received within timeout
                elapsed = int(time.time() - start_time)
                print(f"[...] No signal (listening for {elapsed}s, received: {packets_received})")
                
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n\nReceiver stopped after {elapsed:.1f} seconds")
        print(f"Total packets received: {packets_received}")
        print("Goodbye!")


if __name__ == "__main__":
    main()
