#!/usr/bin/env python3
"""
RFM69 Low-Level SPI Diagnostic Script
======================================
This script performs raw SPI communication to diagnose connection issues.
It bypasses the Adafruit library to see exactly what the radio is returning.
"""

import time

print("=" * 60)
print("   RFM69 Low-Level SPI Diagnostic")
print("=" * 60)

# ============================================
# Step 1: Check if spidev is available
# ============================================
print("\n📋 Step 1: Checking SPI availability...")

try:
    import spidev
    print("   ✅ spidev module found")
except ImportError:
    print("   ❌ spidev not installed!")
    print("   Run: sudo apt-get install python3-spidev")
    exit(1)

# Check if SPI devices exist
import os
spi_devices = [f for f in os.listdir('/dev') if f.startswith('spidev')]
if spi_devices:
    print(f"   ✅ SPI devices found: {spi_devices}")
else:
    print("   ❌ No SPI devices in /dev!")
    print("   Run: sudo raspi-config -> Interface Options -> SPI -> Enable")
    print("   Then reboot!")
    exit(1)

# ============================================
# Step 2: Check GPIO for reset
# ============================================
print("\n📋 Step 2: Testing GPIO reset pin...")

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    RST_PIN = 25  # GPIO25
    GPIO.setup(RST_PIN, GPIO.OUT)
    
    # Perform reset sequence
    print("   🔄 Performing radio reset...")
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.1)
    print("   ✅ Reset complete")
    
except Exception as e:
    print(f"   ❌ GPIO Error: {e}")
    exit(1)

# ============================================
# Step 3: Raw SPI communication
# ============================================
print("\n📋 Step 3: Raw SPI communication test...")

spi = spidev.SpiDev()

# Try different SPI settings
test_configs = [
    {"bus": 0, "device": 0, "speed": 1000000, "mode": 0},
    {"bus": 0, "device": 0, "speed": 500000, "mode": 0},
    {"bus": 0, "device": 0, "speed": 100000, "mode": 0},
    {"bus": 0, "device": 1, "speed": 1000000, "mode": 0},
]

def read_register(spi, reg):
    """Read a register from the RFM69."""
    # For reading, send register address with bit 7 = 0
    result = spi.xfer2([reg & 0x7F, 0x00])
    return result[1]

def read_version(spi):
    """Read the version register (0x10)."""
    return read_register(spi, 0x10)

version_found = None
working_config = None

for config in test_configs:
    try:
        spi.open(config["bus"], config["device"])
        spi.max_speed_hz = config["speed"]
        spi.mode = config["mode"]
        
        # Read version register multiple times
        versions = [read_version(spi) for _ in range(5)]
        spi.close()
        
        print(f"\n   Config: bus={config['bus']}, dev={config['device']}, "
              f"speed={config['speed']//1000}kHz, mode={config['mode']}")
        print(f"   📖 Version register reads: {[hex(v) for v in versions]}")
        
        # Check if we got consistent non-zero/non-0xFF values
        if versions[0] == versions[1] == versions[2] and versions[0] not in [0x00, 0xFF]:
            version_found = versions[0]
            working_config = config
            print(f"   ✅ Consistent version: {hex(version_found)}")
        elif all(v == 0x00 for v in versions):
            print("   ⚠️  All zeros - MISO might not be connected or radio not powered")
        elif all(v == 0xFF for v in versions):
            print("   ⚠️  All 0xFF - MISO might be floating or radio not responding")
        else:
            print("   ⚠️  Inconsistent reads - possible connection issue")
            
    except Exception as e:
        print(f"   Config {config}: Error - {e}")

# ============================================
# Step 4: Interpret results
# ============================================
print("\n" + "=" * 60)
print("   DIAGNOSTIC RESULTS")
print("=" * 60)

if version_found == 0x24:
    print("\n🎉 SUCCESS! Radio is communicating correctly!")
    print(f"   Version 0x24 = RFM69 confirmed")
    print(f"   Working config: {working_config}")
    print("\n   The Adafruit library should work. If it still fails,")
    print("   there might be a library version issue.")
    
elif version_found is not None:
    print(f"\n⚠️  Got version {hex(version_found)} instead of expected 0x24")
    print("   This could mean:")
    print("   - Different radio variant")
    print("   - Wiring issue affecting data")
    
else:
    print("\n❌ Could not communicate with radio!")
    print("\n🔧 Troubleshooting based on what we saw:")
    
    print("""
   If you saw all ZEROS (0x00):
   ────────────────────────────
   • MISO line is not connected properly
   • Radio is not powered (check VIN -> 3.3V connection)
   • Radio is held in reset state
   
   If you saw all 0xFF:
   ────────────────────────────
   • MOSI or SCK not connected
   • CS (chip select) not working
   • MISO floating (not connected to radio)
   
   If you saw random/inconsistent values:
   ────────────────────────────
   • Loose connections
   • MISO/MOSI swapped
   • Interference or long wires
""")

# ============================================
# Step 5: Pin verification helper
# ============================================
print("\n📋 Step 5: Verify your PHYSICAL pin connections")
print("=" * 60)
print("""
Please verify these connections on your Adafruit RFM69HCW breakout:

   RADIO BOARD          RASPBERRY PI
   ───────────          ────────────
   Vin  ──────────────► Pin 1  (3.3V Power)
   GND  ──────────────► Pin 6  (Ground)
   SCK  ──────────────► Pin 23 (GPIO11 - SPI CLK)
   MISO ──────────────► Pin 21 (GPIO9  - SPI MISO)  ← CRITICAL!
   MOSI ──────────────► Pin 19 (GPIO10 - SPI MOSI)  ← CRITICAL!
   CS   ──────────────► Pin 24 (GPIO8  - SPI CE0)
   RST  ──────────────► Pin 22 (GPIO25)
   G0   ──────────────► Pin 18 (GPIO24) [optional for basic test]

   ⚠️  IMPORTANT: On the Adafruit breakout board:
   • MISO on radio connects to MISO on Pi (Pin 21/GPIO9)
   • MOSI on radio connects to MOSI on Pi (Pin 19/GPIO10)
   • These do NOT cross over!
   
   💡 TIP: Use a multimeter in continuity mode to verify each connection.
""")

# ============================================
# Step 6: Additional checks
# ============================================
print("\n📋 Step 6: Additional system checks")
print("=" * 60)

# Check kernel modules
print("\n   Checking loaded SPI kernel modules:")
with open('/proc/modules', 'r') as f:
    modules = f.read()
    spi_modules = [line.split()[0] for line in modules.split('\n') 
                   if 'spi' in line.lower()]
    if spi_modules:
        print(f"   ✅ SPI modules loaded: {spi_modules}")
    else:
        print("   ⚠️  No SPI modules found in /proc/modules")

# Check config.txt for SPI
print("\n   Checking /boot/config.txt for SPI settings:")
try:
    with open('/boot/config.txt', 'r') as f:
        config = f.read()
        if 'dtparam=spi=on' in config:
            print("   ✅ SPI is enabled in config.txt")
        else:
            print("   ⚠️  'dtparam=spi=on' not found - SPI might not be enabled")
except:
    # Try firmware config location on newer Pi OS
    try:
        with open('/boot/firmware/config.txt', 'r') as f:
            config = f.read()
            if 'dtparam=spi=on' in config:
                print("   ✅ SPI is enabled in config.txt")
            else:
                print("   ⚠️  'dtparam=spi=on' not found")
    except:
        print("   ⚠️  Could not read config.txt")

print("\n" + "=" * 60)
print("   Run this on both Pis and compare results!")
print("=" * 60)

# Cleanup
GPIO.cleanup()
