import requests2

import config


def _quote(s):
    out = []
    for ch in s:
        if ch.isalpha() or ch.isdigit() or ch in "-_.~":
            out.append(ch)
        elif ch == " ":
            out.append("%20")
        else:
            for b in ch.encode("utf-8"):
                out.append("%%%02X" % b)
    return "".join(out)


def search(query):
    url = config.GEOCODE_URL.format(query=_quote(query))
    resp = requests2.get(url)
    try:
        if resp.status_code != 200:
            return []
        data = resp.json()
    finally:
        resp.close()

    results = []
    for r in data.get("results") or []:
        parts = [r["name"]]
        if r.get("admin1"):
            parts.append(r["admin1"])
        if r.get("country"):
            parts.append(r["country"])
        results.append(
            {
                "label": ", ".join(parts),
                "lat": r["latitude"],
                "lon": r["longitude"],
            }
        )
    return results
