import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db import fetch_all, insert_rows, update_row, get_supabase
from auth import require_login
from ui_helpers import delete_button

st.set_page_config(page_title="Running Schedule", layout="wide")
require_login()

st.title("Running Schedule")

try:
    data = fetch_all("running_schedule", order_col="date")
except Exception:
    data = []
df = pd.DataFrame(data)

today = date.today()
_has_data = not df.empty

if not _has_data:
    st.info("No schedule loaded yet. Add workouts below.")

if _has_data:
    df["date"] = pd.to_datetime(df["date"]).dt.date


def workout_type(text):
    t = text.split("\n")[0].strip()
    if t == "Rest Day":
        return "rest"
    if "Rest" in t or "Cross" in t:
        return "rest"
    if "Tempo" in t or "tempo" in t:
        return "tempo"
    if "Hill" in t or "hill" in t:
        return "hills"
    if "Fartlek" in t or "Speed" in t or "Repeat" in t or "Interval" in t:
        return "speed"
    if "Long" in t or "Aerobic" in t:
        return "long"
    return "easy"


TYPE_COLORS = {
    "rest": "#888888",
    "easy": "#4CAF50",
    "tempo": "#FF9800",
    "hills": "#9C27B0",
    "speed": "#F44336",
    "long": "#2196F3",
}

TYPE_LABELS = {
    "rest": "Rest",
    "easy": "Easy",
    "tempo": "Tempo",
    "hills": "Hills",
    "speed": "Speed",
    "long": "Long Run",
}

if _has_data:
    df["type"] = df["workout"].apply(workout_type)

    # --- Auto-complete past rest days ---
    past_rest = df[(df["date"] <= today) & (df["type"] == "rest") & (~df["completed"])]
    if not past_rest.empty:
        for _, r in past_rest.iterrows():
            update_row("running_schedule", int(r["id"]), {"completed": True})
        df.loc[past_rest.index, "completed"] = True

    # --- Today's Workout ---
    today_row = df[df["date"] == today]
    if not today_row.empty:
        row = today_row.iloc[0]
        wtype = row["type"]
        color = TYPE_COLORS[wtype]
        st.markdown(
            f'<div style="border-left: 5px solid {color}; padding: 12px 16px; '
            f'border-radius: 4px; margin-bottom: 16px;">'
            f'<span style="color: {color}; font-weight: bold; font-size: 0.85em;">'
            f'{TYPE_LABELS[wtype].upper()}</span>'
            f'<h3 style="margin: 4px 0;">Today\'s Workout</h3>'
            f'<p style="white-space: pre-line; margin: 0;">{row["workout"]}</p></div>',
            unsafe_allow_html=True,
        )
        if not row["completed"]:
            if st.button("Mark Complete"):
                update_row("running_schedule", int(row["id"]), {"completed": True})
                st.rerun()
        else:
            st.success("Completed!")
    else:
        st.info("No workout scheduled for today.")

    st.divider()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_df = df[(df["date"] >= week_start) & (df["date"] <= week_end)]

    st.subheader("This Week")
    if week_df.empty:
        st.info("No workouts scheduled this week.")
    else:
        cols = st.columns(7)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, col in enumerate(cols):
            day = week_start + timedelta(days=i)
            day_row = week_df[week_df["date"] == day]
            with col:
                st.caption(f"**{day_names[i]}** {day.strftime('%m/%d')}")
                if not day_row.empty:
                    r = day_row.iloc[0]
                    color = TYPE_COLORS[r["type"]]
                    title = r["workout"].split("\n")[0]
                    if day == today:
                        st.markdown(
                            f'<span style="color:{color}; font-weight:bold;">'
                            f'{"~~" + title + "~~" if r["completed"] else title}'
                            f'</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'<span style="color:{color};">{title}</span>',
                            unsafe_allow_html=True,
                        )
                    if r["completed"]:
                        st.caption("Done")
                else:
                    st.caption("--")

    st.divider()

    view_tab, progress_tab = st.tabs(["Full Schedule", "Progress"])

    with view_tab:
        show_completed = st.checkbox("Show completed only", value=False)
        show_rest = st.checkbox("Show rest days", value=True)

        display_df = df.copy()
        if show_completed:
            display_df = display_df[display_df["completed"]]
        if not show_rest:
            display_df = display_df[display_df["type"] != "rest"]

        for _, row in display_df.iterrows():
            color = TYPE_COLORS[row["type"]]
            is_past = row["date"] < today
            is_today = row["date"] == today
            opacity = "0.5" if is_past and not is_today else "1.0"

            date_str = row["date"].strftime("%a %m/%d")
            title = row["workout"].split("\n")[0]
            details = "\n".join(row["workout"].split("\n")[1:]).strip()
            done = row["completed"]

            col_date, col_workout, col_action = st.columns([1.5, 6, 1.5])
            with col_date:
                label = f"**{date_str}**" if is_today else date_str
                st.markdown(
                    f'<span style="opacity:{opacity};">{label}</span>',
                    unsafe_allow_html=True,
                )
            with col_workout:
                badge = f'<span style="color:{color}; font-weight:bold; font-size:0.8em;">{TYPE_LABELS[row["type"]].upper()}</span> '
                text = f"~~{title}~~" if done else title
                st.markdown(
                    f'<span style="opacity:{opacity};">{badge}{text}</span>',
                    unsafe_allow_html=True,
                )
                if details and not done:
                    with st.expander("Details"):
                        st.markdown(details)
            with col_action:
                if not done and row["type"] != "rest":
                    if st.button("Done", key=f"done_{row['id']}"):
                        update_row("running_schedule", int(row["id"]), {"completed": True})
                        st.rerun()
                elif done:
                    st.caption("Done")

        with st.expander("Delete Workouts"):
            for _, row in display_df.iterrows():
                title = row["workout"].split("\n")[0]
                delete_button(
                    "running_schedule", row["id"],
                    f"{row['date'].strftime('%m/%d')} — {title}",
                    "run",
                )

        st.divider()
        export_df = df[["date", "workout", "type", "completed"]].copy()
        export_df.columns = ["Date", "Workout", "Type", "Completed"]
        st.download_button(
            "Download Schedule CSV",
            export_df.to_csv(index=False),
            "running_schedule.csv",
            "text/csv",
        )

    with progress_tab:
        total_workouts = len(df[df["type"] != "rest"])
        completed_workouts = len(df[(df["type"] != "rest") & (df["completed"])])
        remaining = total_workouts - completed_workouts

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Workouts", total_workouts)
        col2.metric("Completed", completed_workouts)
        col3.metric("Remaining", remaining)
        if total_workouts > 0:
            col4.metric("Progress", f"{completed_workouts / total_workouts * 100:.0f}%")

        st.progress(completed_workouts / total_workouts if total_workouts > 0 else 0)

        st.subheader("By Workout Type")
        type_summary = (
            df[df["type"] != "rest"]
            .groupby("type")
            .agg(total=("id", "count"), done=("completed", "sum"))
            .reset_index()
        )
        type_summary["type_label"] = type_summary["type"].map(TYPE_LABELS)
        type_summary["remaining"] = type_summary["total"] - type_summary["done"]
        st.dataframe(
            type_summary[["type_label", "total", "done", "remaining"]].rename(
                columns={
                    "type_label": "Type",
                    "total": "Total",
                    "done": "Done",
                    "remaining": "Remaining",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

with st.expander("Add to Schedule"):
    st.markdown("Paste tab-separated rows: `Date` and `Workout`")
    st.code("2026-08-17\tEasy Run - 30 min\n2026-08-18\tRest Day")
    paste_text = st.text_area("Paste rows here", height=150, key="paste_schedule")
    replace_existing = st.checkbox(
        "Replace existing schedule (deletes all current data)", value=False,
    )
    if st.button("Upload", key="upload_schedule"):
        if not paste_text.strip():
            st.error("Nothing to upload.")
        else:
            rows = []
            errors = []
            for line in paste_text.strip().split("\n"):
                parts = line.split("\t", 1)
                if len(parts) < 2:
                    parts = line.split(None, 1)
                if len(parts) < 2:
                    errors.append(f"Bad line: {line}")
                    continue
                date_str = parts[0].strip()
                workout = parts[1].strip().replace("•", "\n-")
                try:
                    pd.to_datetime(date_str)
                except Exception:
                    errors.append(f"Bad date: {date_str}")
                    continue
                rows.append({
                    "date": date_str,
                    "workout": workout or "Rest Day",
                    "completed": False,
                })
            for e in errors:
                st.error(e)
            if rows:
                if replace_existing:
                    get_supabase().table("running_schedule").delete().neq("id", 0).execute()
                insert_rows("running_schedule", rows)
                st.success(f"Uploaded {len(rows)} days.")
                st.rerun()
