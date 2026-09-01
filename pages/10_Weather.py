import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from auth import require_login
from db import get_setting, set_setting
from weather import fetch_weather, geocode, weather_category, best_outdoor_hour, best_run_hour, fmt_hour

st.set_page_config(page_title="Weather", layout="wide")
require_login()

st.title("Weather")

# ---------- location ----------

_saved_loc = get_setting("wardrobe_location")
_lat, _lon, _city_name = None, None, None

if _saved_loc:
    try:
        _loc = json.loads(_saved_loc)
        _lat, _lon, _city_name = _loc["lat"], _loc["lon"], _loc["city"]
    except Exception:
        pass

_wc1, _wc2 = st.columns([3, 1])
_city_input = _wc1.text_input("City", value=_city_name or "", placeholder="e.g. West Lafayette")
if _wc2.button("Set Location", key="set_loc"):
    if _city_input.strip():
        result = geocode(_city_input.strip())
        if result:
            _lat, _lon, _city_name = result
            set_setting("wardrobe_location", json.dumps({"lat": _lat, "lon": _lon, "city": _city_name}))
            st.rerun()
        else:
            st.error("City not found")

if not _lat or not _lon:
    st.info("Set your city above to see the forecast.")
    st.stop()

weather = fetch_weather(_lat, _lon, days=3)
if not weather or "hourly" not in weather:
    st.error("Couldn't fetch weather data")
    st.stop()

hours = weather["hourly"]
temps = hours["temperature_2m"]
humids = hours["relative_humidity_2m"]
precip = hours.get("precipitation_probability", [0] * len(temps))
times = hours["time"]

now = datetime.now()
now_hour = now.hour

# ---------- current conditions ----------

st.subheader(f"Now in {_city_name}")
current_temp = temps[now_hour] if now_hour < len(temps) else temps[-1]
current_humid = humids[now_hour] if now_hour < len(humids) else humids[-1]
current_precip = precip[now_hour] if now_hour < len(precip) else 0
cat = weather_category(current_temp)

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Temperature", f"{current_temp:.0f}°F")
mc2.metric("Humidity", f"{current_humid}%")
mc3.metric("Rain Chance", f"{current_precip}%")
mc4.metric("Dress For", cat.title())

st.divider()

# ---------- best times ----------

_best_out = best_outdoor_hour(temps, humids, precip, now_hour)
_best_run = best_run_hour(temps, humids, precip, now_hour)

bc1, bc2 = st.columns(2)
if _best_out is not None:
    _bo_t = temps[_best_out]
    _bo_h = humids[_best_out]
    bc1.info(
        f"Best time to go out: **{fmt_hour(_best_out)}** — "
        f"{_bo_t:.0f}°F, {_bo_h}% humidity"
    )
if _best_run is not None:
    _br_t = temps[_best_run]
    _br_h = humids[_best_run]
    _br_p = precip[_best_run] if _best_run < len(precip) else 0
    bc2.success(
        f"Best time to run: **{fmt_hour(_best_run)}** — "
        f"{_br_t:.0f}°F, {_br_h}% humidity"
        f"{f', {_br_p}% rain' if _br_p > 0 else ''}"
    )

_run_deadline = st.select_slider(
    "I won't run later than", options=[f"{fmt_hour(h)}" for h in range(17, 23)],
    value=fmt_hour(21), key="run_deadline",
)
_dl_map = {fmt_hour(h): h for h in range(17, 23)}
_dl_hour = _dl_map.get(_run_deadline, 21)
_custom_best = best_run_hour(temps, humids, precip, now_hour, deadline=_dl_hour)
if _custom_best is not None and _custom_best != _best_run:
    _cb_t = temps[_custom_best]
    _cb_h = humids[_custom_best]
    st.caption(f"With that cutoff: best run time is {fmt_hour(_custom_best)} — {_cb_t:.0f}°F, {_cb_h}% humidity")

high_humid_hours = [i for i in range(now_hour, min(24, len(humids))) if humids[i] >= 70]
if high_humid_hours:
    _hh_start = high_humid_hours[0]
    st.warning(f"High humidity ({humids[_hh_start]}%+) starting around {fmt_hour(_hh_start)}")

st.divider()

# ---------- today hourly chart ----------

st.subheader("Today")

_today_start = 0
_today_end = min(24, len(temps))
_today_hours = list(range(_today_start, _today_end))
_today_labels = [fmt_hour(h) for h in _today_hours]

_today_df = pd.DataFrame({
    "Hour": _today_labels,
    "Temp (°F)": [temps[h] for h in _today_hours],
    "Humidity (%)": [humids[h] for h in _today_hours],
    "Rain (%)": [precip[h] if h < len(precip) else 0 for h in _today_hours],
})

_chart_tab1, _chart_tab2, _chart_tab3 = st.tabs(["Temperature", "Humidity", "Rain Chance"])

with _chart_tab1:
    st.line_chart(_today_df, x="Hour", y="Temp (°F)", color="#FF6B35")
with _chart_tab2:
    st.line_chart(_today_df, x="Hour", y="Humidity (%)", color="#2196F3")
with _chart_tab3:
    st.bar_chart(_today_df, x="Hour", y="Rain (%)", color="#4CAF50")

st.divider()

# ---------- 3-day forecast ----------

st.subheader("3-Day Forecast")

_days_data = []
for d in range(3):
    _d_start = d * 24
    _d_end = min((d + 1) * 24, len(temps))
    if _d_start >= len(temps):
        break
    _d_temps = temps[_d_start:_d_end]
    _d_humids = humids[_d_start:_d_end]
    _d_precip = precip[_d_start:_d_end] if _d_start < len(precip) else []
    _d_date = (now + timedelta(days=d)).strftime("%A %m/%d")
    _days_data.append({
        "date": _d_date,
        "high": max(_d_temps) if _d_temps else 0,
        "low": min(_d_temps) if _d_temps else 0,
        "avg_humid": sum(_d_humids) / len(_d_humids) if _d_humids else 0,
        "max_rain": max(_d_precip) if _d_precip else 0,
        "temps": _d_temps,
        "humids": _d_humids,
        "precip": _d_precip,
    })

_day_cols = st.columns(len(_days_data))
for _di, _dd in enumerate(_days_data):
    with _day_cols[_di]:
        st.markdown(f"**{_dd['date']}**")
        st.metric("High / Low", f"{_dd['high']:.0f}° / {_dd['low']:.0f}°")
        st.caption(f"Humidity avg: {_dd['avg_humid']:.0f}%")
        st.caption(f"Max rain chance: {_dd['max_rain']}%")
        _cat = weather_category((_dd["high"] + _dd["low"]) / 2)
        st.caption(f"Dress for: {_cat.title()}")

# hourly chart for all 3 days
_all_hours_df = pd.DataFrame({
    "Hour": [times[i][11:16] for i in range(len(temps))],
    "Temp (°F)": temps[:len(times)],
    "Humidity (%)": humids[:len(times)],
    "Rain (%)": precip[:len(times)] if len(precip) >= len(times) else precip + [0] * (len(times) - len(precip)),
})

with st.expander("Full 3-Day Hourly"):
    _fc1, _fc2 = st.tabs(["Temperature & Humidity", "Rain Chance"])
    with _fc1:
        st.line_chart(_all_hours_df, x="Hour", y=["Temp (°F)", "Humidity (%)"])
    with _fc2:
        st.bar_chart(_all_hours_df, x="Hour", y="Rain (%)", color="#4CAF50")
