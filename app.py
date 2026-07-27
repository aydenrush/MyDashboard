import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db import fetch_all, fetch_games, update_row
from auth import require_login
from colors import get_nfl_colors
from constants import ROUND_ORDER, AWARD_COLS

st.set_page_config(page_title="My Dashboard", layout="wide")
require_login()

st.title("Dashboard")
st.link_button("Ayden Music", "https://aydenmusic.streamlit.app")

NFL_COLORS = get_nfl_colors()

today = date.today()

# --- Today's Workout ---
try:
    schedule = fetch_all("running_schedule", order_col="date")
    sched_df = pd.DataFrame(schedule)
    if not sched_df.empty:
        sched_df["date"] = pd.to_datetime(sched_df["date"]).dt.date
except Exception:
    sched_df = pd.DataFrame()

run_col, progress_col = st.columns([3, 2])

with run_col:
    st.subheader("Today's Workout")
    if not sched_df.empty:
        today_row = sched_df[sched_df["date"] == today]
        if not today_row.empty:
            row = today_row.iloc[0]
            title = row["workout"].split("\n")[0]
            details = "\n".join(row["workout"].split("\n")[1:]).strip()
            is_rest = "Rest" in title
            if row["completed"]:
                st.success(f"~~{title}~~ — Done!")
            elif is_rest:
                st.info(title)
            else:
                st.markdown(f"**{title}**")
                if details:
                    st.caption(details)
                if st.button("Mark Complete"):
                    update_row("running_schedule", int(row["id"]), {"completed": True})
                    st.rerun()

            tomorrow = today + timedelta(days=1)
            next_row = sched_df[sched_df["date"] == tomorrow]
            if not next_row.empty:
                nxt = next_row.iloc[0]["workout"].split("\n")[0]
                st.caption(f"Tomorrow: {nxt}")
        else:
            st.info("No workout scheduled today.")
    else:
        st.info("No running schedule loaded.")

with progress_col:
    st.subheader("Running Progress")
    if not sched_df.empty:
        non_rest = sched_df[~sched_df["workout"].str.startswith("Rest")]
        total = len(non_rest)
        done = int(non_rest["completed"].sum())
        upcoming = len(non_rest[(non_rest["date"] >= today) & (~non_rest["completed"])])

        m1, m2, m3 = st.columns(3)
        m1.metric("Done", done)
        m2.metric("Upcoming", upcoming)
        m3.metric("Progress", f"{done / total * 100:.0f}%" if total else "—")
        st.progress(done / total if total else 0)

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week = sched_df[(sched_df["date"] >= week_start) & (sched_df["date"] <= week_end)]
        day_names = ["M", "T", "W", "T", "F", "S", "S"]
        cols = st.columns(7)
        for i, col in enumerate(cols):
            d = week_start + timedelta(days=i)
            day_row = week[week["date"] == d]
            with col:
                if not day_row.empty:
                    r = day_row.iloc[0]
                    is_rest = "Rest" in r["workout"].split("\n")[0]
                    label = f"**{day_names[i]}**" if d == today else day_names[i]
                    if r["completed"]:
                        col.markdown(f"{label}\n\n:white_check_mark:")
                    elif is_rest:
                        col.markdown(f"{label}\n\n—")
                    elif d < today:
                        col.markdown(f"{label}\n\n:x:")
                    else:
                        col.markdown(f"{label}\n\n:circle:")
                else:
                    col.markdown(f"{day_names[i]}\n\n—")

st.divider()

# --- Load all data ---
cfb_games = fetch_games("cfb")
madden_games = fetch_games("madden")

all_picks = []
for game, pfx in cfb_games.items():
    try:
        data = fetch_all(f"{pfx}_draft_picks")
        for r in data:
            r["game"] = game
        all_picks.extend(data)
    except Exception:
        pass
picks_df = pd.DataFrame(all_picks) if all_picks else pd.DataFrame()

all_seasons = []
all_wins = []
for game, pfx in madden_games.items():
    try:
        sdata = fetch_all(f"{pfx}_seasons")
        for r in sdata:
            r["game"] = game
        all_seasons.extend(sdata)
    except Exception:
        pass
    try:
        wdata = fetch_all(f"{pfx}_team_wins")
        for r in wdata:
            r["game"] = game
        all_wins.extend(wdata)
    except Exception:
        pass
seasons_df = pd.DataFrame(all_seasons) if all_seasons else pd.DataFrame()
wins_df = pd.DataFrame(all_wins) if all_wins else pd.DataFrame()

# --- CFB Dynasty ---
st.subheader("CFB Dynasty")

if not picks_df.empty:
    cfb_m1, cfb_m2, cfb_m3, cfb_m4 = st.columns(4)
    cfb_m1.metric("Total Picks", len(picks_df))
    first_rd = picks_df[picks_df["round"] == "1st"]
    cfb_m2.metric("1st Rounders", len(first_rd))
    cfb_m3.metric("Draft Classes", picks_df["year"].nunique())
    top_pos = picks_df["position"].value_counts().idxmax() if "position" in picks_df.columns else "—"
    cfb_m4.metric("Top Position", top_pos)

    cfb_left, cfb_right = st.columns(2)

    with cfb_left:
        st.markdown("**1st Round Picks**")
        if not first_rd.empty:
            display = first_rd[["game", "name", "position", "year", "school"]].rename(
                columns={"game": "Game", "name": "Name", "position": "Pos", "year": "Year", "school": "School"}
            ).sort_values("Year", ascending=False)
            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.caption("No 1st rounders yet.")

    with cfb_right:
        st.markdown("**Picks by Round**")
        by_round = picks_df.groupby("round").size().reset_index(name="count")
        by_round["round"] = pd.Categorical(by_round["round"], categories=ROUND_ORDER, ordered=True)
        by_round = by_round.sort_values("round").dropna(subset=["round"])
        st.bar_chart(by_round.set_index("round")["count"])

        st.markdown("**Picks by Position (Top 10)**")
        by_pos = picks_df["position"].value_counts().head(10)
        st.bar_chart(by_pos)

    with st.expander("Cross-Game Comparison"):
        game_comp = picks_df.groupby("game").agg(
            total=("name", "count"),
            first_round=("round", lambda x: (x == "1st").sum()),
            positions=("position", "nunique"),
            classes=("year", "nunique"),
        ).reset_index().rename(columns={
            "game": "Game", "total": "Total Picks", "first_round": "1st Rounders",
            "positions": "Positions", "classes": "Draft Classes",
        })
        st.dataframe(game_comp, use_container_width=True, hide_index=True)

        st.markdown("**Picks per Game by Round**")
        game_round = picks_df.groupby(["game", "round"]).size().unstack(fill_value=0)
        for r in ROUND_ORDER:
            if r not in game_round.columns:
                game_round[r] = 0
        game_round = game_round[[r for r in ROUND_ORDER if r in game_round.columns]]
        st.dataframe(game_round, use_container_width=True)

        st.markdown("**Top Positions Across All Games**")
        all_pos = picks_df.groupby(["game", "position"]).size().unstack(fill_value=0)
        top_pos_cols = picks_df["position"].value_counts().head(8).index.tolist()
        st.dataframe(
            all_pos[[c for c in top_pos_cols if c in all_pos.columns]],
            use_container_width=True,
        )
else:
    st.info("No CFB draft data loaded.")

st.divider()

# --- Madden Franchise ---
st.subheader("Madden Franchise")

if not seasons_df.empty:
    mad_m1, mad_m2, mad_m3, mad_m4 = st.columns(4)
    mad_m1.metric("Seasons Recorded", len(seasons_df))
    franchises = seasons_df.groupby(["game", "franchise"]).ngroups
    mad_m2.metric("Franchises", franchises)

    sb_counts = seasons_df["sb_winner"].dropna().value_counts()
    if not sb_counts.empty:
        mad_m3.metric("Most SB Wins", f"{sb_counts.index[0]} ({sb_counts.iloc[0]})")
    else:
        mad_m3.metric("Most SB Wins", "—")

    mvp_counts = seasons_df["nfl_mvp"].dropna().value_counts()
    if not mvp_counts.empty:
        mad_m4.metric("Most MVPs", f"{mvp_counts.index[0]} ({mvp_counts.iloc[0]})")
    else:
        mad_m4.metric("Most MVPs", "—")

    mad_left, mad_right = st.columns(2)

    with mad_left:
        st.markdown("**Award Leaders**")
        leaders = []
        for col, label in AWARD_COLS.items():
            if col in seasons_df.columns:
                counts = seasons_df[col].dropna().value_counts()
                if not counts.empty:
                    leaders.append({
                        "Award": label,
                        "Leader": counts.index[0],
                        "Times": counts.iloc[0],
                    })
        if leaders:
            st.dataframe(
                pd.DataFrame(leaders), use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No award data yet.")

    with mad_right:
        st.markdown("**Top Teams by Wins (All-Time)**")
        if not wins_df.empty:
            wins_df["wins"] = pd.to_numeric(wins_df["wins"], errors="coerce")
            top_teams = wins_df.groupby("team")["wins"].sum().sort_values(ascending=False).head(10)
            top_display = top_teams.reset_index()
            top_display["team_name"] = top_display["team"].map(
                lambda t: f"{t} ({NFL_COLORS[t][2]})" if t in NFL_COLORS else t
            )
            st.bar_chart(top_display.set_index("team_name")["wins"])
        else:
            st.caption("No team win data yet.")

    with st.expander("SB Winners by Year"):
        sb_data = seasons_df[seasons_df["sb_winner"].notna()][
            ["game", "franchise", "year", "sb_winner", "sb_mvp"]
        ].sort_values(["game", "year"], ascending=[True, False]).rename(
            columns={
                "game": "Game", "franchise": "Franchise", "year": "Year",
                "sb_winner": "SB Winner", "sb_mvp": "SB MVP",
            }
        )
        if not sb_data.empty:
            st.dataframe(sb_data, use_container_width=True, hide_index=True)
        else:
            st.caption("No SB data.")

    with st.expander("MVP History"):
        mvp_data = seasons_df[seasons_df["nfl_mvp"].notna()][
            ["game", "franchise", "year", "nfl_mvp"]
        ].sort_values(["game", "year"], ascending=[True, False]).rename(
            columns={
                "game": "Game", "franchise": "Franchise", "year": "Year",
                "nfl_mvp": "NFL MVP",
            }
        )
        if not mvp_data.empty:
            st.dataframe(mvp_data, use_container_width=True, hide_index=True)
        else:
            st.caption("No MVP data.")

    with st.expander("Cross-Game Comparison"):
        game_stats = seasons_df.groupby("game").agg(
            seasons=("year", "count"),
            franchises=("franchise", "nunique"),
            sb_winners=("sb_winner", lambda x: x.notna().sum()),
            unique_mvps=("nfl_mvp", "nunique"),
        ).reset_index().rename(columns={
            "game": "Game", "seasons": "Seasons", "franchises": "Franchises",
            "sb_winners": "SB Winners Recorded", "unique_mvps": "Unique MVPs",
        })
        st.dataframe(game_stats, use_container_width=True, hide_index=True)

        st.markdown("**Award Leaders Across All Games**")
        cross_leaders = []
        for col, label in AWARD_COLS.items():
            if col in seasons_df.columns:
                counts = seasons_df[col].dropna().value_counts()
                if not counts.empty:
                    cross_leaders.append({
                        "Award": label,
                        "All-Time Leader": counts.index[0],
                        "Total": counts.iloc[0],
                        "Games Won In": seasons_df[seasons_df[col] == counts.index[0]]["game"].nunique(),
                    })
        if cross_leaders:
            st.dataframe(pd.DataFrame(cross_leaders), use_container_width=True, hide_index=True)

        if not wins_df.empty:
            st.markdown("**Top Teams by Total Wins Across All Games**")
            cross_wins = wins_df.groupby("team").agg(
                total_wins=("wins", "sum"),
                games_in=("game", "nunique"),
                seasons=("year", "nunique"),
            ).sort_values("total_wins", ascending=False).head(15).reset_index()
            cross_wins.columns = ["Team", "Total Wins", "Games", "Seasons"]
            st.dataframe(cross_wins, use_container_width=True, hide_index=True)

            st.markdown("**Average Wins Per Season by Team (min 3 seasons)**")
            team_avg = wins_df.groupby("team").agg(
                total_wins=("wins", "sum"), seasons=("year", "count"),
            )
            team_avg = team_avg[team_avg["seasons"] >= 3]
            team_avg["avg_wins"] = (team_avg["total_wins"] / team_avg["seasons"]).round(1)
            team_avg = team_avg.sort_values("avg_wins", ascending=False).head(10).reset_index()
            team_avg.columns = ["Team", "Total Wins", "Seasons", "Avg Wins"]
            st.dataframe(team_avg, use_container_width=True, hide_index=True)
else:
    st.info("No Madden data loaded.")

st.divider()

# --- Rhymes ---
st.subheader("Rhymes")
try:
    rhyme_data = fetch_all("rhymes")
    if rhyme_data:
        rdf = pd.DataFrame(rhyme_data)
        r1, r2 = st.columns(2)
        r1.metric("Words", len(rdf))
        r2.metric("Groups", rdf["rhyme_group"].nunique())
    else:
        st.info("No rhyme data loaded.")
except Exception:
    st.info("No rhyme data loaded.")
