import streamlit as st
from db import fetch_custom_colors

NFL_COLORS = {
    "ARI": ("#97233F", "#000000", "Cardinals"),
    "ATL": ("#A71930", "#000000", "Falcons"),
    "BAL": ("#241773", "#9E7C0C", "Ravens"),
    "BUF": ("#00338D", "#C60C30", "Bills"),
    "CAR": ("#0085CA", "#101820", "Panthers"),
    "CHI": ("#C83200", "#0B162A", "Bears"),
    "CIN": ("#FB4F14", "#000000", "Bengals"),
    "CLE": ("#311D00", "#FF3C00", "Browns"),
    "DAL": ("#003594", "#869397", "Cowboys"),
    "DEN": ("#FB4F14", "#002244", "Broncos"),
    "DET": ("#0076B6", "#B0B7BC", "Lions"),
    "GB":  ("#203731", "#FFB612", "Packers"),
    "HOU": ("#03202F", "#A71930", "Texans"),
    "IND": ("#002C5F", "#A2AAAD", "Colts"),
    "JAX": ("#006778", "#9F792C", "Jaguars"),
    "KC":  ("#E31837", "#FFB81C", "Chiefs"),
    "LAC": ("#0080C6", "#FFC20E", "Chargers"),
    "LAR": ("#003594", "#FFA300", "Rams"),
    "LV":  ("#000000", "#A5ACAF", "Raiders"),
    "MIA": ("#008E97", "#FC4C02", "Dolphins"),
    "MIN": ("#4F2683", "#FFC62F", "Vikings"),
    "NE":  ("#002244", "#C60C30", "Patriots"),
    "NO":  ("#D3BC8D", "#101820", "Saints"),
    "NYG": ("#0B2265", "#A71930", "Giants"),
    "NYJ": ("#125740", "#FFFFFF", "Jets"),
    "PHI": ("#004C54", "#A5ACAF", "Eagles"),
    "PIT": ("#FFB612", "#101820", "Steelers"),
    "SEA": ("#002244", "#69BE28", "Seahawks"),
    "SF":  ("#AA0000", "#B3995D", "49ers"),
    "TB":  ("#D50A0A", "#FF7900", "Buccaneers"),
    "TEN": ("#0C2340", "#4B92DB", "Titans"),
    "WAS": ("#5A1414", "#FFB612", "Commanders"),
    # Relocated / expansion teams from Madden saves
    "MEL": ("#0C2340", "#4B92DB", "Melbourne"),
    "HON": ("#006778", "#9F792C", "Honolulu"),
    "SAD": ("#0080C6", "#FFC20E", "San Diego"),
    "HST": ("#E31837", "#FFB81C", "Houston Stars"),
    "BKN": ("#FB4F14", "#002244", "Brooklyn"),
    "OKC": ("#0080C6", "#FFC20E", "OKC"),
    "MON": ("#008E97", "#FC4C02", "Montreal"),
    "POR": ("#203731", "#FFB612", "Portland"),
    "AUE": ("#0076B6", "#B0B7BC", "Austin"),
    "AUS": ("#0076B6", "#B0B7BC", "Austin"),
    "ANC": ("#003594", "#869397", "Anchorage"),
    "SJU": ("#0B2265", "#A71930", "San Juan"),
    "SJV": ("#0B2265", "#A71930", "San Juan"),
    "TKY": ("#D50A0A", "#FF7900", "Tokyo"),
    "TOK": ("#D50A0A", "#FF7900", "Tokyo"),
    "MEX": ("#006778", "#9F792C", "Mexico City"),
}

COLLEGE_COLORS = {
    "Vincennes":      ("#003366", "#FFFFFF"),
    "Purdue":         ("#CEB888", "#000000"),
    "Ivy Tech":       ("#003B71", "#FFFFFF"),
    "Goshen College": ("#5C2D91", "#FFFFFF"),
}


def apply_theme(primary, secondary):
    st.markdown(f"""
    <style>
    /* accent bar at top */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        display: block;
        height: 5px;
        background: linear-gradient(90deg, {primary}, {secondary}, {primary});
    }}
    /* title color */
    [data-testid="stAppViewContainer"] h1 {{
        color: {primary} !important;
    }}
    /* tab highlight */
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {primary} !important;
    }}
    /* active tab text */
    .stTabs [aria-selected="true"] {{
        color: {primary} !important;
    }}
    /* metric labels */
    [data-testid="stMetricLabel"] {{
        color: {primary} !important;
    }}
    /* buttons */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {{
        background-color: {primary} !important;
        border-color: {primary} !important;
    }}
    /* expander headers */
    [data-testid="stExpander"] summary {{
        color: {primary} !important;
    }}
    /* divider */
    hr {{
        border-color: {secondary} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=120)
def _load_custom():
    return fetch_custom_colors()


def clear_color_cache():
    _load_custom.clear()


def get_nfl_colors():
    merged = dict(NFL_COLORS)
    for row in _load_custom():
        if row["color_type"] == "nfl":
            merged[row["key"]] = (
                row["primary_color"],
                row["secondary_color"],
                row.get("display_name") or row["key"],
            )
    return merged


def get_college_colors():
    merged = dict(COLLEGE_COLORS)
    for row in _load_custom():
        if row["color_type"] == "college":
            merged[row["key"]] = (row["primary_color"], row["secondary_color"])
    return merged


def apply_nfl_theme(team_abbr):
    colors = get_nfl_colors()
    if team_abbr and team_abbr in colors:
        primary, secondary, _ = colors[team_abbr]
        apply_theme(primary, secondary)


def apply_college_theme(school):
    colors = get_college_colors()
    if school and school in colors:
        primary, secondary = colors[school]
        apply_theme(primary, secondary)
