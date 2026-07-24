import streamlit as st
import pandas as pd
from db import fetch_all, insert_row

st.set_page_config(page_title="Madden Franchise", layout="wide")
st.title("Madden Franchise Records")

GAMES = {
    "Madden 24": "m24",
    "Madden 25": "m25",
    "Madden 26": "m26",
}

selected_game = st.selectbox("Game", list(GAMES.keys()))
prefix = GAMES[selected_game]

seasons_table = f"{prefix}_seasons"
wins_table = f"{prefix}_team_wins"
allpro_table = f"{prefix}_all_pro"

seasons_data = fetch_all(seasons_table, order_col="year")
wins_data = fetch_all(wins_table, order_col="year")
seasons_df = pd.DataFrame(seasons_data)
wins_df = pd.DataFrame(wins_data)

if seasons_df.empty:
    st.info("No Madden data loaded yet. Run upload_data.py to populate.")
    st.stop()

franchises = sorted(seasons_df["franchise"].unique())
selected_franchise = st.selectbox("Franchise", franchises)

fran_seasons = seasons_df[seasons_df["franchise"] == selected_franchise].sort_values("year")
fran_wins = wins_df[wins_df["franchise"] == selected_franchise].sort_values("year") if not wins_df.empty else pd.DataFrame()

col1, col2, col3 = st.columns(3)
col1.metric("Seasons Played", len(fran_seasons))
sb_count = fran_seasons["sb_winner"].notna().sum()
col2.metric("Seasons w/ SB Data", sb_count)
if not fran_wins.empty:
    user_team = fran_wins.groupby("team")["wins"].sum().idxmax()
    col3.metric("Top Win Team", user_team)

st.divider()

awards_tab, records_tab, allpro_tab = st.tabs(["Season Awards", "Team Records", "All-Pro Teams"])

with awards_tab:
    display_cols = ["year", "sb_winner", "sb_mvp", "nfl_mvp", "coach_of_year",
                    "opoy", "dpoy", "oroy", "droy", "ninety_nine_club"]
    col_names = {
        "year": "Year", "sb_winner": "SB Winner", "sb_mvp": "SB MVP",
        "nfl_mvp": "NFL MVP", "coach_of_year": "Coach of Year",
        "opoy": "OPOY", "dpoy": "DPOY", "oroy": "OROY", "droy": "DROY",
        "ninety_nine_club": "99 Club"
    }
    existing = [c for c in display_cols if c in fran_seasons.columns]
    st.dataframe(
        fran_seasons[existing].rename(columns=col_names),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Award Counts")
    award_cols = ["sb_winner", "sb_mvp", "nfl_mvp", "opoy", "dpoy"]
    for col_name in award_cols:
        if col_name in fran_seasons.columns:
            counts = fran_seasons[col_name].dropna().value_counts().head(5)
            if not counts.empty:
                with st.expander(col_names.get(col_name, col_name)):
                    st.dataframe(counts.reset_index().rename(
                        columns={"index": "Winner", col_name: "Winner", "count": "Times"}
                    ), hide_index=True)

with records_tab:
    if fran_wins.empty:
        st.info("No team win records for this franchise.")
    else:
        fran_wins_clean = fran_wins[fran_wins["wins"].notna()]

        sel_year = st.selectbox(
            "Select Year",
            sorted(fran_wins_clean["year"].unique()),
            index=len(fran_wins_clean["year"].unique()) - 1 if len(fran_wins_clean["year"].unique()) > 0 else 0
        )
        year_data = fran_wins_clean[fran_wins_clean["year"] == sel_year].sort_values("wins", ascending=False)
        if not year_data.empty:
            st.bar_chart(year_data.set_index("team")["wins"])

        st.subheader("All-Time Team Wins")
        total_wins = fran_wins_clean.groupby("team")["wins"].sum().sort_values(ascending=False)
        if not total_wins.empty:
            st.bar_chart(total_wins)

with allpro_tab:
    try:
        allpro_data = fetch_all(allpro_table, order_col="year")
    except Exception:
        allpro_data = []
    allpro_df = pd.DataFrame(allpro_data)

    if allpro_df.empty:
        st.info("No All-Pro data for this game.")
    else:
        sel_ap_year = st.selectbox(
            "Year", sorted(allpro_df["year"].unique()), key="ap_year"
        )
        year_ap = allpro_df[allpro_df["year"] == sel_ap_year]
        st.dataframe(
            year_ap[["position_label", "player"]].rename(
                columns={"position_label": "Position", "player": "Player"}
            ),
            use_container_width=True,
            hide_index=True,
        )

st.divider()
with st.expander("Add Season Record"):
    with st.form("add_season"):
        fc1, fc2 = st.columns(2)
        new_fran = fc1.selectbox("Franchise", franchises, key="new_fran")
        new_year = fc2.number_input("Year", min_value=2023, max_value=2060, value=2027)
        fc3, fc4, fc5 = st.columns(3)
        new_sb = fc3.text_input("SB Winner")
        new_mvp = fc4.text_input("SB MVP")
        new_nfl_mvp = fc5.text_input("NFL MVP")
        fc6, fc7, fc8 = st.columns(3)
        new_coy = fc6.text_input("Coach of Year")
        new_opoy = fc7.text_input("OPOY")
        new_dpoy = fc8.text_input("DPOY")
        fc9, fc10 = st.columns(2)
        new_oroy = fc9.text_input("OROY")
        new_droy = fc10.text_input("DROY")

        if st.form_submit_button("Add Season"):
            insert_row(seasons_table, {
                "franchise": new_fran, "year": new_year,
                "sb_winner": new_sb or None, "sb_mvp": new_mvp or None,
                "nfl_mvp": new_nfl_mvp or None, "coach_of_year": new_coy or None,
                "opoy": new_opoy or None, "dpoy": new_dpoy or None,
                "oroy": new_oroy or None, "droy": new_droy or None,
            })
            st.success("Season added.")
            st.rerun()
