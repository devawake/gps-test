#!/usr/bin/env python3
"""
Low-Level SPI Debug Script for RFM69
=====================================
This script bypasses the Adafruit library to directly test SPI communication
with the RFM69 chip. It will help identify if the issue is:
- SPI not working at all (reads 0x00)
- MISO not connected (reads 0xFF)
- Wrong chip or different version
- Library issue vs hardware issue
"""

import time

def test_with_spidev():
    """Test using the lower-level spidev library directly."""
    print("\n" + "=" * 50)
    print("TEST 1: Direct SPI using spidev")
    print("=" * 50)
    
    try:
        import spidev
        import RPi.GPIO as GPIO
    except ImportError as e:
        print(f"✗ Missing library: {e}")
        print("  Install with: sudo apt install python3-spidev python3-rpi.gpio")
        return False
    
    # GPIO setup
    RST_PIN = 25  # GPIO25 for reset
    CS_PIN = 8    # GPIO8 / CE0
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(RST_PIN, GPIO.OUT)
        
        # Perform a proper reset sequence
        print("\n[1] Performing reset sequence...")
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.1)  # 100ms high
        GPIO.output(RST_PIN, GPIO.LOW)
        time.sleep(0.01)  # 10ms low, then wait for chip to boot
        time.sleep(0.1)   # Wait for oscillator to stabilize
        print("    ✓ Reset complete")
        
        # Open SPI
        print("\n[2] Opening SPI device...")
        spi = spidev.SpiDev()
        spi.open(0, 0)  # Bus 0, Device 0 (CE0)
        spi.max_speed_hz = 1000000  # 1 MHz (slow for reliability)
        spi.mode = 0b00  # SPI Mode 0
        print(f"    ✓ SPI opened (mode={spi.mode}, speed={spi.max_speed_hz}Hz)")
        
        # Read version register (0x10)
        # To read: send address with bit 7 = 0, then read response
        print("\n[3] Reading RFM69 Version Register (0x10)...")
        
        # RFM69 read: address byte (bit7=0 for read), then dummy byte to clock out response
        response = spi.xfer2([0x10, 0x00])
        version = response[1]
        
        print(f"    Raw response: {response}")
        print(f"    Version byte: 0x{version:02X} ({version})")
        
        # Interpret the result
        print("\n[4] Interpretation:")
        if version == 0x24:
            print("    ✓ SUCCESS! RFM69 detected (version 0x24)")
            print("    This is exactly what we expect!")
            result = True
        elif version == 0x00:
            print("    ✗ Got 0x00 - Chip not responding")
            print("    Possible causes:")
            print("      - VIN not connected to 3.3V")
            print("      - GND not connected")
            print("      - CS (CE0) not connected")
            print("      - Chip is dead")
            result = False
        elif version == 0xFF:
            print("    ✗ Got 0xFF - MISO line issue")
            print("    Possible causes:")
            print("      - MISO not connected")
            print("      - MISO connected to wrong pin")
            print("      - Pullup on MISO line")
            result = False
        else:
            print(f"    ? Got unexpected version: 0x{version:02X}")
            print("    This could mean:")
            print("      - Different radio chip/revision")
            print("      - Intermittent connection")
            print("      - SPI timing issue")
            result = False
        
        # Try reading a few more registers
        print("\n[5] Reading additional registers for diagnosis...")
        registers = [
            (0x00, "FIFO"),
            (0x01, "OpMode"),
            (0x02, "DataModul"),
            (0x10, "Version"),
        ]
        
        for addr, name in registers:
            resp = spi.xfer2([addr, 0x00])
            print(f"    Reg 0x{addr:02X} ({name:10}): 0x{resp[1]:02X}")
        
        spi.close()
        GPIO.cleanup()
        return result
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        try:
            GPIO.cleanup()
        except:
            pass
        return False


def test_spi_loopback():
    """Test if SPI bus itself is working by checking MOSI/MISO."""
    print("\n" + "=" * 50)
    print("TEST 2: SPI Bus Self-Test")
    print("=" * 50)
    
    try:
        import spidev
    except ImportError:
        print("✗ spidev not available")
        return
    
    print("\nThis test checks if SPI signals are being generated.")
    print("If you have a logic analyzer or oscilloscope, check:")
    print("  - Pin 23 (SCK)  - Should see clock pulses")
    print("  - Pin 19 (MOSI) - Should see data")
    print("  - Pin 21 (MISO) - Should see response from radio")
    print("  - Pin 24 (CS)   - Should go LOW during transaction")


def check_kernel_spi():
    """Check if SPI is enabled at the kernel level."""
    print("\n" + "=" * 50)
    print("TEST 3: Kernel SPI Check")
    print("=" * 50)
    
    import os
    
    # Check for SPI devices
    spi_devices = []
    if os.path.exists("/dev"):
        for f in os.listdir("/dev"):
            if f.startswith("spidev"):
                spi_devices.append(f"/dev/{f}")
    
    if spi_devices:
        print(f"\n✓ SPI devices found: {spi_devices}")
    else:
        print("\n✗ No SPI devices found in /dev!")
        print("  SPI may not be enabled. Run:")
        print("    sudo raspi-config -> Interface Options -> SPI -> Enable")
        print("  Then reboot.")
        return False
    
    # Check /boot/config.txt for SPI
    config_paths = ["/boot/config.txt", "/boot/firmware/config.txt"]
    for config_path in config_paths:
        if os.path.exists(config_path):
            print(f"\nChecking {config_path}...")
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                    if "dtparam=spi=on" in content:
                        print("  ✓ SPI enabled in config")
                    elif "#dtparam=spi=on" in content:
                        print("  ✗ SPI is COMMENTED OUT (disabled)")
                    else:
                        print("  ? SPI setting not found")
            except PermissionError:
                print(f"  ? Cannot read {config_path} (try with sudo)")
            break
    
    return True


def check_permissions():
    """Check if we have permission to access SPI."""
    print("\n" + "=" * 50)
    print("TEST 4: Permission Check")
    print("=" * 50)
    
    import os
    import grp
    import pwd
    
    user = pwd.getpwuid(os.getuid()).pw_name
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
    
    print(f"\nCurrent user: {user}")
    print(f"User groups: {groups}")
    
    if "spi" in groups or "gpio" in groups or user == "root":
        print("✓ User has SPI/GPIO access")
    else:
        print("✗ User may not have SPI access!")
        print("  Try running with: sudo python3 spi_debug.py")
        print("  Or add user to groups: sudo usermod -aG spi,gpio $USER")


def main():
    print("=" * 50)
    print("RFM69 LOW-LEVEL SPI DIAGNOSTIC")
    print("=" * 50)
    print("\nThis script tests SPI communication at a lower level")
    print("to help diagnose the 'Invalid RFM69 version' error.")
    
    check_kernel_spi()
    check_permissions()
    success = test_with_spidev()
    test_spi_loopback()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if success:
        print("\n✓ SPI communication is working!")
        print("  The Adafruit library issue might be a timing problem.")
        print("  Try running the radio scripts with: sudo python3 <script>.py")
    else:
        print("\n✗ SPI communication failed")
        print("\nNext steps to try:")
        print("  1. Run this script with sudo: sudo python3 spi_debug.py")
        print("  2. Double-check your wiring:")
        print("     - Is VIN connected to 3.3V (Pin 1)?")
        print("     - Is GND connected to Pin 6?")
        print("     - Inspect solder joints if using a breakout board")
        print("  3. Try swapping the radios between Pis")
        print("  4. Check if antenna is attached (some modules won't init without it)")


if __name__ == "__main__":
    main()
