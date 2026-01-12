# Pi Zero 2W Rocket GPS Interface

This project interfaces a **GEPRC GEP-M10DQ** GPS & Compass module with a Raspberry Pi Zero 2W.

## Wiring Diagram

| GPS Module Pin | Label | Pi Zero 2W Pin / GPIO | Description |
| :--- | :--- | :--- | :--- |
| **G** | Ground | Ground (e.g., Pin 6 or 9) | Power Ground |
| **V** | VCC | Pin 2 (5V) or Pin 1 (3.3V) | Power (M10 is 3.3-5V) |
| **T** | TX | GPIO 15 (Pin 10) | UART RX |
| **R** | RX | GPIO 14 (Pin 8) | UART TX |
| **L** | SCL | GPIO 3 (Pin 5) | I2C SCL |
| **A** | SDA | GPIO 2 (Pin 3) | I2C SDA |

## Configuration on Raspberry Pi

1. Run `sudo raspi-config`.
2. Go to **Interface Options**.
3. **Serial Port**: 
   - Login shell over serial: **No**
   - Serial port hardware enabled: **Yes**
4. **I2C**: Enable it.
5. Reboot the Pi.

## Installation

```bash
pip install -r requirements.txt
```

## Running the App

```bash
python main.py
```

*Note: If you don't see any GPS data, try changing the `BAUD_RATE` in `main.py` to `115200` or `38400`.*
