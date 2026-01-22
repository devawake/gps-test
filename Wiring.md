# RFM69HCW Radio Wiring

## Correct Wiring (Radio -> Raspberry Pi)

| Radio Pin | Pi Pin | Pi GPIO | Description |
|-----------|--------|---------|-------------|
| VIN       | Pin 1  | 3.3V    | Power (3.3V only!) |
| GND       | Pin 6  | GND     | Ground |
| G0        | Pin 18 | GPIO24  | Interrupt |
| SCK       | Pin 23 | GPIO11  | SPI Clock |
| MISO      | Pin 21 | GPIO9   | SPI MISO (Master In, Slave Out) |
| MOSI      | Pin 19 | GPIO10  | SPI MOSI (Master Out, Slave In) |
| CS        | Pin 24 | GPIO8   | SPI Chip Select (CE0) |
| RST       | Pin 22 | GPIO25  | Reset |

## Important Notes

⚠️ **MISO/MOSI are NOT crossed!** Unlike UART TX/RX, SPI uses:
- MISO -> MISO (both same signal)
- MOSI -> MOSI (both same signal)

This wiring is identical on both the Pi Zero 2W and Pi 4B.