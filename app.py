import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db import fetch_all, get_supabase
from auth import require_login

st.set_page_config(page_title="My Dashboard", layout="wide")
require_login()

st.title("Dashboard")

today = date.today()

# --- Today's Workout ---
try:
    schedule = fetch_all("running_schedule", order_col="date")
    sched_df = pd.DataFrame(schedule)
    if not sched_df.empty:
        sched_df["date"] = pd.to_datetime(sched_df["date"]).dt.date
except Exception:
    sched_df = pd.DataFrame()

run_col, stats_col = st.columns([3, 2])

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
                    get_supabase().table("running_schedule").update(
                        {"completed": True}
                    ).eq("id", row["id"]).execute()
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

with stats_col:
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
                    if d == today:
                        label = f"**{day_names[i]}**"
                    else:
                        label = day_names[i]
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
    else:
        st.caption("No data.")

st.divider()

# --- Quick Stats ---
st.subheader("Quick Stats")

cfb_col, madden_col, rhyme_col = st.columns(3)

with cfb_col:
    st.markdown("**CFB Dynasty**")
    games = {"CFB 25": "cfb25_draft_picks", "CFB 26": "cfb26_draft_picks", "CFB 27": "cfb27_draft_picks"}
    total_picks = 0
    first_rounders = 0
    for game, table in games.items():
        try:
            data = fetch_all(table)
            if data:
                total_picks += len(data)
                first_rounders += sum(1 for r in data if r.get("round") == "1st")
        except Exception:
            pass
    st.metric("Total Draft Picks", total_picks)
    st.metric("1st Rounders", first_rounders)

with madden_col:
    st.markdown("**Madden Franchise**")
    prefixes = {"Madden 24": "m24", "Madden 25": "m25", "Madden 26": "m26"}
    total_seasons = 0
    total_franchises = set()
    for game, pfx in prefixes.items():
        try:
            data = fetch_all(f"{pfx}_seasons")
            if data:
                total_seasons += len(data)
                for r in data:
                    total_franchises.add(f"{pfx}_{r.get('franchise', '')}")
        except Exception:
            pass
    st.metric("Seasons Recorded", total_seasons)
    st.metric("Franchises", len(total_franchises))

with rhyme_col:
    st.markdown("**Rhymes**")
    try:
        rhyme_data = fetch_all("rhymes")
        if rhyme_data:
            rdf = pd.DataFrame(rhyme_data)
            st.metric("Words", len(rdf))
            st.metric("Groups", rdf["rhyme_group"].nunique())
        else:
            st.metric("Words", 0)
            st.metric("Groups", 0)
    except Exception:
        st.metric("Words", 0)
        st.metric("Groups", 0)
