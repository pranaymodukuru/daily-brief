"""Today's forecast from Open-Meteo (free, no account or key)."""

import json
import urllib.parse
import urllib.request

# WMO weather codes, grouped.
CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Showers", 81: "Showers", 82: "Heavy showers", 85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorms", 96: "Thunderstorms with hail", 99: "Thunderstorms with hail",
}
PARTS = {"morning": 8, "midday": 13, "evening": 18}


def _get(url: str, **params) -> dict:
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=20) as r:
        return json.load(r)


def forecast(cfg: dict) -> dict:
    """cfg: {place, latitude?, longitude?}. Returns the numbers plus a printable line."""
    place = cfg.get("place", "")
    lat, lon = cfg.get("latitude"), cfg.get("longitude")
    if lat is None or lon is None:
        hits = _get("https://geocoding-api.open-meteo.com/v1/search", name=place, count=1).get("results")
        if not hits:
            raise SystemExit(f"weather: place not found: {place!r}")
        lat, lon = hits[0]["latitude"], hits[0]["longitude"]
    f = _get("https://api.open-meteo.com/v1/forecast", latitude=lat, longitude=lon, timezone="auto",
             forecast_days=1, hourly="temperature_2m",
             daily="weather_code,temperature_2m_max,temperature_2m_min,"
                   "precipitation_probability_max,sunrise,sunset")
    d = {k: v[0] for k, v in f["daily"].items()}
    temps = dict(zip((t[11:13] for t in f["hourly"]["time"]), f["hourly"]["temperature_2m"]))
    parts = {name: round(temps[f"{h:02d}"]) for name, h in PARTS.items()}
    out = {
        "place": place,
        "conditions": CODES.get(d["weather_code"], "Mixed"),
        "low": round(d["temperature_2m_min"]),
        "high": round(d["temperature_2m_max"]),
        "rain_chance": d["precipitation_probability_max"],
        "parts": parts,
        "sunrise": d["sunrise"][11:16],
        "sunset": d["sunset"][11:16],
    }
    out["line"] = " · ".join(filter(None, [
        place,
        f"{out['conditions']}, {out['low']}–{out['high']} °C",
        f"rain {out['rain_chance']}%" if out["rain_chance"] is not None else "",
        ", ".join(f"{k} {v}°" for k, v in parts.items()),
        f"sunrise {out['sunrise']}, sunset {out['sunset']}",
    ]))
    return out
