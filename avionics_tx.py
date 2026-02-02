#!/usr/bin/env python3
"""
Avionics Transmitter Script (Pi Zero 2W) - Using spidev
========================================================
Fixed version with proper RFM69HCW high-power configuration.
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

# Transmission settings
TX_POWER = 20           # dBm (max 20 for RFM69HCW)
TX_INTERVAL = 3.0       # Seconds between transmissions

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
REG_VERSION = 0x10
REG_PALEVEL = 0x11
REG_OCP = 0x13
REG_LNA = 0x18
REG_RXBW = 0x19
REG_AFCBW = 0x1A
REG_RSSIVALUE = 0x24
REG_DIOMAPPING1 = 0x25
REG_IRQFLAGS1 = 0x27
REG_IRQFLAGS2 = 0x28
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
    
    def __init__(self, spi_bus=0, spi_device=0, reset_pin=25, freq_mhz=433.0, is_high_power=True):
        self.reset_pin = reset_pin
        self.freq_mhz = freq_mhz
        self.is_high_power = is_high_power
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
        
        # Verify chip - should be 0x24 for RFM69
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
    
    def _write_fifo(self, data):
        """Write data to FIFO."""
        self.spi.xfer2([REG_FIFO | 0x80] + list(data))
    
    def _init_radio(self):
        """Initialize radio with default settings."""
        # Go to standby first
        self._write_reg(REG_OPMODE, MODE_STANDBY)
        time.sleep(0.01)
        
        config = [
            # Packet mode, FSK, no shaping
            (REG_DATAMODUL, 0x00),
            
            # Bit rate: 4.8 kbps (FXOSC / bitrate = 32MHz / 4800 = 6667 = 0x1A0B)
            (REG_BITRATEMSB, 0x1A),
            (REG_BITRATELSB, 0x0B),
            
            # Frequency deviation: 5 kHz (FDEV = 5000 / FSTEP = 5000 / 61 = 82 = 0x0052)
            (REG_FDEVMSB, 0x00),
            (REG_FDEVLSB, 0x52),
            
            # RX bandwidth - wider for better reception
            (REG_RXBW, 0x55),   # RxBwMant=16, RxBwExp=5 -> ~10.4 kHz
            (REG_AFCBW, 0x8B),  # AFC bandwidth
            
            # Preamble length: 4 bytes
            (0x2C, 0x00),
            (0x2D, 0x04),
            
            # Sync word config: on, 2 bytes, no errors tolerated
            (REG_SYNCCONFIG, 0x88),
            (REG_SYNCVALUE1, 0x2D),  # Sync word byte 1: 0x2D
            (REG_SYNCVALUE2, 0xD4),  # Sync word byte 2: 0xD4
            
            # Packet config: variable length, DC-FREE off, CRC on, no address filtering
            # Bit 7: packet format (1=variable)
            # Bit 6-5: DC-free encoding (00=none)
            # Bit 4: CRC on (1=yes)
            # Bit 3: CRC auto clear off (0=clear)
            # Bit 2-1: address filtering (00=none)
            (REG_PACKETCONFIG1, 0x90),  # Variable length, CRC on, no addr filter
            
            # Max payload length
            (REG_PAYLOADLENGTH, 66),
            
            # FIFO threshold: start TX when FIFO not empty
            (REG_FIFOTHRESH, 0x8F),  # TxStartCondition=1 (FifoNotEmpty), FifoThreshold=15
            
            # Packet config 2: Inter-packet RX delay, auto restart
            (REG_PACKETCONFIG2, 0x02),
            
            # Improved AFC
            (REG_TESTDAGC, 0x30),
            
            # LNA settings
            (REG_LNA, 0x88),
        ]
        
        for reg, val in config:
            self._write_reg(reg, val)
            # Verify write
            readback = self._read_reg(reg)
            if readback != val and reg != REG_IRQFLAGS2:  # Some regs are read-only or auto-clear
                print(f"  [WARN] Reg 0x{reg:02X}: wrote 0x{val:02X}, read 0x{readback:02X}")
        
        # Set frequency
        self._set_frequency(self.freq_mhz)
        
        # Set TX power (must be done after high power setup)
        self._set_tx_power(TX_POWER)
        
        # Set node address (not used with no address filtering, but set anyway)
        self._write_reg(REG_NODEADRS, NODE_ADDRESS)
        self._write_reg(REG_BROADCASTADRS, BROADCAST_ADDR)
    
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
    
    def _set_tx_power(self, power_dbm):
        """
        Set transmit power for RFM69HCW (high power module).
        
        For RFM69HCW:
        - PA1 + PA2 on PA_BOOST pin
        - Power range: -2 dBm to +20 dBm
        - For +18 to +20 dBm, need to enable high power settings
        """
        power_dbm = max(-2, min(20, power_dbm))
        
        if self.is_high_power:
            if power_dbm >= 18:
                # High power mode (+18 to +20 dBm)
                # PA1 + PA2, OutputPower = power_dbm + 11
                self._write_reg(REG_OCP, 0x0F)  # Disable OCP
                self._write_reg(REG_PALEVEL, 0x60 | (power_dbm + 11))
                # Enable high power boost
                self._write_reg(REG_TESTPA1, 0x5D)
                self._write_reg(REG_TESTPA2, 0x7C)
            else:
                # Normal power mode (-2 to +17 dBm)
                # PA1 + PA2, OutputPower = power_dbm + 14
                self._write_reg(REG_OCP, 0x1A)  # Enable OCP
                self._write_reg(REG_PALEVEL, 0x60 | (power_dbm + 14))
                # Disable high power boost
                self._write_reg(REG_TESTPA1, 0x55)
                self._write_reg(REG_TESTPA2, 0x70)
        else:
            # Standard RFM69 (non-HCW)
            # PA0 on RFIO pin, power range -18 to +13 dBm
            self._write_reg(REG_PALEVEL, 0x80 | (power_dbm + 18))
        
        print(f"  [DEBUG] TX power set to {power_dbm} dBm (high_power={self.is_high_power})")
    
    def _set_mode(self, mode):
        """Set operating mode and wait for mode ready."""
        if mode == self.mode:
            return
        
        # If leaving TX mode, disable high power boost
        if self.mode == MODE_TX and self.is_high_power:
            self._write_reg(REG_TESTPA1, 0x55)
            self._write_reg(REG_TESTPA2, 0x70)
        
        self._write_reg(REG_OPMODE, mode)
        
        # If entering TX mode, enable high power boost (if power >= 18)
        if mode == MODE_TX and self.is_high_power and TX_POWER >= 18:
            self._write_reg(REG_TESTPA1, 0x5D)
            self._write_reg(REG_TESTPA2, 0x7C)
        
        # Wait for mode ready (bit 7 of IRQFLAGS1)
        timeout = time.time() + 1.0
        while not (self._read_reg(REG_IRQFLAGS1) & 0x80):
            if time.time() > timeout:
                print(f"  [ERROR] Mode change timeout! IRQFLAGS1=0x{self._read_reg(REG_IRQFLAGS1):02X}")
                break
            time.sleep(0.001)
        
        self.mode = mode
    
    def send(self, message, debug=True):
        """Send a message (string or bytes)."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Limit message length
        message = message[:60]
        
        if debug:
            print("     [1] Entering standby mode...")
        
        # Go to standby mode first
        self._set_mode(MODE_STANDBY)
        time.sleep(0.005)
        
        if debug:
            irq1 = self._read_reg(REG_IRQFLAGS1)
            irq2 = self._read_reg(REG_IRQFLAGS2)
            print(f"     [2] Status: IRQFLAGS1=0x{irq1:02X}, IRQFLAGS2=0x{irq2:02X}")
        
        # Clear FIFO by reading it (optional, but ensures clean state)
        # Actually, going to standby should reset FIFO state
        
        if debug:
            print(f"     [3] Writing {len(message)+1} bytes to FIFO...")
        
        # Write to FIFO: length byte + data
        payload = [len(message)] + list(message)
        self._write_fifo(payload)
        
        if debug:
            irq2 = self._read_reg(REG_IRQFLAGS2)
            print(f"     [4] After FIFO write: IRQFLAGS2=0x{irq2:02X}")
        
        if debug:
            print("     [5] Switching to TX mode...")
        
        # Switch to TX mode
        self._set_mode(MODE_TX)
        
        if debug:
            irq1 = self._read_reg(REG_IRQFLAGS1)
            irq2 = self._read_reg(REG_IRQFLAGS2)
            print(f"     [6] In TX mode: IRQFLAGS1=0x{irq1:02X}, IRQFLAGS2=0x{irq2:02X}")
        
        # Wait for packet sent (bit 3 of IRQFLAGS2 = PacketSent)
        timeout = time.time() + 2.0
        while True:
            irq2 = self._read_reg(REG_IRQFLAGS2)
            if irq2 & 0x08:  # PacketSent
                break
            if time.time() > timeout:
                irq1 = self._read_reg(REG_IRQFLAGS1)
                print(f"     ✗ TX timeout! IRQFLAGS1=0x{irq1:02X}, IRQFLAGS2=0x{irq2:02X}")
                self._set_mode(MODE_STANDBY)
                return False
            time.sleep(0.001)
        
        if debug:
            print("     [7] PacketSent flag set, returning to standby...")
        
        # Back to standby
        self._set_mode(MODE_STANDBY)
        return True
    
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
        radio = RFM69(freq_mhz=RADIO_FREQ_MHZ, is_high_power=True)
        print(f"✓ Radio initialized at {RADIO_FREQ_MHZ} MHz")
        print(f"✓ TX Power: {TX_POWER} dBm")
        print(f"✓ Node address: 0x{NODE_ADDRESS:02X}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("Starting transmission... (Ctrl+C to stop)")
    print("=" * 50 + "\n")
    
    packet_count = 0
    success_count = 0
    
    try:
        while True:
            packet_count += 1
            timestamp = time.strftime("%H:%M:%S")
            message = f"AVIONICS #{packet_count} @ {timestamp}"
            
            print(f"[TX] Sending: {message}")
            
            try:
                if radio.send(message):
                    success_count += 1
                    print(f"     ✓ Packet #{packet_count} sent! ({success_count}/{packet_count} success)")
                else:
                    print(f"     ✗ Packet #{packet_count} failed!")
            except Exception as e:
                print(f"     ✗ Send exception: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(TX_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\nStopped. Packets: {success_count}/{packet_count} sent successfully")
    finally:
        radio.close()
        print("Radio closed. Goodbye!")


if __name__ == "__main__":
    main()
