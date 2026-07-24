import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, insert_rows
from colors import apply_college_theme
from auth import require_login

st.set_page_config(page_title="CFB Dynasty", layout="wide")
require_login()

GAMES = {
    "CFB 25": "cfb25_draft_picks",
    "CFB 26": "cfb26_draft_picks",
    "CFB 27": "cfb27_draft_picks",
}

selected_game = st.selectbox("Game", list(GAMES.keys()))
table = GAMES[selected_game]

data = fetch_all(table, order_col="year")
df = pd.DataFrame(data)

if df.empty:
    st.info("No draft pick data loaded yet. Run upload_data.py to populate.")

schools = sorted(df["school"].unique()) if not df.empty else []
selected_school = st.selectbox("School", schools) if schools else None

apply_college_theme(selected_school)
st.title(f"{selected_game} Draft Tracker")

if df.empty or not selected_school:
    st.stop()

school_df = df[df["school"] == selected_school].sort_values(["year", "round"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Picks", len(school_df))
first_count = len(school_df[school_df["round"] == "1st"])
col2.metric("1st Rounders", first_count)
years_active = school_df["year"].nunique()
col3.metric("Draft Classes", years_active)
if years_active > 0:
    col4.metric("Avg Picks/Year", f"{len(school_df) / years_active:.1f}")

st.divider()

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    positions = sorted(school_df["position"].dropna().unique())
    sel_positions = st.multiselect("Position", positions)
with filter_col2:
    rounds = sorted(school_df["round"].dropna().unique())
    sel_rounds = st.multiselect("Round", rounds)
with filter_col3:
    years = sorted(school_df["year"].dropna().unique())
    sel_years = st.multiselect("Year", [int(y) for y in years])

filtered = school_df.copy()
if sel_positions:
    filtered = filtered[filtered["position"].isin(sel_positions)]
if sel_rounds:
    filtered = filtered[filtered["round"].isin(sel_rounds)]
if sel_years:
    filtered = filtered[filtered["year"].isin(sel_years)]

display_cols = ["year", "name", "position", "class", "draft_age", "height", "weight",
                "number", "race", "round", "additional_notes"]
st.dataframe(
    filtered[display_cols].rename(columns={
        "year": "Year", "name": "Name", "position": "Pos", "class": "Class",
        "draft_age": "Age", "height": "Ht", "weight": "Wt", "number": "#",
        "race": "Race", "round": "Round", "additional_notes": "Notes"
    }),
    use_container_width=True,
    hide_index=True,
)

st.divider()

tab_chart1, tab_chart2 = st.tabs(["Draft Picks by Year", "Picks by Round"])

with tab_chart1:
    by_year = school_df.groupby("year").size().reset_index(name="count")
    st.bar_chart(by_year.set_index("year")["count"])

with tab_chart2:
    round_order = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "UDFA"]
    by_round = school_df.groupby("round").size().reset_index(name="count")
    by_round["round"] = pd.Categorical(by_round["round"], categories=round_order, ordered=True)
    by_round = by_round.sort_values("round")
    st.bar_chart(by_round.set_index("round")["count"])

st.divider()

add_single, add_bulk = st.tabs(["Add Single Pick", "Bulk Add"])

with add_single:
    with st.form("add_pick"):
        fc1, fc2, fc3 = st.columns(3)
        new_school = fc1.text_input("School", value=selected_school)
        new_year = fc2.number_input("Year", min_value=2024, max_value=2060, value=2027)
        new_name = fc3.text_input("Player Name")
        fc4, fc5, fc6 = st.columns(3)
        new_pos = fc4.text_input("Position")
        new_class = fc5.text_input("Class (e.g., SR, JR(RS))")
        new_round = fc6.selectbox("Round", ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "UDFA"])
        fc7, fc8, fc9 = st.columns(3)
        new_age = fc7.number_input("Draft Age", min_value=18, max_value=30, value=22)
        new_height = fc8.text_input("Height (e.g., 6'2\")")
        new_weight = fc9.number_input("Weight", min_value=100, max_value=400, value=200)
        fc10, fc11 = st.columns(2)
        new_number = fc10.text_input("Jersey Number")
        new_notes = fc11.text_input("Additional Notes")

        if st.form_submit_button("Add Pick"):
            if new_name:
                insert_row(table, {
                    "school": new_school, "year": new_year, "name": new_name,
                    "position": new_pos, "class": new_class, "round": new_round,
                    "draft_age": new_age, "height": new_height, "weight": new_weight,
                    "number": new_number, "additional_notes": new_notes or None,
                })
                st.success(f"Added {new_name}")
                st.rerun()
            else:
                st.error("Player name is required.")

with add_bulk:
    st.markdown("Paste tab-separated rows. Columns:")
    st.code("Year\tName\tPosition\tClass\tDraft Age\tHeight\tWeight\tNumber\tRace\tRound\tNotes")
    bulk_school = st.text_input("School for all rows", value=selected_school, key="bulk_school")
    bulk_text = st.text_area("Paste rows here", height=200, key="bulk_cfb")

    if st.button("Preview", key="preview_cfb"):
        if bulk_text.strip():
            rows = []
            for line in bulk_text.strip().split("\n"):
                cols = line.split("\t")
                if len(cols) >= 2:
                    rows.append({
                        "Year": cols[0] if len(cols) > 0 else "",
                        "Name": cols[1] if len(cols) > 1 else "",
                        "Position": cols[2] if len(cols) > 2 else "",
                        "Class": cols[3] if len(cols) > 3 else "",
                        "Draft Age": cols[4] if len(cols) > 4 else "",
                        "Height": cols[5] if len(cols) > 5 else "",
                        "Weight": cols[6] if len(cols) > 6 else "",
                        "Number": cols[7] if len(cols) > 7 else "",
                        "Race": cols[8] if len(cols) > 8 else "",
                        "Round": cols[9] if len(cols) > 9 else "",
                        "Notes": cols[10] if len(cols) > 10 else "",
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                st.session_state["bulk_cfb_parsed"] = rows

    if st.button("Upload", key="upload_cfb"):
        parsed = st.session_state.get("bulk_cfb_parsed", [])
        if not parsed:
            st.error("Preview first to validate the data.")
        else:
            db_rows = []
            for r in parsed:
                name = r.get("Name", "").strip()
                if not name:
                    continue
                year_val = None
                try:
                    year_val = int(float(r.get("Year", "")))
                except (ValueError, TypeError):
                    pass
                age_val = None
                try:
                    age_val = int(float(r.get("Draft Age", "")))
                except (ValueError, TypeError):
                    pass
                weight_val = None
                try:
                    weight_val = float(r.get("Weight", "").replace("lbs", "").strip())
                except (ValueError, TypeError):
                    pass
                num = r.get("Number", "").replace("#", "").strip() or None
                db_rows.append({
                    "school": bulk_school,
                    "year": year_val,
                    "name": name,
                    "position": r.get("Position", "").strip() or None,
                    "class": r.get("Class", "").strip() or None,
                    "draft_age": age_val,
                    "height": r.get("Height", "").strip() or None,
                    "weight": weight_val,
                    "number": num,
                    "race": r.get("Race", "").strip() or None,
                    "round": r.get("Round", "").strip() or None,
                    "additional_notes": r.get("Notes", "").strip() or None,
                })
            if db_rows:
                insert_rows(table, db_rows)
                st.success(f"Uploaded {len(db_rows)} picks.")
                st.session_state.pop("bulk_cfb_parsed", None)
                st.rerun()
