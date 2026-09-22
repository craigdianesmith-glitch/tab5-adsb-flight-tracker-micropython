import network
import time

import secrets


def connect(timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        deadline = time.time() + timeout_s
        while not wlan.isconnected() and time.time() < deadline:
            time.sleep_ms(200)
    return wlan.isconnected()
