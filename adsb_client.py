import math

import requests2

import config


def _haversine_nm(lat1, lon1, lat2, lon2):
    r_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    km = 2 * r_km * math.asin(math.sqrt(a))
    return km * 0.539957


def _status(ac):
    if ac.get("alt_baro") == "ground":
        gs = ac.get("gs")
        return "TAXI" if isinstance(gs, (int, float)) and gs > 2 else "GROUND"
    rate = ac.get("baro_rate")
    if rate is None:
        rate = ac.get("geom_rate", 0)
    if rate >= config.CLIMB_THRESHOLD_FPM:
        return "CLIMB"
    if rate <= config.DESCEND_THRESHOLD_FPM:
        return "DESCEND"
    return "LEVEL"


def fetch(lat, lon, radius_nm=None):
    radius_nm = radius_nm or config.DEFAULT_RADIUS_NM
    url = config.ADSB_API_URL.format(lat=lat, lon=lon, radius=radius_nm)
    resp = requests2.get(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        if resp.status_code != 200:
            # Raise rather than returning [] so a failed/blocked request is
            # distinguishable from a genuinely empty (but successful) result -
            # callers should keep showing the last good data on failure.
            raise OSError("ADS-B API returned status {}".format(resp.status_code))
        data = resp.json()
    finally:
        resp.close()

    out = []
    for ac in data.get("ac", []):
        hexid = ac.get("hex")
        if not hexid:
            continue
        alt = ac.get("alt_baro")
        if isinstance(alt, (int, float)) and alt < 0:
            continue  # bogus negative-altitude reports occasionally show up
        callsign = (ac.get("flight") or hexid).strip()
        actype = ac.get("t") or "----"
        alt_str = "GND" if alt == "ground" else (str(alt) if alt is not None else "?")
        speed = ac.get("gs")
        speed_str = str(round(speed)) if speed is not None else "?"
        ac_lat, ac_lon = ac.get("lat"), ac.get("lon")
        dist_nm = _haversine_nm(lat, lon, ac_lat, ac_lon) if ac_lat is not None and ac_lon is not None else None
        out.append(
            {
                "hex": hexid,
                "callsign": callsign,
                "type": actype,
                "alt": alt_str,
                "speed": speed_str,
                "dist_nm": dist_nm,
                "status": _status(ac),
            }
        )
    out.sort(key=lambda a: a["dist_nm"] if a["dist_nm"] is not None else 9999)
    return out
