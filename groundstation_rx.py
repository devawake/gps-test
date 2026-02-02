#!/usr/bin/env python3
"""
Ground Station Receiver Script (Pi 4B) - Using spidev
======================================================
Fixed version with proper RFM69HCW configuration and improved debugging.
"""

import time
import spidev
import RPi.GPIO as GPIO

# ============================================
# CONFIGURATION - MUST MATCH ON BOTH RADIOS!
# ============================================
RADIO_FREQ_MHZ = 433.0
NODE_ADDRESS = 0x02      # This node (ground station)
BROADCAST_ADDR = 0xFF    # Accept broadcasts

# Hardware pins
RST_PIN = 25  # GPIO25
DIO0_PIN = 24 # GPIO24 (interrupt for PayloadReady)

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
REG_VERSION = 0x10
REG_PALEVEL = 0x11
REG_OCP = 0x13
REG_LNA = 0x18
REG_RXBW = 0x19
REG_AFCBW = 0x1A
REG_RSSICONFIG = 0x23
REG_RSSIVALUE = 0x24
REG_DIOMAPPING1 = 0x25
REG_IRQFLAGS1 = 0x27
REG_IRQFLAGS2 = 0x28
REG_RSSITHRESH = 0x29
REG_SYNCCONFIG = 0x2E
REG_SYNCVALUE1 = 0x2F
REG_SYNCVALUE2 = 0x30
REG_PACKETCONFIG1 = 0x37
REG_PAYLOADLENGTH = 0x38
REG_NODEADRS = 0x39
REG_BROADCASTADRS = 0x3A
REG_FIFOTHRESH = 0x3C
REG_PACKETCONFIG2 = 0x3D
REG_TESTPA1 = 0x5A
REG_TESTPA2 = 0x5C
REG_TESTDAGC = 0x6F

# Operating modes (bits 4:2 of OPMODE)
MODE_SLEEP = 0x00
MODE_STANDBY = 0x04
MODE_FS = 0x08        # Frequency synthesizer
MODE_TX = 0x0C
MODE_RX = 0x10

# FXOSC = 32MHz
FXOSC = 32000000
FSTEP = FXOSC / 524288  # 2^19


class RFM69:
    """Simple RFM69HCW driver using spidev."""
    
    def __init__(self, spi_bus=0, spi_device=0, reset_pin=25, freq_mhz=433.0):
        self.reset_pin = reset_pin
        self.freq_mhz = freq_mhz
        self.last_rssi = 0
        self.mode = MODE_STANDBY
        
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
        version = self._read_reg(REG_VERSION)
        print(f"  [DEBUG] Chip version: 0x{version:02X}")
        if version != 0x24:
            raise RuntimeError(f"Invalid RFM69 version: 0x{version:02X} (expected 0x24)")
        
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
    
    def _read_fifo(self, length):
        """Read data from FIFO."""
        resp = self.spi.xfer2([REG_FIFO] + [0x00] * length)
        return resp[1:]
    
    def _init_radio(self):
        """Initialize radio with default settings matching TX."""
        # Go to standby first
        self._write_reg(REG_OPMODE, MODE_STANDBY)
        time.sleep(0.01)
        
        config = [
            # Packet mode, FSK, no shaping
            (REG_DATAMODUL, 0x00),
            
            # Bit rate: 4.8 kbps (MUST match TX!)
            (REG_BITRATEMSB, 0x1A),
            (REG_BITRATELSB, 0x0B),
            
            # Frequency deviation: 5 kHz (MUST match TX!)
            (REG_FDEVMSB, 0x00),
            (REG_FDEVLSB, 0x52),
            
            # RX bandwidth - same as TX
            (REG_RXBW, 0x55),
            (REG_AFCBW, 0x8B),
            
            # Preamble length: 4 bytes (MUST match TX!)
            (0x2C, 0x00),
            (0x2D, 0x04),
            
            # Sync word config: on, 2 bytes (MUST match TX!)
            (REG_SYNCCONFIG, 0x88),
            (REG_SYNCVALUE1, 0x2D),  # Sync word byte 1
            (REG_SYNCVALUE2, 0xD4),  # Sync word byte 2
            
            # Packet config: variable length, CRC on, no address filtering (MUST match TX!)
            (REG_PACKETCONFIG1, 0x90),
            
            # Max payload length
            (REG_PAYLOADLENGTH, 66),
            
            # FIFO threshold
            (REG_FIFOTHRESH, 0x8F),
            
            # Packet config 2
            (REG_PACKETCONFIG2, 0x02),
            
            # Improved sensitivity for RFM69HCW
            (REG_TESTDAGC, 0x30),
            
            # LNA settings - high gain, auto AGC
            (REG_LNA, 0x88),
            
            # RSSI threshold (optional, for carrier sense)
            (REG_RSSITHRESH, 0xE4),  # -114 dBm threshold
        ]
        
        for reg, val in config:
            self._write_reg(reg, val)
            readback = self._read_reg(reg)
            if readback != val:
                print(f"  [WARN] Reg 0x{reg:02X}: wrote 0x{val:02X}, read 0x{readback:02X}")
        
        # Set frequency
        self._set_frequency(self.freq_mhz)
        
        # Set node address
        self._write_reg(REG_NODEADRS, NODE_ADDRESS)
        self._write_reg(REG_BROADCASTADRS, BROADCAST_ADDR)
        
        # For RX, ensure high power boost is OFF
        self._write_reg(REG_TESTPA1, 0x55)
        self._write_reg(REG_TESTPA2, 0x70)
    
    def _set_frequency(self, freq_mhz):
        """Set the carrier frequency."""
        frf = int((freq_mhz * 1000000) / FSTEP)
        self._write_reg(REG_FRFMSB, (frf >> 16) & 0xFF)
        self._write_reg(REG_FRFMID, (frf >> 8) & 0xFF)
        self._write_reg(REG_FRFLSB, frf & 0xFF)
        
        # Verify
        msb = self._read_reg(REG_FRFMSB)
        mid = self._read_reg(REG_FRFMID)
        lsb = self._read_reg(REG_FRFLSB)
        actual_frf = (msb << 16) | (mid << 8) | lsb
        actual_freq = actual_frf * FSTEP / 1000000
        print(f"  [DEBUG] Frequency set to {actual_freq:.3f} MHz")
    
    def _set_mode(self, mode):
        """Set operating mode."""
        if mode == self.mode:
            return
        
        self._write_reg(REG_OPMODE, mode)
        
        # Wait for mode ready
        timeout = time.time() + 1.0
        while not (self._read_reg(REG_IRQFLAGS1) & 0x80):
            if time.time() > timeout:
                print(f"  [ERROR] Mode change timeout!")
                break
            time.sleep(0.001)
        
        self.mode = mode
    
    def read_rssi(self):
        """Read current RSSI value."""
        # Trigger RSSI measurement
        self._write_reg(REG_RSSICONFIG, 0x01)
        # Wait for RSSI done
        timeout = time.time() + 0.1
        while not (self._read_reg(REG_RSSICONFIG) & 0x02):
            if time.time() > timeout:
                break
            time.sleep(0.001)
        return -(self._read_reg(REG_RSSIVALUE) // 2)
    
    def receive(self, timeout=5.0):
        """
        Listen for a packet.
        Returns the message as bytes, or None if timeout.
        """
        # Enter RX mode
        self._set_mode(MODE_RX)
        
        start_time = time.time()
        last_rssi_time = 0
        
        while True:
            current_time = time.time()
            
            # Check for PayloadReady flag (bit 2 of IRQFLAGS2)
            irq2 = self._read_reg(REG_IRQFLAGS2)
            
            if irq2 & 0x04:  # PayloadReady
                # Read RSSI
                self.last_rssi = -(self._read_reg(REG_RSSIVALUE) // 2)
                
                # Read length byte from FIFO
                length = self._read_reg(REG_FIFO)
                
                if 0 < length <= 66:
                    # Read payload
                    payload = self._read_fifo(length)
                    
                    # Back to standby
                    self._set_mode(MODE_STANDBY)
                    
                    return bytes(payload)
                else:
                    # Invalid length, flush and restart
                    print(f"  [WARN] Invalid payload length: {length}")
                    self._set_mode(MODE_STANDBY)
                    self._set_mode(MODE_RX)
            
            # Periodically show RSSI to confirm RX is working
            if current_time - last_rssi_time > 2.0:
                rssi = self.read_rssi()
                irq1 = self._read_reg(REG_IRQFLAGS1)
                print(f"  [DEBUG] Listening... RSSI={rssi} dBm, IRQFLAGS1=0x{irq1:02X}, IRQFLAGS2=0x{irq2:02X}")
                last_rssi_time = current_time
            
            # Check timeout
            if current_time - start_time > timeout:
                self._set_mode(MODE_STANDBY)
                return None
            
            time.sleep(0.01)
    
    def close(self):
        """Clean up."""
        self._set_mode(MODE_SLEEP)
        self.spi.close()
        GPIO.cleanup()


def main():
    """Main receive loop."""
    print("=" * 50)
    print("GROUND STATION RECEIVER (spidev version)")
    print("=" * 50)
    
    print("\nInitializing radio...")
    try:
        radio = RFM69(freq_mhz=RADIO_FREQ_MHZ)
        print(f"✓ Radio initialized at {RADIO_FREQ_MHZ} MHz")
        print(f"✓ Node address: 0x{NODE_ADDRESS:02X}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Print register comparison info
    print("\n[CONFIG CHECK]")
    print(f"  Bitrate: 0x{radio._read_reg(REG_BITRATEMSB):02X}{radio._read_reg(REG_BITRATELSB):02X}")
    print(f"  FDev: 0x{radio._read_reg(REG_FDEVMSB):02X}{radio._read_reg(REG_FDEVLSB):02X}")
    print(f"  Sync: 0x{radio._read_reg(REG_SYNCVALUE1):02X}{radio._read_reg(REG_SYNCVALUE2):02X}")
    print(f"  PacketConfig1: 0x{radio._read_reg(REG_PACKETCONFIG1):02X}")
    
    print("\n" + "=" * 50)
    print("Listening for packets... (Ctrl+C to stop)")
    print("=" * 50 + "\n")
    
    packets_received = 0
    start_time = time.time()
    
    try:
        while True:
            packet = radio.receive(timeout=5.0)
            
            if packet is not None:
                packets_received += 1
                
                # Try to decode as UTF-8
                try:
                    message = packet.decode('utf-8')
                except UnicodeDecodeError:
                    message = f"<raw: {packet.hex()}>"
                
                timestamp = time.strftime("%H:%M:%S")
                print(f"\n{'='*50}")
                print(f"[RX] PACKET RECEIVED!")
                print(f"     Time: {timestamp}")
                print(f"     RSSI: {radio.last_rssi} dBm")
                print(f"     Message: {message}")
                print(f"     Packets received: {packets_received}")
                print(f"{'='*50}\n")
            else:
                elapsed = int(time.time() - start_time)
                print(f"[...] No packet (listening for {elapsed}s, received: {packets_received})")
                
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n\nStopped after {elapsed:.1f} seconds")
        print(f"Total packets received: {packets_received}")
    finally:
        radio.close()
        print("Radio closed. Goodbye!")


if __name__ == "__main__":
    main()
