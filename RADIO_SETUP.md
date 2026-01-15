# RFM69HCW Radio Setup Guide

This guide helps you set up and test your Adafruit RFM69HCW radios on Raspberry Pi.

## 1. Wiring (Default pins used in radio_test.py)

| RFM69 Pin | Pi Pin (Physical) | Pi GPIO | Description |
|-----------|-------------------|---------|-------------|
| VIN       | 3.3V (1 or 17)     | -       | Power       |
| GND       | Ground (6, 9, ...) | -       | Ground      |
| SCK       | Pin 23            | GPIO 11 | SPI Clock   |
| MISO      | Pin 21            | GPIO 9  | SPI MISO    |
| MOSI      | Pin 19            | GPIO 10 | SPI MOSI    |
| CS        | Pin 29            | GPIO 5  | Chip Select |
| RST       | Pin 22            | GPIO 25 | Reset       |
| G0 (IRQ)  | Pin 15 (Optional) | GPIO 22 | Interrupt   |

*Note: You MUST enable SPI on your Raspberry Pi using `sudo raspi-config` (Interfacing Options -> SPI).*

## 2. Installation

Run this on both Raspberry Pis:

```bash
sudo pip3 install adafruit-circuitpython-rfm69 RPi.GPIO
```

## 3. Running the Test

Copy `radio_test.py` to both Pis.

### On Pi 1 (Receiver):
```bash
python3 radio_test.py receive
```

### On Pi 2 (Sender):
```bash
python3 radio_test.py send
```

## 4. Troubleshooting

- **Check Frequency:** Ensure the `FREQUENCY` variable in `radio_test.py` matches your hardware (usually 915.0 or 433.0 MHz).
- **SPI Errors:** Ensure SPI is enabled in `raspi-config`.
- **Power:** The HCW version can draw significant current during transmission. If you experience crashes, try a stronger power supply.
- **Antenna:** Make sure you have an antenna (even a simple wire) soldered to the ANT pin. Running without an antenna can damage the module.
