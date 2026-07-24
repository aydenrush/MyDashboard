import streamlit as st
import pandas as pd
from db import fetch_all, insert_row

st.set_page_config(page_title="CFB Dynasty", layout="wide")
st.title("CFB Dynasty Draft Tracker")

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
    st.stop()

df = df.sort_values(["school", "year", "round"])

schools = sorted(df["school"].unique())
selected_school = st.selectbox("School", schools)
school_df = df[df["school"] == selected_school]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Picks", len(school_df))
first_count = len(school_df[school_df["round"] == "1st"])
col2.metric("1st Rounders", first_count)
years_active = school_df["year"].nunique()
col3.metric("Draft Classes", years_active)
if len(school_df) > 0 and years_active > 0:
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

tab1, tab2 = st.tabs(["Draft Picks by Year", "Picks by Round"])

with tab1:
    by_year = school_df.groupby("year").size().reset_index(name="count")
    st.bar_chart(by_year.set_index("year")["count"])

with tab2:
    round_order = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "UDFA"]
    by_round = school_df.groupby("round").size().reset_index(name="count")
    by_round["round"] = pd.Categorical(by_round["round"], categories=round_order, ordered=True)
    by_round = by_round.sort_values("round")
    st.bar_chart(by_round.set_index("round")["count"])

st.divider()
with st.expander("Add Draft Pick"):
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
