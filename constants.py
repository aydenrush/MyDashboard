ROUND_ORDER = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "UDFA"]

AWARD_COLS = {
    "sb_winner": "SB Winner",
    "sb_mvp": "SB MVP",
    "nfl_mvp": "NFL MVP",
    "coach_of_year": "Coach of Year",
    "opoy": "OPOY",
    "dpoy": "DPOY",
    "oroy": "OROY",
    "droy": "DROY",
}

SEASON_DISPLAY_COLS = [
    "year", "sb_winner", "sb_mvp", "nfl_mvp", "coach_of_year",
    "opoy", "dpoy", "oroy", "droy", "ninety_nine_club",
]

SEASON_COL_NAMES = {
    "year": "Year", "sb_winner": "SB Winner", "sb_mvp": "SB MVP",
    "nfl_mvp": "NFL MVP", "coach_of_year": "Coach of Year",
    "opoy": "OPOY", "dpoy": "DPOY", "oroy": "OROY", "droy": "DROY",
    "ninety_nine_club": "99 Club",
}

NFL_DIVISIONS = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West": ["ARI", "LAR", "SEA", "SF"],
}

ALL_DIV_TEAMS = [t for ts in NFL_DIVISIONS.values() for t in ts]

AP_POSITIONS_OFF = [
    "QB 1st", "QB 2nd",
    "RB 1st", "RB 2nd", "RB 3rd",
    "FB 1st", "FB 2nd",
    "WR 1st", "WR 2nd", "WR 3rd", "WR 4th", "WR 5th",
    "TE 1st", "TE 2nd",
    "OT 1st", "OT 2nd", "OT 3rd",
    "OG 1st", "OG 2nd", "OG 3rd",
    "C 1st", "C 2nd",
]
AP_POSITIONS_DEF = [
    "EDGE 1st", "EDGE 2nd", "EDGE 3rd", "EDGE 4th", "EDGE 5th", "EDGE 6th",
    "DT 1st", "DT 2nd", "DT 3rd", "DT 4th",
    "SAM 1st", "SAM 2nd",
    "MIKE 1st", "MIKE 2nd", "MIKE 3rd",
    "WILL 1st", "WILL 2nd",
    "CB 1st", "CB 2nd", "CB 3rd", "CB 4th", "CB 5th",
    "S 1st", "S 2nd", "S 3rd",
]
AP_POSITIONS_ST = ["K 1st", "K 2nd", "P 1st", "P 2nd", "KR 1st", "PR 1st", "LS 1st"]
AP_POSITIONS_ALL = AP_POSITIONS_OFF + AP_POSITIONS_DEF + AP_POSITIONS_ST

AP_ALIASES = {
    "HB": "RB 1st", "RB": "RB 1st",
    "FB": "FB 1st",
    "WR": "WR 1st", "WR 1": "WR 1st", "WR 2": "WR 2nd",
    "TE": "TE 1st",
    "LT": "OT 1st", "RT": "OT 2nd", "OT": "OT 1st",
    "LG": "OG 1st", "RG": "OG 2nd", "OG": "OG 1st",
    "C": "C 1st",
    "QB": "QB 1st",
    "LE": "EDGE 1st", "RE": "EDGE 2nd", "DE": "EDGE 1st", "EDGE": "EDGE 1st",
    "DT": "DT 1st", "DT 1": "DT 1st", "DT 2": "DT 2nd",
    "LOLB": "SAM 1st", "ROLB": "WILL 1st", "OLB": "SAM 1st",
    "MLB": "MIKE 1st", "MLB 1": "MIKE 1st", "MLB 2": "MIKE 2nd",
    "CB": "CB 1st", "CB 1": "CB 1st", "CB 2": "CB 2nd",
    "FS": "S 1st", "SS": "S 2nd", "S": "S 1st",
    "K": "K 1st", "P": "P 1st", "KR": "KR 1st", "PR": "PR 1st",
}

_ORDINALS = {"1st", "2nd", "3rd", "4th", "5th", "6th", "7th"}


def ap_display_label(pos):
    parts = pos.rsplit(" ", 1)
    if len(parts) == 2 and parts[1] in _ORDINALS:
        return parts[0]
    return pos

CLASS_AGE = {
    "FR": 19, "SO": 20, "JR": 21, "SR": 22,
    "FR(RS)": 20, "SO(RS)": 21, "JR(RS)": 22, "SR(RS)": 23,
    "RS FR": 20, "RS SO": 21, "RS JR": 22, "RS SR": 23,
}


def age_from_class(class_str):
    if not class_str:
        return None
    return CLASS_AGE.get(class_str.strip().upper())


ACTIVITY_TYPES = {
    "running": ("Running", "#F44336"),
    "lifting": ("Lifting", "#FF9800"),
    "cycling": ("Cycling", "#4CAF50"),
    "frisbee_golf": ("Frisbee Golf", "#2196F3"),
    "rap_writing": ("Rap Writing", "#9C27B0"),
    "other": ("Other", "#607D8B"),
}

TIME_SLOTS = ["Morning", "Midday", "Afternoon", "Evening"]
TIME_DISPLAY = {"Morning": "8 AM", "Midday": "11 AM", "Afternoon": "2 PM", "Evening": "5:30 PM"}
