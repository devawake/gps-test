#!/usr/bin/env python3
"""
RFM69HCW Radio Connection Check Script
=======================================
Run this script on each Pi to verify the radio is connected and responding.

Usage: python3 radio_check.py
"""

import time
import board
import busio
import digitalio

# Try to import the RFM69 library
try:
    import adafruit_rfm69
except ImportError:
    print("❌ ERROR: adafruit-circuitpython-rfm69 not installed!")
    print("   Run: pip install adafruit-circuitpython-rfm69")
    exit(1)

# Radio configuration
RADIO_FREQ_MHZ = 433.0  # Frequency in MHz (433.0 for EU, 915.0 for US)

# Pin configuration (matching your wiring)
CS_PIN = board.D8       # GPIO8 - Chip Select
RESET_PIN = board.D25   # GPIO25 - Reset
IRQ_PIN = board.D24     # GPIO24 - Interrupt (G0)


def check_spi():
    """Check if SPI is available and working."""
    print("\n🔍 Checking SPI bus...")
    try:
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        print("   ✅ SPI bus initialized successfully")
        return spi
    except Exception as e:
        print(f"   ❌ SPI Error: {e}")
        print("\n   💡 Make sure SPI is enabled:")
        print("      1. Run: sudo raspi-config")
        print("      2. Go to: Interface Options -> SPI -> Enable")
        print("      3. Reboot the Pi")
        return None


def check_pins():
    """Check if we can access the GPIO pins."""
    print("\n🔍 Checking GPIO pins...")
    
    try:
        # Check CS pin
        cs = digitalio.DigitalInOut(CS_PIN)
        cs.direction = digitalio.Direction.OUTPUT
        print(f"   ✅ CS (GPIO8) - OK")
        
        # Check Reset pin
        reset = digitalio.DigitalInOut(RESET_PIN)
        reset.direction = digitalio.Direction.OUTPUT
        print(f"   ✅ RST (GPIO25) - OK")
        
        return cs, reset
    except Exception as e:
        print(f"   ❌ GPIO Error: {e}")
        return None, None


def check_radio(spi, cs, reset):
    """Try to initialize the RFM69 radio."""
    print("\n🔍 Checking RFM69 radio...")
    
    try:
        rfm69 = adafruit_rfm69.RFM69(spi, cs, reset, RADIO_FREQ_MHZ)
        print(f"   ✅ Radio initialized successfully!")
        print(f"   📻 Frequency: {RADIO_FREQ_MHZ} MHz")
        print(f"   📶 TX Power: {rfm69.tx_power} dBm")
        print(f"   🔧 Bitrate: {rfm69.bitrate} bps")
        return rfm69
    except RuntimeError as e:
        print(f"   ❌ Radio Error: {e}")
        print("\n   💡 Troubleshooting tips:")
        print("      1. Check your wiring (especially MISO/MOSI - they should NOT be crossed!)")
        print("      2. Ensure the radio is powered (VIN -> 3.3V)")
        print("      3. Check all connections are secure")
        print("      4. Try a different radio module if available")
        return None


def radio_self_test(rfm69):
    """Perform a basic self-test on the radio."""
    print("\n🔍 Running radio self-test...")
    
    # Test setting different TX power levels
    try:
        original_power = rfm69.tx_power
        for power in [-2, 0, 10, 20]:
            rfm69.tx_power = power
            print(f"   ✅ TX Power set to {power} dBm - OK")
        rfm69.tx_power = original_power
    except Exception as e:
        print(f"   ❌ TX Power test failed: {e}")
        return False
    
    # Test encryption key setting
    try:
        test_key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'
        rfm69.encryption_key = test_key
        print("   ✅ Encryption key set - OK")
        rfm69.encryption_key = None  # Disable for now
    except Exception as e:
        print(f"   ❌ Encryption test failed: {e}")
        return False
    
    print("\n✅ All self-tests passed!")
    return True


def main():
    print("=" * 50)
    print("   RFM69HCW Radio Connection Check")
    print("=" * 50)
    
    # Step 1: Check SPI
    spi = check_spi()
    if spi is None:
        print("\n❌ FAILED: SPI not available")
        return False
    
    # Step 2: Check GPIO pins
    cs, reset = check_pins()
    if cs is None or reset is None:
        print("\n❌ FAILED: GPIO pins not accessible")
        return False
    
    # Step 3: Check radio
    rfm69 = check_radio(spi, cs, reset)
    if rfm69 is None:
        print("\n❌ FAILED: Radio not responding")
        return False
    
    # Step 4: Self-test
    if not radio_self_test(rfm69):
        print("\n❌ FAILED: Self-test failed")
        return False
    
    print("\n" + "=" * 50)
    print("   🎉 RADIO CHECK COMPLETE - ALL OK!")
    print("=" * 50)
    print("\nNext steps:")
    print("   1. Run 'python3 radio_rx.py' on the receiver Pi")
    print("   2. Run 'python3 radio_tx.py' on the transmitter Pi")
    print("   3. Watch for messages being sent/received!")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        exit(0)
