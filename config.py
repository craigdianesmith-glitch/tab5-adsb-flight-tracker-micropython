DEFAULT_LAT = 55.9297
DEFAULT_LON = -4.4664
DEFAULT_LABEL = "Erskine, UK"
DEFAULT_RADIUS_NM = 25

POLL_INTERVAL_S = 10
FORGET_AFTER_S = 120

CLIMB_THRESHOLD_FPM = 150
DESCEND_THRESHOLD_FPM = -150

SETTINGS_PATH = "/flash/tracker_settings.json"

# api.airplanes.live's public point endpoint now requires contacting them for
# access (403 "feeder-only"); adsb.lol is a live, free, unauthenticated
# drop-in with the same readsb-derived JSON schema.
ADSB_API_URL = "https://api.adsb.lol/v2/point/{lat}/{lon}/{radius}"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search?name={query}&count=8&language=en&format=json"
