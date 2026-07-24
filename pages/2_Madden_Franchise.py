import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, insert_rows, get_config, upsert_config
from colors import apply_nfl_theme, NFL_COLORS

st.set_page_config(page_title="Madden Franchise", layout="wide")

GAMES = {
    "Madden 24": "m24",
    "Madden 25": "m25",
    "Madden 26": "m26",
}

selected_game = st.radio("Game", list(GAMES.keys()), horizontal=True)
prefix = GAMES[selected_game]

seasons_table = f"{prefix}_seasons"
wins_table = f"{prefix}_team_wins"
allpro_table = f"{prefix}_all_pro"

seasons_data = fetch_all(seasons_table, order_col="year")
wins_data = fetch_all(wins_table, order_col="year")
seasons_df = pd.DataFrame(seasons_data)
wins_df = pd.DataFrame(wins_data)

if seasons_df.empty:
    st.info(f"No data loaded for {selected_game} yet.")
    st.stop()

franchises = sorted(seasons_df["franchise"].unique())
selected_franchise = st.selectbox("Franchise", franchises)

config = get_config(prefix, selected_franchise)
primary_team = config["primary_team"] if config else None

apply_nfl_theme(primary_team)

team_label = ""
if primary_team and primary_team in NFL_COLORS:
    team_label = f" -- {NFL_COLORS[primary_team][2]}"
st.title(f"{selected_game}: {selected_franchise}{team_label}")

with st.sidebar:
    st.subheader("Franchise Settings")
    all_teams = sorted(NFL_COLORS.keys())
    team_options = [f"{abbr} - {NFL_COLORS[abbr][2]}" for abbr in all_teams]
    current_idx = 0
    if primary_team and primary_team in all_teams:
        current_idx = all_teams.index(primary_team)
    sel_team_display = st.selectbox("Primary Team", team_options, index=current_idx)
    new_primary = sel_team_display.split(" - ")[0]
    if st.button("Save Primary Team"):
        upsert_config(prefix, selected_franchise, new_primary)
        st.success(f"Set to {new_primary}")
        st.rerun()

fran_seasons = seasons_df[
    seasons_df["franchise"] == selected_franchise
].sort_values("year")
fran_wins = (
    wins_df[wins_df["franchise"] == selected_franchise].sort_values("year")
    if not wins_df.empty
    else pd.DataFrame()
)

col1, col2, col3 = st.columns(3)
col1.metric("Seasons Played", len(fran_seasons))
sb_wins = fran_seasons["sb_winner"].notna().sum()
col2.metric("Seasons w/ SB Data", sb_wins)
if not fran_wins.empty and primary_team:
    my_wins = fran_wins[fran_wins["team"] == primary_team]["wins"].sum()
    col3.metric(f"{primary_team} Total Wins", f"{my_wins:.0f}")
elif not fran_wins.empty:
    top_team = fran_wins.groupby("team")["wins"].sum().idxmax()
    col3.metric("Top Win Team", top_team)

st.divider()

awards_tab, records_tab, allpro_tab = st.tabs(
    ["Season Awards", "Team Records", "All-Pro Teams"]
)

with awards_tab:
    display_cols = [
        "year", "sb_winner", "sb_mvp", "nfl_mvp", "coach_of_year",
        "opoy", "dpoy", "oroy", "droy", "ninety_nine_club",
    ]
    col_names = {
        "year": "Year", "sb_winner": "SB Winner", "sb_mvp": "SB MVP",
        "nfl_mvp": "NFL MVP", "coach_of_year": "Coach of Year",
        "opoy": "OPOY", "dpoy": "DPOY", "oroy": "OROY", "droy": "DROY",
        "ninety_nine_club": "99 Club",
    }
    existing = [c for c in display_cols if c in fran_seasons.columns]
    st.dataframe(
        fran_seasons[existing].rename(columns=col_names),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Award Counts")
    award_cols = ["sb_winner", "sb_mvp", "nfl_mvp", "opoy", "dpoy"]
    for acol in award_cols:
        if acol in fran_seasons.columns:
            counts = fran_seasons[acol].dropna().value_counts().head(5)
            if not counts.empty:
                with st.expander(col_names.get(acol, acol)):
                    st.dataframe(
                        counts.reset_index().rename(
                            columns={
                                "index": "Winner",
                                acol: "Winner",
                                "count": "Times",
                            }
                        ),
                        hide_index=True,
                    )

with records_tab:
    if fran_wins.empty:
        st.info("No team win records for this franchise.")
    else:
        fran_wins_clean = fran_wins[fran_wins["wins"].notna()]

        years_list = sorted(fran_wins_clean["year"].unique())
        sel_year = st.selectbox(
            "Select Year", years_list,
            index=len(years_list) - 1 if years_list else 0,
        )
        year_data = fran_wins_clean[
            fran_wins_clean["year"] == sel_year
        ].sort_values("wins", ascending=False)
        if not year_data.empty:
            st.bar_chart(year_data.set_index("team")["wins"])

        st.subheader("All-Time Team Wins")
        total_wins = (
            fran_wins_clean.groupby("team")["wins"]
            .sum()
            .sort_values(ascending=False)
        )
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
            "Year", sorted(allpro_df["year"].unique()), key="ap_year",
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

add_single, add_bulk, add_wins = st.tabs(
    ["Add Single Season", "Bulk Add Seasons", "Add Team Wins"]
)

with add_single:
    with st.form("add_season"):
        fc1, fc2 = st.columns(2)
        new_fran = fc1.selectbox("Franchise", franchises, key="new_fran")
        new_year = fc2.number_input(
            "Year", min_value=2023, max_value=2060, value=2027,
        )
        fc3, fc4, fc5 = st.columns(3)
        new_sb = fc3.text_input("SB Winner")
        new_mvp = fc4.text_input("SB MVP")
        new_nfl_mvp = fc5.text_input("NFL MVP")
        fc6, fc7, fc8 = st.columns(3)
        new_coy = fc6.text_input("Coach of Year")
        new_opoy = fc7.text_input("OPOY")
        new_dpoy = fc8.text_input("DPOY")
        fc9, fc10, fc11 = st.columns(3)
        new_oroy = fc9.text_input("OROY")
        new_droy = fc10.text_input("DROY")
        new_99 = fc11.text_input("99 Club")

        if st.form_submit_button("Add Season"):
            insert_row(seasons_table, {
                "franchise": new_fran, "year": new_year,
                "sb_winner": new_sb or None, "sb_mvp": new_mvp or None,
                "nfl_mvp": new_nfl_mvp or None,
                "coach_of_year": new_coy or None,
                "opoy": new_opoy or None, "dpoy": new_dpoy or None,
                "oroy": new_oroy or None, "droy": new_droy or None,
                "ninety_nine_club": new_99 or None,
            })
            st.success("Season added.")
            st.rerun()

with add_bulk:
    st.markdown("Paste tab-separated rows. Columns:")
    st.code(
        "Year\tSB Winner\tSB MVP\tNFL MVP\tCoach of Year"
        "\tOPOY\tDPOY\tOROY\tDROY\t99 Club"
    )
    bulk_fran = st.text_input(
        "Franchise for all rows", value=selected_franchise, key="bulk_fran",
    )
    bulk_text = st.text_area("Paste rows here", height=200, key="bulk_madden")

    if st.button("Preview", key="preview_madden"):
        if bulk_text.strip():
            rows = []
            for line in bulk_text.strip().split("\n"):
                cols = line.split("\t")
                if len(cols) >= 1:
                    rows.append({
                        "Year": cols[0] if len(cols) > 0 else "",
                        "SB Winner": cols[1] if len(cols) > 1 else "",
                        "SB MVP": cols[2] if len(cols) > 2 else "",
                        "NFL MVP": cols[3] if len(cols) > 3 else "",
                        "Coach of Year": cols[4] if len(cols) > 4 else "",
                        "OPOY": cols[5] if len(cols) > 5 else "",
                        "DPOY": cols[6] if len(cols) > 6 else "",
                        "OROY": cols[7] if len(cols) > 7 else "",
                        "DROY": cols[8] if len(cols) > 8 else "",
                        "99 Club": cols[9] if len(cols) > 9 else "",
                    })
            if rows:
                st.dataframe(
                    pd.DataFrame(rows), hide_index=True,
                    use_container_width=True,
                )
                st.session_state["bulk_madden_parsed"] = rows

    if st.button("Upload", key="upload_madden"):
        parsed = st.session_state.get("bulk_madden_parsed", [])
        if not parsed:
            st.error("Preview first to validate the data.")
        else:
            db_rows = []
            for r in parsed:
                try:
                    year_val = int(float(r.get("Year", "")))
                except (ValueError, TypeError):
                    continue
                db_rows.append({
                    "franchise": bulk_fran,
                    "year": year_val,
                    "sb_winner": r.get("SB Winner", "").strip() or None,
                    "sb_mvp": r.get("SB MVP", "").strip() or None,
                    "nfl_mvp": r.get("NFL MVP", "").strip() or None,
                    "coach_of_year": r.get("Coach of Year", "").strip() or None,
                    "opoy": r.get("OPOY", "").strip() or None,
                    "dpoy": r.get("DPOY", "").strip() or None,
                    "oroy": r.get("OROY", "").strip() or None,
                    "droy": r.get("DROY", "").strip() or None,
                    "ninety_nine_club": r.get("99 Club", "").strip() or None,
                })
            if db_rows:
                insert_rows(seasons_table, db_rows)
                st.success(f"Uploaded {len(db_rows)} seasons.")
                st.session_state.pop("bulk_madden_parsed", None)
                st.rerun()

with add_wins:
    st.markdown("Enter records (W-L or W-L-T) by division. Wins are calculated automatically.")

    with st.form("add_team_wins"):
        wf1, wf2 = st.columns(2)
        wins_fran = wf1.text_input(
            "Franchise", value=selected_franchise, key="wins_fran",
        )
        wins_year = wf2.number_input(
            "Year", min_value=2023, max_value=2060, value=2027, key="wins_year",
        )

        afc_col, nfc_col = st.columns(2)

        with afc_col:
            st.subheader("AFC")
            for div_name in ["AFC East", "AFC North", "AFC South", "AFC West"]:
                st.markdown(f"**{div_name}**")
                teams = NFL_DIVISIONS[div_name]
                c1, c2, c3, c4 = st.columns(4)
                for col, team in zip([c1, c2, c3, c4], teams):
                    label = f"{team}"
                    if team in NFL_COLORS:
                        label = f"{team} ({NFL_COLORS[team][2]})"
                    col.text_input(
                        label, placeholder="W-L", key=f"rec_{team}",
                    )

        with nfc_col:
            st.subheader("NFC")
            for div_name in ["NFC East", "NFC North", "NFC South", "NFC West"]:
                st.markdown(f"**{div_name}**")
                teams = NFL_DIVISIONS[div_name]
                c1, c2, c3, c4 = st.columns(4)
                for col, team in zip([c1, c2, c3, c4], teams):
                    label = f"{team}"
                    if team in NFL_COLORS:
                        label = f"{team} ({NFL_COLORS[team][2]})"
                    col.text_input(
                        label, placeholder="W-L", key=f"rec_{team}",
                    )

        st.markdown("**Custom / Relocated Teams**")
        st.caption("One per line: ABBR W-L (e.g. MEL 10-7)")
        custom_records = st.text_area(
            "Custom teams", height=80, key="custom_team_records",
            label_visibility="collapsed",
        )

        if st.form_submit_button("Submit Records"):
            db_rows = []
            errors = []
            all_div_teams = [
                t for teams in NFL_DIVISIONS.values() for t in teams
            ]
            for team in all_div_teams:
                record = st.session_state.get(f"rec_{team}", "").strip()
                if not record:
                    continue
                parts = record.split("-")
                try:
                    wins = int(parts[0])
                except (ValueError, IndexError):
                    errors.append(f"{team}: invalid record '{record}'")
                    continue
                db_rows.append({
                    "franchise": wins_fran,
                    "year": wins_year,
                    "team": team,
                    "wins": wins,
                })

            if custom_records and custom_records.strip():
                for line in custom_records.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 2:
                        errors.append(f"Bad custom line: '{line}'")
                        continue
                    team_abbr = parts[0].upper()
                    record = parts[1]
                    rec_parts = record.split("-")
                    try:
                        wins = int(rec_parts[0])
                    except (ValueError, IndexError):
                        errors.append(f"{team_abbr}: invalid record '{record}'")
                        continue
                    db_rows.append({
                        "franchise": wins_fran,
                        "year": wins_year,
                        "team": team_abbr,
                        "wins": wins,
                    })

            if errors:
                for e in errors:
                    st.error(e)
            if db_rows:
                insert_rows(wins_table, db_rows)
                st.success(f"Uploaded {len(db_rows)} team win records.")
                st.rerun()
            elif not errors:
                st.warning("No records entered.")

    with st.expander("Bulk Paste (wide format)"):
        st.markdown(
            "First row = header with team abbreviations. "
            "Subsequent rows = Year + wins per team."
        )
        st.code("Year\tARI\tATL\tBAL\t...\n2024\t10\t8\t12\t...")
        paste_fran = st.text_input(
            "Franchise for all rows", value=selected_franchise, key="paste_wins_fran",
        )
        wins_text = st.text_area("Paste rows here", height=200, key="bulk_wins")

        if st.button("Preview", key="preview_wins"):
            if wins_text.strip():
                lines = wins_text.strip().split("\n")
                if len(lines) >= 2:
                    headers = lines[0].split("\t")
                    team_cols = headers[1:]
                    preview_rows = []
                    for line in lines[1:]:
                        vals = line.split("\t")
                        row = {"Year": vals[0]}
                        for i, team in enumerate(team_cols):
                            row[team] = vals[i + 1] if i + 1 < len(vals) else ""
                        preview_rows.append(row)
                    if preview_rows:
                        st.dataframe(
                            pd.DataFrame(preview_rows), hide_index=True,
                            use_container_width=True,
                        )
                        st.session_state["bulk_wins_parsed"] = {
                            "teams": team_cols,
                            "rows": preview_rows,
                        }
                else:
                    st.error("Need a header row + at least one data row.")

        if st.button("Upload", key="upload_wins"):
            parsed = st.session_state.get("bulk_wins_parsed")
            if not parsed:
                st.error("Preview first to validate the data.")
            else:
                db_rows = []
                for r in parsed["rows"]:
                    try:
                        year_val = int(float(r["Year"]))
                    except (ValueError, TypeError):
                        continue
                    for team in parsed["teams"]:
                        wins_val = r.get(team, "").strip()
                        if not wins_val:
                            continue
                        try:
                            wins_num = float(wins_val)
                        except (ValueError, TypeError):
                            continue
                        db_rows.append({
                            "franchise": paste_fran,
                            "year": year_val,
                            "team": team.strip(),
                            "wins": wins_num,
                        })
                if db_rows:
                    insert_rows(wins_table, db_rows)
                    st.success(f"Uploaded {len(db_rows)} team win records.")
                    st.session_state.pop("bulk_wins_parsed", None)
                    st.rerun()
                else:
                    st.error("No valid data found.")
