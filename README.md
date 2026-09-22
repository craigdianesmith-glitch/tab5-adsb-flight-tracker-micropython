# Overhead

A live ADS-B flight tracker for the [M5Stack Tab5](https://docs.m5stack.com/en/core/Tab5), written in MicroPython for UIFlow2. Polls [adsb.lol](https://adsb.lol) for aircraft near a configurable location and shows them in a full-screen table with callsign, type, altitude, speed, distance and climb/descend/level status, with newly-arrived aircraft highlighted in green for one refresh.

## Hardware

- M5Stack Tab5 (5" 1280x720 touchscreen, ESP32-P4/ESP32-C6)
- Flashed with the UIFlow2 firmware via [M5Burner](https://docs.m5stack.com/en/uiflow2/m5burner/intro)

## Setup

1. Copy `secrets.py.example` to `secrets.py` and fill in your WiFi credentials (`secrets.py` is gitignored).
2. Deploy all `.py` files to the device's flash root, e.g. with [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html):
   ```
   mpremote connect <port> fs cp config.py secrets.py wifi.py settings.py adsb_client.py geocode.py tracker.py main.py :
   ```
3. Reset the device. By default UIFlow2 shows its launcher menu on boot; to auto-run this app instead, set `boot_option` to `0` in the `uiflow` NVS namespace:
   ```python
   import esp32
   nvs = esp32.NVS("uiflow")
   nvs.set_u8("boot_option", 0)
   nvs.commit()
   ```

## Layout

- `main.py` - entry point
- `tracker.py` - app state, UI construction, and the main loop
- `adsb_client.py` - adsb.lol polling and aircraft data parsing
- `geocode.py` - Open-Meteo location search for the "set location" screen
- `settings.py` - persists the chosen location to flash
- `wifi.py` - WiFi connection
- `config.py` - tunable constants (poll interval, radius, thresholds)

## Known limitations

- The network fetch runs synchronously (briefly pausing the UI each poll) - sockets can't be created from a secondary `_thread` on this firmware.
- Table rows have no scrolling; only the first ~11 aircraft in range are shown.
