import json

import config


def load():
    try:
        with open(config.SETTINGS_PATH) as f:
            data = json.load(f)
        return (
            data.get("lat", config.DEFAULT_LAT),
            data.get("lon", config.DEFAULT_LON),
            data.get("label", config.DEFAULT_LABEL),
        )
    except (OSError, ValueError):
        return config.DEFAULT_LAT, config.DEFAULT_LON, config.DEFAULT_LABEL


def save(lat, lon, label):
    with open(config.SETTINGS_PATH, "w") as f:
        json.dump({"lat": lat, "lon": lon, "label": label}, f)
