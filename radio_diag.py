#!/usr/bin/env python3
"""
Radio Diagnostic Script
=======================
Run this on EACH Pi to verify the RFM69HCW radio is properly connected
and initialized before testing communication.

This checks:
1. SPI bus availability
2. GPIO pin configuration
3. Radio chip detection and version
4. Basic radio initialization
"""

import time

def check_spi():
    """Check if SPI is available."""
    print("\n[1] Checking SPI bus...")
    try:
        import board
        import busio
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        print("    ✓ SPI bus initialized successfully")
        print(f"    ✓ SCK:  {board.SCK}")
        print(f"    ✓ MOSI: {board.MOSI}")
        print(f"    ✓ MISO: {board.MISO}")
        return spi
    except Exception as e:
        print(f"    ✗ SPI initialization failed: {e}")
        print("\n    [FIX] Enable SPI:")
        print("          sudo raspi-config -> Interface Options -> SPI -> Enable")
        return None


def check_gpio():
    """Check GPIO pin configuration."""
    print("\n[2] Checking GPIO pins...")
    try:
        import board
        import digitalio
        
        # Test CS pin (CE0)
        cs = digitalio.DigitalInOut(board.CE0)
        cs.direction = digitalio.Direction.OUTPUT
        cs.value = True
        print(f"    ✓ CS (CE0): OK")
        
        # Test Reset pin (D25/GPIO25)
        reset = digitalio.DigitalInOut(board.D25)
        reset.direction = digitalio.Direction.OUTPUT
        print(f"    ✓ RST (GPIO25): OK")
        
        return cs, reset
    except Exception as e:
        print(f"    ✗ GPIO configuration failed: {e}")
        return None, None


def check_radio(spi, cs, reset):
    """Check radio initialization."""
    print("\n[3] Checking RFM69 radio...")
    
    if spi is None or cs is None or reset is None:
        print("    ✗ Skipping (SPI/GPIO not available)")
        return None
    
    try:
        import adafruit_rfm69
        
        # Initialize radio
        rfm69 = adafruit_rfm69.RFM69(spi, cs, reset, 433.0)
        print("    ✓ Radio initialized successfully!")
        print(f"    ✓ Frequency: 433.0 MHz")
        
        # Check temperature sensor (built into radio)
        try:
            temp = rfm69.temperature
            print(f"    ✓ Temperature: {temp}°C")
        except:
            print("    ? Temperature: unavailable")
        
        return rfm69
        
    except RuntimeError as e:
        print(f"    ✗ Radio initialization failed: {e}")
        print("\n    [TROUBLESHOOTING]")
        print("    1. Check all wiring connections")
        print("    2. Verify using 3.3V power (NOT 5V!)")
        print("    3. Check MISO/MOSI are connected correctly")
        print("    4. Ensure the radio module is not damaged")
        return None
    except ImportError:
        print("    ✗ adafruit-circuitpython-rfm69 not installed")
        print("\n    [FIX] Install required library:")
        print("          pip install adafruit-circuitpython-rfm69")
        return None


def check_dependencies():
    """Check all required Python packages."""
    print("\n[0] Checking dependencies...")
    
    required = [
        ("board", "adafruit-blinka"),
        ("digitalio", "adafruit-blinka"),
        ("busio", "adafruit-blinka"),
        ("adafruit_rfm69", "adafruit-circuitpython-rfm69"),
    ]
    
    all_ok = True
    for module, package in required:
        try:
            __import__(module)
            print(f"    ✓ {module}")
        except ImportError:
            print(f"    ✗ {module} - install with: pip install {package}")
            all_ok = False
    
    return all_ok


def main():
    """Run all diagnostic checks."""
    print("=" * 50)
    print("RFM69HCW RADIO DIAGNOSTIC")
    print("=" * 50)
    
    # Check dependencies first
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n" + "=" * 50)
        print("RESULT: MISSING DEPENDENCIES")
        print("=" * 50)
        print("\nInstall all dependencies with:")
        print("  pip install adafruit-blinka adafruit-circuitpython-rfm69")
        return
    
    # Check hardware
    spi = check_spi()
    cs, reset = check_gpio()
    rfm69 = check_radio(spi, cs, reset)
    
    # Summary
    print("\n" + "=" * 50)
    if rfm69 is not None:
        print("RESULT: ALL CHECKS PASSED ✓")
        print("=" * 50)
        print("\nYour radio is ready for communication!")
        print("Run the appropriate script:")
        print("  - Avionics (Pi Zero 2W): python3 avionics_tx.py")
        print("  - Ground Station (Pi 4B): python3 groundstation_rx.py")
    else:
        print("RESULT: HARDWARE ISSUE DETECTED ✗")
        print("=" * 50)
        print("\nPlease check the troubleshooting steps above.")


if __name__ == "__main__":
    main()
