import streamlit as st
import colorsys
import json
import base64
import io
import math
from datetime import datetime
from collections import Counter
from PIL import Image
from auth import require_login
from db import fetch_all, insert_row, delete_row, get_setting, set_setting

st.set_page_config(page_title="Wardrobe", layout="wide")
require_login()

st.title("Wardrobe")

CATEGORIES = ["Tops", "Bottoms", "Outerwear", "Shoes", "Accessories"]
WEATHER_TAGS = ["Hot (85+)", "Warm (70-85)", "Mild (55-70)", "Cool (40-55)", "Cold (<40)"]
WEATHER_TAG_MAP = {"Hot (85+)": "hot", "Warm (70-85)": "warm", "Mild (55-70)": "mild", "Cool (40-55)": "cool", "Cold (<40)": "cold"}

# ---------- color helpers (kept from original) ----------

def hex_to_hsl(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, sat * 100, light * 100


def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def color_name(h, s, l):
    if s < 10:
        if l > 85:
            return "White"
        if l < 15:
            return "Black"
        return "Gray"
    if l < 12:
        return "Black"
    if l > 90:
        return "White"
    names = [
        (0, "Red"), (15, "Red-Orange"), (30, "Orange"), (45, "Gold"),
        (55, "Yellow"), (75, "Yellow-Green"), (100, "Lime"), (130, "Green"),
        (160, "Teal"), (185, "Cyan"), (210, "Blue"), (240, "Indigo"),
        (265, "Violet"), (285, "Purple"), (310, "Magenta"), (335, "Pink"),
        (350, "Rose"), (360, "Red"),
    ]
    for i in range(len(names) - 1):
        if h < names[i + 1][0]:
            name = names[i][1]
            break
    else:
        name = "Red"
    if l < 30:
        return f"Dark {name}"
    if l > 70:
        return f"Light {name}"
    return name


def swatch(hex_color, label="", size=40):
    text_color = "#fff" if hex_to_hsl(hex_color)[2] < 55 else "#222"
    return (
        f'<div style="background:{hex_color};color:{text_color};'
        f'width:{size}px;height:{size}px;border-radius:8px;'
        f'display:inline-flex;align-items:center;justify-content:center;'
        f'font-size:0.55em;font-weight:600;text-align:center;'
        f'border:1px solid rgba(128,128,128,0.3);padding:2px;">'
        f'{label}</div>'
    )


def extract_colors(image_bytes, n=4):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((40, 40))
    pixels = list(img.getdata())
    quantized = []
    for r, g, b in pixels:
        qr, qg, qb = (r // 24) * 24, (g // 24) * 24, (b // 24) * 24
        quantized.append((min(qr, 255), min(qg, 255), min(qb, 255)))
    counter = Counter(quantized)
    top = counter.most_common(n * 3)
    results = []
    for (r, g, b), _ in top:
        hex_c = f"#{r:02x}{g:02x}{b:02x}"
        h, s, l = hex_to_hsl(hex_c)
        too_close = False
        for existing in results:
            eh, es, el = hex_to_hsl(existing)
            if abs(eh - h) < 20 and abs(es - s) < 15 and abs(el - l) < 15:
                too_close = True
                break
        if not too_close:
            results.append(hex_c)
        if len(results) >= n:
            break
    return results


def resize_thumbnail(image_bytes, max_size=300):
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def colors_compatible(c1_hex, c2_hex):
    h1, s1, l1 = hex_to_hsl(c1_hex)
    h2, s2, l2 = hex_to_hsl(c2_hex)
    is_neutral_1 = s1 < 12 or l1 < 12 or l1 > 88
    is_neutral_2 = s2 < 12 or l2 < 12 or l2 > 88
    if is_neutral_1 or is_neutral_2:
        return True
    hue_diff = min(abs(h1 - h2), 360 - abs(h1 - h2))
    if hue_diff < 40:
        return True
    if 150 < hue_diff < 210:
        return True
    if 100 < hue_diff < 140 or 220 < hue_diff < 260:
        return True
    return False


# ---------- weather ----------

def _fetch_weather(lat, lon):
    import urllib.request
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,precipitation_probability"
        f"&temperature_unit=fahrenheit&timezone=auto&forecast_days=1"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _weather_category(temp_f):
    if temp_f >= 85:
        return "hot"
    if temp_f >= 70:
        return "warm"
    if temp_f >= 55:
        return "mild"
    if temp_f >= 40:
        return "cool"
    return "cold"


def _geocode(city):
    import urllib.request
    import urllib.parse
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=en&format=json"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                return r["latitude"], r["longitude"], r.get("name", city)
    except Exception:
        pass
    return None

# ---------- load wardrobe data ----------

try:
    _wardrobe_data = fetch_all("wardrobe_items", order_col="created_at")
except Exception:
    _wardrobe_data = None

if _wardrobe_data is None:
    st.error("Table `wardrobe_items` not found. Create it in Supabase:")
    st.code(
        "create table wardrobe_items (\n"
        "    id bigint generated by default as identity primary key,\n"
        "    name text not null,\n"
        "    category text not null,\n"
        "    colors jsonb,\n"
        "    weather_tags jsonb,\n"
        "    image_b64 text,\n"
        "    created_at timestamptz default now()\n"
        ");\n\n"
        "-- RLS\n"
        "alter table wardrobe_items enable row level security;\n"
        "create policy \"Allow All\" on wardrobe_items for all using (true) with check (true);",
        language="sql",
    )
    st.stop()

_wardrobe_df = json.dumps(None)
_items = _wardrobe_data

# ---------- weather section ----------

_saved_loc = get_setting("wardrobe_location")
_lat, _lon, _city_name = None, None, None

if _saved_loc:
    try:
        _loc = json.loads(_saved_loc)
        _lat, _lon, _city_name = _loc["lat"], _loc["lon"], _loc["city"]
    except Exception:
        pass

with st.expander("Weather & Best Time to Go Out", expanded=_lat is not None):
    _wc1, _wc2 = st.columns([3, 1])
    _city_input = _wc1.text_input("City", value=_city_name or "", placeholder="e.g. West Lafayette")
    if _wc2.button("Set Location", key="set_loc"):
        if _city_input.strip():
            result = _geocode(_city_input.strip())
            if result:
                _lat, _lon, _city_name = result
                set_setting("wardrobe_location", json.dumps({"lat": _lat, "lon": _lon, "city": _city_name}))
                st.rerun()
            else:
                st.error("City not found")

    if _lat and _lon:
        weather = _fetch_weather(_lat, _lon)
        if weather and "hourly" in weather:
            hours = weather["hourly"]
            temps = hours["temperature_2m"]
            humids = hours["relative_humidity_2m"]
            precip = hours.get("precipitation_probability", [0] * 24)
            times = hours["time"]

            now_hour = datetime.now().hour

            current_temp = temps[now_hour] if now_hour < len(temps) else temps[-1]
            current_humid = humids[now_hour] if now_hour < len(humids) else humids[-1]
            current_precip = precip[now_hour] if now_hour < len(precip) else 0
            cat = _weather_category(current_temp)

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Now", f"{current_temp:.0f}°F")
            mc2.metric("Humidity", f"{current_humid}%")
            mc3.metric("Rain Chance", f"{current_precip}%")
            mc4.metric("Dress For", cat.title())

            best_hour = None
            best_score = float("inf")
            for hi in range(max(now_hour, 6), min(22, len(temps))):
                t = temps[hi]
                h = humids[hi]
                p = precip[hi] if hi < len(precip) else 0
                comfort = abs(t - 72) + (h * 0.5) + (p * 0.3)
                if comfort < best_score:
                    best_score = comfort
                    best_hour = hi

            if best_hour is not None:
                _bt = temps[best_hour]
                _bh = humids[best_hour]
                _bp = precip[best_hour] if best_hour < len(precip) else 0
                _period = "AM" if best_hour < 12 else "PM"
                _disp_hour = best_hour % 12 or 12
                st.info(
                    f"Best time to go out: **{_disp_hour} {_period}** — "
                    f"{_bt:.0f}°F, {_bh}% humidity"
                    f"{f', {_bp}% rain chance' if _bp > 0 else ''}"
                )

            high_humid_hours = [i for i in range(len(humids)) if humids[i] >= 70 and i >= now_hour]
            if high_humid_hours:
                _hh_start = high_humid_hours[0]
                _hh_p = "AM" if _hh_start < 12 else "PM"
                _hh_d = _hh_start % 12 or 12
                st.warning(f"High humidity ({humids[_hh_start]}%+) starting around {_hh_d} {_hh_p}")
        else:
            st.warning("Couldn't fetch weather data")

st.divider()

# ---------- color matcher (original feature) ----------

with st.expander("What Goes With This?"):
    st.caption("Pick the color you're wearing — see what pairs well with it.")

    PRESETS = {
        "Navy": "#1a2744", "Royal Blue": "#2563eb", "Baby Blue": "#89CFF0",
        "Black": "#111111", "White": "#f5f5f5", "Gray": "#808080",
        "Charcoal": "#36454F", "Cream": "#FFFDD0", "Khaki": "#c3b091",
        "Olive": "#556B2F", "Forest Green": "#228B22", "Sage": "#9DC183",
        "Burgundy": "#800020", "Red": "#cc0000", "Pink": "#FF69B4",
        "Orange": "#FF6600", "Burnt Orange": "#CC5500", "Yellow": "#FFD700",
        "Purple": "#6A0DAD", "Lavender": "#B57EDC", "Tan": "#D2B48C",
        "Brown": "#5C4033", "Teal": "#008080", "Coral": "#FF6F61",
        "Maroon": "#800000",
    }

    pc1, pc2 = st.columns([1, 1])
    with pc1:
        preset = st.selectbox("Quick pick", ["Custom..."] + list(PRESETS.keys()))
    with pc2:
        if preset != "Custom...":
            picked = st.color_picker("Fine-tune", value=PRESETS[preset])
        else:
            picked = st.color_picker("Pick your color", value="#2563eb")

    h, s, l = hex_to_hsl(picked)
    name = color_name(h, s, l)

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;margin:16px 0;">'
        f'<div style="width:60px;height:60px;border-radius:12px;background:{picked};'
        f'border:2px solid rgba(128,128,128,0.3);"></div>'
        f'<div><div style="font-size:1.2em;font-weight:700;">{name}</div>'
        f'<div style="font-size:0.85em;opacity:0.6;">{picked}</div></div></div>',
        unsafe_allow_html=True,
    )

    def swatch_row(colors, labels):
        cards = "".join(swatch(c, l, 60) for c, l in zip(colors, labels))
        return f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;">{cards}</div>'

    def render_palette(title, hsl_list, description=""):
        colors = [hsl_to_hex(h2, s2, l2) for h2, s2, l2 in hsl_list]
        labels = [color_name(h2, s2, l2) for h2, s2, l2 in hsl_list]
        st.markdown(f"**{title}**")
        if description:
            st.caption(description)
        st.markdown(swatch_row(colors, labels), unsafe_allow_html=True)

    is_neutral = s < 12 or l < 12 or l > 88

    if is_neutral:
        pops = [
            (0, 70, 50), (210, 70, 45), (130, 50, 40),
            (30, 80, 50), (280, 50, 45), (350, 65, 50),
        ]
        render_palette("Pop Colors", pops, "Add a bold accent")
        earth = [(25, 40, 35), (35, 50, 55), (85, 25, 40), (15, 30, 30)]
        render_palette("Earth Tones", earth, "Muted, warm tones")
    else:
        render_palette("Complementary", [[(h + 180) % 360, s, l]], "Opposite on the wheel — bold contrast")
        render_palette("Analogous", [[(h - 30) % 360, s, l], [(h + 30) % 360, s, l]], "Neighbors — smooth, cohesive")
        render_palette("Split Complementary", [[(h + 150) % 360, s, l], [(h + 210) % 360, s, l]], "Softer contrast")

    # matching items from wardrobe
    if _items:
        _matching = []
        for item in _items:
            item_colors = item.get("colors") or []
            for ic in item_colors:
                if colors_compatible(picked, ic):
                    _matching.append(item)
                    break
        if _matching:
            st.markdown(f"**{len(_matching)} items from your closet match:**")
            _match_cols = st.columns(min(len(_matching), 5))
            for i, item in enumerate(_matching[:10]):
                with _match_cols[i % 5]:
                    if item.get("image_b64"):
                        st.image(base64.b64decode(item["image_b64"]), width=100)
                    st.caption(item["name"])

st.divider()

# ---------- my closet ----------

st.subheader("My Closet")

if not _items:
    st.info("No items yet — upload some clothes below.")
else:
    _cat_tabs = st.tabs(CATEGORIES)
    for _ci, _cat in enumerate(CATEGORIES):
        with _cat_tabs[_ci]:
            _cat_items = [it for it in _items if it.get("category") == _cat]
            if not _cat_items:
                st.caption("Nothing here yet")
                continue
            _cols = st.columns(4)
            for _ii, _item in enumerate(_cat_items):
                with _cols[_ii % 4]:
                    if _item.get("image_b64"):
                        st.image(base64.b64decode(_item["image_b64"]), width=150)
                    st.markdown(f"**{_item['name']}**")
                    _ic = _item.get("colors") or []
                    if _ic:
                        _swatches = "".join(swatch(c, "", 24) for c in _ic)
                        st.markdown(
                            f'<div style="display:flex;gap:4px;margin:4px 0;">{_swatches}</div>',
                            unsafe_allow_html=True,
                        )
                    _wt = _item.get("weather_tags") or []
                    if _wt:
                        st.caption(", ".join(_wt))

st.divider()

# ---------- outfit suggestions ----------

if _items and _lat:
    weather = _fetch_weather(_lat, _lon)
    if weather and "hourly" in weather:
        now_hour = datetime.now().hour
        current_temp = weather["hourly"]["temperature_2m"][min(now_hour, 23)]
        cat = _weather_category(current_temp)

        _tops = [it for it in _items if it.get("category") == "Tops" and cat in (it.get("weather_tags") or [])]
        _bots = [it for it in _items if it.get("category") == "Bottoms" and cat in (it.get("weather_tags") or [])]
        _outer = [it for it in _items if it.get("category") == "Outerwear" and cat in (it.get("weather_tags") or [])]

        if _tops and _bots:
            with st.expander(f"Outfit Suggestions ({cat.title()} weather, {current_temp:.0f}°F)"):
                _combos = []
                for t in _tops:
                    for b in _bots:
                        t_colors = t.get("colors") or []
                        b_colors = b.get("colors") or []
                        if t_colors and b_colors:
                            if any(colors_compatible(tc, bc) for tc in t_colors for bc in b_colors):
                                _combos.append((t, b))
                        else:
                            _combos.append((t, b))

                if not _combos:
                    st.caption("No color-compatible combos found — try adding more items")
                else:
                    for _oi, (_t, _b) in enumerate(_combos[:6]):
                        _oc1, _oc2 = st.columns(2)
                        with _oc1:
                            if _t.get("image_b64"):
                                st.image(base64.b64decode(_t["image_b64"]), width=120)
                            st.caption(f"Top: {_t['name']}")
                        with _oc2:
                            if _b.get("image_b64"):
                                st.image(base64.b64decode(_b["image_b64"]), width=120)
                            st.caption(f"Bottom: {_b['name']}")
                        if _outer:
                            st.caption(f"Layer: {_outer[0]['name']}")
                        st.markdown("---")

st.divider()

# ---------- add item ----------

with st.expander("Add Item"):
    _up_file = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "webp"], key="ward_upload")
    _ac1, _ac2 = st.columns(2)
    _item_name = _ac1.text_input("Name", placeholder="e.g. Blue Nike Dri-Fit")
    _item_cat = _ac2.selectbox("Category", CATEGORIES)
    _item_weather = st.multiselect("Suitable weather", WEATHER_TAGS, default=["Warm (70-85)", "Mild (55-70)"])

    _extracted = []
    _img_b64 = None

    if _up_file:
        _raw = _up_file.read()
        st.image(_raw, width=200)
        _extracted = extract_colors(_raw, n=4)
        _thumb = resize_thumbnail(_raw, 300)
        _img_b64 = base64.b64encode(_thumb).decode()

        if _extracted:
            st.markdown("**Detected colors:**")
            _sw = "".join(swatch(c, color_name(*hex_to_hsl(c)), 50) for c in _extracted)
            st.markdown(f'<div style="display:flex;gap:6px;margin:8px 0;">{_sw}</div>', unsafe_allow_html=True)

    if st.button("Save Item", key="save_ward") and _item_name.strip():
        _tags = [WEATHER_TAG_MAP[w] for w in _item_weather]
        insert_row("wardrobe_items", {
            "name": _item_name.strip(),
            "category": _item_cat,
            "colors": _extracted if _extracted else None,
            "weather_tags": _tags,
            "image_b64": _img_b64,
        })
        st.success(f"Added {_item_name.strip()}!")
        st.rerun()

# ---------- delete items ----------

if _items:
    with st.expander("Delete Items"):
        for _item in _items:
            _dc1, _dc2, _dc3 = st.columns([1, 8, 1])
            if _item.get("image_b64"):
                _dc1.image(base64.b64decode(_item["image_b64"]), width=40)
            _dc2.caption(f"{_item['name']} ({_item.get('category', '')})")
            if _dc3.button("X", key=f"del_w_{_item['id']}"):
                delete_row("wardrobe_items", _item["id"])
                st.rerun()
