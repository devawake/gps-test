#!/usr/bin/env python3
"""
Avionics Transmitter Script (Pi Zero 2W) - Using spidev
========================================================
This version uses spidev directly instead of Adafruit library
since spidev has proven to work.
"""

import time
import spidev
import RPi.GPIO as GPIO

# ============================================
# CONFIGURATION - MUST MATCH ON BOTH RADIOS!
# ============================================
RADIO_FREQ_MHZ = 433.0
NODE_ADDRESS = 0x01      # This node (avionics)
BROADCAST_ADDR = 0xFF    # Broadcast to all
ENCRYPTION_KEY = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                  0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10]

# Transmission settings
TX_POWER = 20           # dBm (max 20)
TX_INTERVAL = 2.0       # Seconds between transmissions

# Hardware pins
RST_PIN = 25  # GPIO25
DIO0_PIN = 24 # GPIO24 (interrupt, optional)

# RFM69 Register addresses
REG_FIFO = 0x00
REG_OPMODE = 0x01
REG_DATAMODUL = 0x02
REG_BITRATEMSB = 0x03
REG_BITRATELSB = 0x04
REG_FDEVMSB = 0x05
REG_FDEVLSB = 0x06
REG_FRFMSB = 0x07
REG_FRFMID = 0x08
REG_FRFLSB = 0x09
REG_PALEVEL = 0x11
REG_LNA = 0x18
REG_RXBW = 0x19
REG_AFCBW = 0x1A
REG_RSSIVALUE = 0x24
REG_DIOMAPPING1 = 0x25
REG_IRQFLAGS1 = 0x27
REG_IRQFLAGS2 = 0x28
REG_SYNCCONFIG = 0x2E
REG_SYNCVALUE1 = 0x2F
REG_PACKETCONFIG1 = 0x37
REG_PAYLOADLENGTH = 0x38
REG_NODEADRS = 0x39
REG_BROADCASTADRS = 0x3A
REG_FIFOTHRESH = 0x3C
REG_PACKETCONFIG2 = 0x3D
REG_AESKEY1 = 0x3E
REG_TESTDAGC = 0x6F

# Operating modes
MODE_SLEEP = 0x00
MODE_STANDBY = 0x04
MODE_TX = 0x0C
MODE_RX = 0x10

# FXOSC = 32MHz
FXOSC = 32000000
FSTEP = FXOSC / 524288  # 2^19


class RFM69:
    """Simple RFM69 driver using spidev."""
    
    def __init__(self, spi_bus=0, spi_device=0, reset_pin=25, freq_mhz=433.0):
        self.reset_pin = reset_pin
        self.freq_mhz = freq_mhz
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.reset_pin, GPIO.OUT)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 4000000  # 4 MHz
        self.spi.mode = 0b00
        
        # Reset the radio
        self._reset()
        
        # Verify chip
        version = self._read_reg(0x10)
        if version != 0x24:
            raise RuntimeError(f"Invalid RFM69 version: 0x{version:02X}")
        
        # Initialize radio settings
        self._init_radio()
    
    def _reset(self):
        """Perform hardware reset."""
        GPIO.output(self.reset_pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.reset_pin, GPIO.LOW)
        time.sleep(0.1)
    
    def _read_reg(self, addr):
        """Read a single register."""
        resp = self.spi.xfer2([addr & 0x7F, 0x00])
        return resp[1]
    
    def _write_reg(self, addr, value):
        """Write a single register."""
        self.spi.xfer2([addr | 0x80, value])
    
    def _write_fifo(self, data):
        """Write data to FIFO."""
        self.spi.xfer2([REG_FIFO | 0x80] + list(data))
    
    def _init_radio(self):
        """Initialize radio with default settings."""
        config = [
            # Packet mode, FSK, no shaping
            (REG_DATAMODUL, 0x00),
            # ~4.8kbps bitrate
            (REG_BITRATEMSB, 0x1A),
            (REG_BITRATELSB, 0x0B),
            # 5kHz frequency deviation
            (REG_FDEVMSB, 0x00),
            (REG_FDEVLSB, 0x52),
            # RX bandwidth
            (REG_RXBW, 0x55),
            (REG_AFCBW, 0x8B),
            # Preamble length (4 bytes)
            (0x2C, 0x00),
            (0x2D, 0x04),
            # Sync word config: on, 2 bytes
            (REG_SYNCCONFIG, 0x88),
            (REG_SYNCVALUE1, 0x2D),  # Sync word byte 1
            (0x30, 0xD4),            # Sync word byte 2
            # Packet config: variable length, CRC on, no address filtering
            (REG_PACKETCONFIG1, 0x90),
            (REG_PAYLOADLENGTH, 66),
            # FIFO threshold
            (REG_FIFOTHRESH, 0x8F),
            # Auto restart RX, AES off
            (REG_PACKETCONFIG2, 0x02),
            # Improved sensitivity
            (REG_TESTDAGC, 0x30),
            # LNA settings
            (REG_LNA, 0x88),
        ]
        
        for reg, val in config:
            self._write_reg(reg, val)
        
        # Set frequency
        self._set_frequency(self.freq_mhz)
        
        # Set TX power
        self._set_tx_power(TX_POWER)
        
        # Set node address
        self._write_reg(REG_NODEADRS, NODE_ADDRESS)
        self._write_reg(REG_BROADCASTADRS, BROADCAST_ADDR)
    
    def _set_frequency(self, freq_mhz):
        """Set the carrier frequency."""
        frf = int((freq_mhz * 1000000) / FSTEP)
        self._write_reg(REG_FRFMSB, (frf >> 16) & 0xFF)
        self._write_reg(REG_FRFMID, (frf >> 8) & 0xFF)
        self._write_reg(REG_FRFLSB, frf & 0xFF)
    
    def _set_tx_power(self, power_dbm):
        """Set transmit power (dBm)."""
        # For RFM69HCW with PA1+PA2 on PA_BOOST
        # Power range: -2 to +20 dBm
        power_dbm = max(-2, min(20, power_dbm))
        pa_level = power_dbm + 14
        self._write_reg(REG_PALEVEL, 0x60 | pa_level)
    
    def _set_mode(self, mode):
        """Set operating mode."""
        self._write_reg(REG_OPMODE, mode)
        # Wait for mode ready
        while not (self._read_reg(REG_IRQFLAGS1) & 0x80):
            time.sleep(0.001)
    
    def send(self, message):
        """Send a message (string or bytes)."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Limit message length (max 60 bytes to leave room for length byte)
        message = message[:60]
        
        # Go to standby mode
        self._set_mode(MODE_STANDBY)
        
        # Wait for FIFO empty
        while not (self._read_reg(REG_IRQFLAGS2) & 0x40):
            time.sleep(0.001)
        
        # Write to FIFO: length byte + data
        payload = [len(message)] + list(message)
        self._write_fifo(payload)
        
        # Switch to TX mode
        self._set_mode(MODE_TX)
        
        # Wait for packet sent (PacketSent flag in IRQFLAGS2)
        timeout = time.time() + 2.0
        while not (self._read_reg(REG_IRQFLAGS2) & 0x08):
            if time.time() > timeout:
                self._set_mode(MODE_STANDBY)
                raise RuntimeError("TX timeout")
            time.sleep(0.001)
        
        # Back to standby
        self._set_mode(MODE_STANDBY)
    
    def close(self):
        """Clean up."""
        self._set_mode(MODE_SLEEP)
        self.spi.close()
        GPIO.cleanup()


def main():
    """Main transmission loop."""
    print("=" * 50)
    print("AVIONICS TRANSMITTER (spidev version)")
    print("=" * 50)
    
    print("\nInitializing radio...")
    try:
        radio = RFM69(freq_mhz=RADIO_FREQ_MHZ)
        print(f"✓ Radio initialized at {RADIO_FREQ_MHZ} MHz")
        print(f"✓ TX Power: {TX_POWER} dBm")
        print(f"✓ Node address: 0x{NODE_ADDRESS:02X}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return
    
    print("\n" + "=" * 50)
    print("Starting transmission... (Ctrl+C to stop)")
    print("=" * 50 + "\n")
    
    packet_count = 0
    
    try:
        while True:
            packet_count += 1
            timestamp = time.strftime("%H:%M:%S")
            message = f"AVIONICS #{packet_count} @ {timestamp}"
            
            print(f"[TX] Sending: {message}")
            
            try:
                radio.send(message)
                print(f"     ✓ Packet #{packet_count} sent!")
            except Exception as e:
                print(f"     ✗ Send failed: {e}")
            
            time.sleep(TX_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\nStopped. Total packets sent: {packet_count}")
    finally:
        radio.close()
        print("Radio closed. Goodbye!")


if __name__ == "__main__":
    main()
