import streamlit as st
import pandas as pd
import altair as alt
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
apparent = hours.get("apparent_temperature", temps)
humids = hours["relative_humidity_2m"]
dewpoint = hours.get("dewpoint_2m", [None] * len(temps))
precip = hours.get("precipitation_probability", [0] * len(temps))
times = hours["time"]

now = datetime.now()
now_hour = now.hour

# ---------- current conditions ----------

st.subheader(f"Now in {_city_name}")
current_temp = temps[now_hour] if now_hour < len(temps) else temps[-1]
current_feels = apparent[now_hour] if now_hour < len(apparent) else apparent[-1]
current_humid = humids[now_hour] if now_hour < len(humids) else humids[-1]
current_precip = precip[now_hour] if now_hour < len(precip) else 0
current_dp = dewpoint[now_hour] if now_hour < len(dewpoint) and dewpoint[now_hour] is not None else None
cat = weather_category(current_feels)

mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Temperature", f"{current_temp:.0f}°F")
mc2.metric("Feels Like", f"{current_feels:.0f}°F")
mc3.metric("Dew Point", f"{current_dp:.0f}°F" if current_dp is not None else "—")
mc4.metric("Humidity", f"{current_humid}%")
mc5.metric("Rain Chance", f"{current_precip}%")
st.caption(f"Dress for: **{cat.title()}**")

st.divider()

# ---------- best times ----------

_best_out = best_outdoor_hour(temps, humids, precip, now_hour, apparent=apparent)
_best_run = best_run_hour(temps, humids, precip, now_hour, apparent=apparent, dewpoint=dewpoint)

bc1, bc2 = st.columns(2)
if _best_out is not None:
    _bo_t = temps[_best_out]
    _bo_f = apparent[_best_out]
    _bo_h = humids[_best_out]
    _feels_note = f" (feels {_bo_f:.0f}°F)" if abs(_bo_f - _bo_t) >= 2 else ""
    bc1.info(
        f"Best time to go out: **{fmt_hour(_best_out)}** — "
        f"{_bo_t:.0f}°F{_feels_note}, {_bo_h}% humidity"
    )
if _best_run is not None:
    _br_t = temps[_best_run]
    _br_f = apparent[_best_run]
    _br_dp = dewpoint[_best_run] if _best_run < len(dewpoint) else None
    _br_p = precip[_best_run] if _best_run < len(precip) else 0
    _feels_note = f" (feels {_br_f:.0f}°F)" if abs(_br_f - _br_t) >= 2 else ""
    _dp_note = f", dew point {_br_dp:.0f}°F" if _br_dp is not None else ""
    bc2.success(
        f"Best time to run: **{fmt_hour(_best_run)}** — "
        f"{_br_t:.0f}°F{_feels_note}{_dp_note}"
        f"{f', {_br_p}% rain' if _br_p > 0 else ''}"
    )

_run_deadline = st.select_slider(
    "I won't run later than", options=[f"{fmt_hour(h)}" for h in range(17, 24)],
    value=fmt_hour(22), key="run_deadline",
)
_dl_map = {fmt_hour(h): h for h in range(17, 23)}
_dl_hour = _dl_map.get(_run_deadline, 21)
_custom_best = best_run_hour(temps, humids, precip, now_hour, deadline=_dl_hour, apparent=apparent, dewpoint=dewpoint)
if _custom_best is not None and _custom_best != _best_run:
    _cb_t = temps[_custom_best]
    _cb_f = apparent[_custom_best]
    _cb_dp = dewpoint[_custom_best] if _custom_best < len(dewpoint) else None
    _feels_note = f" (feels {_cb_f:.0f}°F)" if abs(_cb_f - _cb_t) >= 2 else ""
    _dp_note = f", dew point {_cb_dp:.0f}°F" if _cb_dp is not None else ""
    st.caption(f"With that cutoff: best run time is {fmt_hour(_custom_best)} — {_cb_t:.0f}°F{_feels_note}{_dp_note}")

high_dp_hours = [i for i in range(now_hour, min(24, len(dewpoint)))
                 if dewpoint[i] is not None and dewpoint[i] >= 65]
if high_dp_hours:
    _hdp_start = high_dp_hours[0]
    _hdp_val = dewpoint[_hdp_start]
    _severity = "Oppressive" if _hdp_val >= 70 else "Uncomfortable"
    st.warning(f"{_severity} dew point ({_hdp_val:.0f}°F) starting around {fmt_hour(_hdp_start)} — consider an easy effort")

st.divider()

# ---------- today hourly chart ----------

st.subheader("Today")

_today_end = min(24, len(temps))
_today_labels = [fmt_hour(h) for h in range(_today_end)]

_today_df = pd.DataFrame({
    "Hour": _today_labels,
    "Temp (°F)": temps[:_today_end],
    "Feels Like (°F)": apparent[:_today_end],
    "Humidity (%)": humids[:_today_end],
    "Rain (%)": [precip[h] if h < len(precip) else 0 for h in range(_today_end)],
})

_hour_sort = _today_labels
_chart_tab1, _chart_tab2, _chart_tab3 = st.tabs(["Temperature", "Humidity", "Rain Chance"])

with _chart_tab1:
    _temp_melt = _today_df[["Hour", "Temp (°F)", "Feels Like (°F)"]].melt(
        "Hour", var_name="Metric", value_name="Temperature")
    st.altair_chart(alt.Chart(_temp_melt).mark_line().encode(
        x=alt.X("Hour:N", sort=_hour_sort, title="Hour"),
        y=alt.Y("Temperature:Q", title="°F"),
        color=alt.Color("Metric:N", legend=alt.Legend(title=None)),
    ), use_container_width=True)
with _chart_tab2:
    st.altair_chart(alt.Chart(_today_df).mark_line(color="#2196F3").encode(
        x=alt.X("Hour:N", sort=_hour_sort, title="Hour"),
        y=alt.Y("Humidity (%):Q", title="Humidity (%)"),
    ), use_container_width=True)
with _chart_tab3:
    st.altair_chart(alt.Chart(_today_df).mark_bar(color="#4CAF50").encode(
        x=alt.X("Hour:N", sort=_hour_sort, title="Hour"),
        y=alt.Y("Rain (%):Q", title="Rain (%)"),
    ), use_container_width=True)

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
    _d_feels = apparent[_d_start:_d_end]
    _d_humids = humids[_d_start:_d_end]
    _d_precip = precip[_d_start:_d_end] if _d_start < len(precip) else []
    _d_date = (now + timedelta(days=d)).strftime("%A %m/%d")
    _days_data.append({
        "date": _d_date,
        "high": max(_d_temps) if _d_temps else 0,
        "low": min(_d_temps) if _d_temps else 0,
        "feels_high": max(_d_feels) if _d_feels else 0,
        "feels_low": min(_d_feels) if _d_feels else 0,
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
        st.caption(f"Feels like: {_dd['feels_high']:.0f}° / {_dd['feels_low']:.0f}°")
        st.caption(f"Humidity avg: {_dd['avg_humid']:.0f}%")
        st.caption(f"Max rain chance: {_dd['max_rain']}%")
        _cat = weather_category((_dd["feels_high"] + _dd["feels_low"]) / 2)
        st.caption(f"Dress for: {_cat.title()}")

# hourly chart for all 3 days
_all_labels = []
for i in range(len(temps)):
    _day_offset = i // 24
    _hour = i % 24
    _day_date = (now + timedelta(days=_day_offset)).strftime("%m/%d")
    _all_labels.append(f"{_day_date} {_hour:02d}:00")
_all_hours_df = pd.DataFrame({
    "Hour": _all_labels[:len(temps)],
    "Temp (°F)": temps[:len(_all_labels)],
    "Humidity (%)": humids[:len(_all_labels)],
    "Rain (%)": precip[:len(_all_labels)] if len(precip) >= len(_all_labels) else precip + [0] * (len(_all_labels) - len(precip)),
})

with st.expander("Full 3-Day Hourly"):
    _all_sort = _all_labels[:len(temps)]
    _fc1, _fc2 = st.tabs(["Temperature & Humidity", "Rain Chance"])
    with _fc1:
        _all_melt = _all_hours_df[["Hour", "Temp (°F)", "Humidity (%)"]].melt(
            "Hour", var_name="Metric", value_name="Value")
        st.altair_chart(alt.Chart(_all_melt).mark_line().encode(
            x=alt.X("Hour:N", sort=_all_sort, title="Hour"),
            y=alt.Y("Value:Q"),
            color=alt.Color("Metric:N", legend=alt.Legend(title=None)),
        ), use_container_width=True)
    with _fc2:
        st.altair_chart(alt.Chart(_all_hours_df).mark_bar(color="#4CAF50").encode(
            x=alt.X("Hour:N", sort=_all_sort, title="Hour"),
            y=alt.Y("Rain (%):Q", title="Rain (%)"),
        ), use_container_width=True)
