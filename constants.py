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

AP_POSITIONS_OFF = ["QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
AP_POSITIONS_DEF = ["DE", "DT", "OLB", "MLB", "CB", "FS", "SS"]
AP_POSITIONS_ST = ["K", "P", "KR", "PR"]
AP_POSITIONS_ALL = AP_POSITIONS_OFF + AP_POSITIONS_DEF + AP_POSITIONS_ST

CLASS_AGE = {
    "FR": 19, "SO": 20, "JR": 21, "SR": 22,
    "FR(RS)": 20, "SO(RS)": 21, "JR(RS)": 22, "SR(RS)": 23,
    "RS FR": 20, "RS SO": 21, "RS JR": 22, "RS SR": 23,
}


def age_from_class(class_str):
    if not class_str:
        return None
    return CLASS_AGE.get(class_str.strip().upper())
