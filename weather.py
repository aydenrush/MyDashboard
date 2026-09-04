import json
import urllib.request
import urllib.parse


def fetch_weather(lat, lon, days=3):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,dewpoint_2m,precipitation_probability"
        f"&temperature_unit=fahrenheit&timezone=auto&forecast_days={days}"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def geocode(city):
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search?"
        f"name={urllib.parse.quote(city)}&count=1&language=en&format=json"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                return r["latitude"], r["longitude"], r.get("name", city)
    except Exception:
        pass
    return None


def weather_category(temp_f):
    if temp_f >= 85:
        return "hot"
    if temp_f >= 70:
        return "warm"
    if temp_f >= 55:
        return "mild"
    if temp_f >= 40:
        return "cool"
    return "cold"


def best_outdoor_hour(temps, humids, precip, now_hour, earliest=6, latest=21, apparent=None):
    best_hour = None
    best_score = float("inf")
    for hi in range(max(now_hour, earliest), min(latest + 1, len(temps))):
        t = apparent[hi] if apparent and hi < len(apparent) else temps[hi]
        h = humids[hi]
        p = precip[hi] if hi < len(precip) else 0
        score = abs(t - 72) + (h * 0.5) + (p * 0.3)
        if score < best_score:
            best_score = score
            best_hour = hi
    return best_hour


def best_run_hour(temps, humids, precip, now_hour, deadline=21, apparent=None, dewpoint=None):
    best_hour = None
    best_score = float("inf")
    for hi in range(max(now_hour, 5), min(deadline + 1, len(temps))):
        t = apparent[hi] if apparent and hi < len(apparent) else temps[hi]
        dp = dewpoint[hi] if dewpoint and hi < len(dewpoint) else None
        p = precip[hi] if hi < len(precip) else 0
        if dp is not None:
            dp_penalty = max(0, dp - 55) * 1.5
        else:
            dp_penalty = humids[hi] * 0.7
        score = abs(t - 65) + dp_penalty + (p * 0.5)
        if score < best_score:
            best_score = score
            best_hour = hi
    return best_hour


def fmt_hour(hour):
    period = "AM" if hour < 12 else "PM"
    disp = hour % 12 or 12
    return f"{disp} {period}"
