#!/usr/bin/env python3
"""
Avionics Transmitter Script (Pi Zero 2W)
=========================================
This script runs on the rocket avionics (Pi Zero 2W) and continuously
transmits test messages to the ground station.

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
NODE_ID = 1             # This node (avionics)
DESTINATION_ID = 2      # Ground station node
ENCRYPTION_KEY = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

# Transmission settings
TX_POWER = 20           # dBm (max 20 for RFM69HCW)
TX_INTERVAL = 2.0       # Seconds between transmissions


def setup_radio():
    """Initialize the RFM69 radio module."""
    print("=" * 50)
    print("AVIONICS TRANSMITTER (Pi Zero 2W)")
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
    
    # Set encryption key (must match receiver!)
    rfm69.encryption_key = ENCRYPTION_KEY
    print("      ✓ Encryption key set")
    
    # Set transmit power
    rfm69.tx_power = TX_POWER
    print(f"      ✓ TX power: {TX_POWER} dBm")
    
    # Set node addresses
    rfm69.node = NODE_ID
    rfm69.destination = DESTINATION_ID
    print(f"      ✓ Node ID: {NODE_ID} -> Destination: {DESTINATION_ID}")
    
    print("\n" + "=" * 50)
    print("RADIO READY - Starting transmission...")
    print("=" * 50 + "\n")
    
    return rfm69


def main():
    """Main transmission loop."""
    rfm69 = setup_radio()
    if rfm69 is None:
        return
    
    packet_count = 0
    
    print("Press Ctrl+C to stop transmitting\n")
    
    try:
        while True:
            packet_count += 1
            
            # Create message with timestamp and counter
            timestamp = time.strftime("%H:%M:%S")
            message = f"AVIONICS #{packet_count} @ {timestamp}"
            
            print(f"[TX] Sending: {message}")
            
            # Convert to bytes and send
            rfm69.send(bytes(message, "utf-8"))
            
            print(f"     ✓ Packet #{packet_count} sent!")
            
            # Wait before next transmission
            time.sleep(TX_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\nTransmission stopped. Total packets sent: {packet_count}")
        print("Goodbye!")


if __name__ == "__main__":
    main()
