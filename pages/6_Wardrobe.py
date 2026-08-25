import streamlit as st
import colorsys
from auth import require_login

st.set_page_config(page_title="Wardrobe", layout="wide")
require_login()

st.title("What Goes With This?")
st.caption("Pick the color you're wearing — see what pairs well with it.")


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


def swatch(hex_color, label, size=60):
    text_color = "#fff" if hex_to_hsl(hex_color)[2] < 55 else "#222"
    return (
        f'<div style="background:{hex_color};color:{text_color};'
        f'width:{size}px;height:{size}px;border-radius:10px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:0.6em;font-weight:600;text-align:center;'
        f'border:1px solid rgba(128,128,128,0.3);padding:4px;">'
        f'{label}</div>'
    )


def swatch_row(colors, labels):
    cards = "".join(swatch(c, l, 80) for c, l in zip(colors, labels))
    return (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:8px 0;">'
        f'{cards}</div>'
    )


PRESETS = {
    "Navy": "#1a2744",
    "Royal Blue": "#2563eb",
    "Baby Blue": "#89CFF0",
    "Black": "#111111",
    "White": "#f5f5f5",
    "Gray": "#808080",
    "Charcoal": "#36454F",
    "Cream": "#FFFDD0",
    "Khaki": "#c3b091",
    "Olive": "#556B2F",
    "Forest Green": "#228B22",
    "Sage": "#9DC183",
    "Burgundy": "#800020",
    "Red": "#cc0000",
    "Pink": "#FF69B4",
    "Orange": "#FF6600",
    "Burnt Orange": "#CC5500",
    "Yellow": "#FFD700",
    "Purple": "#6A0DAD",
    "Lavender": "#B57EDC",
    "Tan": "#D2B48C",
    "Brown": "#5C4033",
    "Teal": "#008080",
    "Coral": "#FF6F61",
    "Maroon": "#800000",
}

pc1, pc2 = st.columns([1, 1])
with pc1:
    preset = st.selectbox(
        "Quick pick", ["Custom..."] + list(PRESETS.keys()),
    )
with pc2:
    if preset != "Custom...":
        picked = st.color_picker("Fine-tune", value=PRESETS[preset])
    else:
        picked = st.color_picker("Pick your color", value="#2563eb")

h, s, l = hex_to_hsl(picked)
name = color_name(h, s, l)

st.markdown(
    f'<div style="display:flex;align-items:center;gap:16px;margin:16px 0;">'
    f'<div style="width:80px;height:80px;border-radius:14px;background:{picked};'
    f'border:2px solid rgba(128,128,128,0.3);"></div>'
    f'<div><div style="font-size:1.4em;font-weight:700;">{name}</div>'
    f'<div style="font-size:0.85em;opacity:0.6;">{picked}</div></div></div>',
    unsafe_allow_html=True,
)

st.divider()


def complementary(h, s, l):
    return [(h + 180) % 360, s, l]


def analogous(h, s, l):
    return [
        [(h - 30) % 360, s, l],
        [(h + 30) % 360, s, l],
    ]


def triadic(h, s, l):
    return [
        [(h + 120) % 360, s, l],
        [(h + 240) % 360, s, l],
    ]


def split_comp(h, s, l):
    return [
        [(h + 150) % 360, s, l],
        [(h + 210) % 360, s, l],
    ]


NEUTRALS = [
    ("#ffffff", "White"),
    ("#f5f5f5", "Off-White"),
    ("#FFFDD0", "Cream"),
    ("#c3b091", "Khaki"),
    ("#D2B48C", "Tan"),
    ("#808080", "Gray"),
    ("#36454F", "Charcoal"),
    ("#222222", "Black"),
]

is_neutral = s < 12 or l < 12 or l > 88


def render_palette(title, hsl_list, description=""):
    colors = [hsl_to_hex(h2, s2, l2) for h2, s2, l2 in hsl_list]
    labels = [color_name(h2, s2, l2) for h2, s2, l2 in hsl_list]
    st.markdown(f"**{title}**")
    if description:
        st.caption(description)
    st.markdown(swatch_row(colors, labels), unsafe_allow_html=True)


if is_neutral:
    st.subheader("Neutrals go with everything")
    st.caption("You picked a neutral — almost any color works. Here are some strong options:")

    pops = [
        (0, 70, 50), (210, 70, 45), (130, 50, 40),
        (30, 80, 50), (280, 50, 45), (350, 65, 50),
        (50, 80, 50), (175, 60, 40),
    ]
    render_palette(
        "Pop Colors",
        pops,
        "Add a bold accent to keep the fit interesting",
    )

    earth = [
        (25, 40, 35), (35, 50, 55), (85, 25, 40),
        (15, 30, 30), (30, 35, 65), (45, 30, 50),
    ]
    render_palette(
        "Earth Tones",
        earth,
        "Muted, warm tones for a relaxed look",
    )

    st.markdown("**Other Neutrals**")
    st.caption("Layer neutrals for a clean, minimal fit")
    neutral_colors = [c for c, _ in NEUTRALS]
    neutral_labels = [l for _, l in NEUTRALS]
    st.markdown(swatch_row(neutral_colors, neutral_labels), unsafe_allow_html=True)

else:
    comp = complementary(h, s, l)
    render_palette(
        "Complementary",
        [comp],
        "Opposite on the color wheel — bold contrast",
    )

    ana = analogous(h, s, l)
    render_palette(
        "Analogous",
        ana,
        "Neighbors on the wheel — smooth, cohesive",
    )

    tri = triadic(h, s, l)
    render_palette(
        "Triadic",
        tri,
        "Evenly spaced — vibrant but balanced",
    )

    sc = split_comp(h, s, l)
    render_palette(
        "Split Complementary",
        sc,
        "Softer take on complementary — less clash",
    )

    muted = max(s - 25, 10)
    toned = [
        [h, muted, min(l + 20, 85)],
        [h, muted, max(l - 15, 20)],
        [(h + 180) % 360, muted, min(l + 15, 80)],
    ]
    render_palette(
        "Toned Down",
        toned,
        "Same family but softer — easy to wear",
    )

    st.markdown("**Safe Neutrals**")
    st.caption("Always works — pair with any of the above")
    neutral_colors = [c for c, _ in NEUTRALS]
    neutral_labels = [l for _, l in NEUTRALS]
    st.markdown(swatch_row(neutral_colors, neutral_labels), unsafe_allow_html=True)

st.divider()

st.subheader("Quick Rules")
st.markdown("""
- **Monochrome**: different shades of the same color — hard to mess up
- **Neutral + 1 color**: safest everyday fit
- **Complementary**: bold — use one as the main, the other as a small accent
- **Analogous**: smooth, low-effort — colors next to each other always vibe
- **Don't match too hard**: your shoes/hat don't need to be the exact same shade — close is better than identical
""")
