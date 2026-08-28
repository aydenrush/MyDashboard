import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from db import fetch_all, insert_row, insert_rows, update_row, get_supabase
from auth import require_login
from ui_helpers import delete_button
from constants import ACTIVITY_TYPES

st.set_page_config(page_title="Training", layout="wide")
require_login()

_t1, _t2 = st.columns([6, 1])
_t1.title("Training")
_t2.link_button("Strava", "https://www.strava.com/dashboard")

try:
    data = fetch_all("running_schedule", order_col="date")
except Exception:
    data = []
df = pd.DataFrame(data)

try:
    _act_data = fetch_all("activities", order_col="date")
except Exception:
    _act_data = []
_act_df = pd.DataFrame(_act_data)

today = datetime.now(ZoneInfo("America/Indiana/Indianapolis")).date()
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

        try:
            _today_logs = [r for r in (_rl_data or []) if r.get("date") == today.isoformat()]
        except Exception:
            _today_logs = []
        if _today_logs:
            for _tl in _today_logs:
                _tl_parts = []
                if _tl.get("distance_miles"):
                    _tl_parts.append(f"{float(_tl['distance_miles']):.2f} mi")
                if _tl.get("duration_seconds"):
                    _ds = int(_tl["duration_seconds"])
                    if _ds >= 3600:
                        _tl_parts.append(f"{_ds // 3600}:{(_ds % 3600) // 60:02d}:{_ds % 60:02d}")
                    else:
                        _tl_parts.append(f"{_ds // 60}:{_ds % 60:02d}")
                if _tl.get("pace_seconds"):
                    _pm, _ps = divmod(int(_tl["pace_seconds"]), 60)
                    _tl_parts.append(f"{_pm}:{_ps:02d}/mi")
                if _tl.get("elevation_gain_ft") and float(_tl["elevation_gain_ft"]) > 0:
                    _tl_parts.append(f"↑{int(float(_tl['elevation_gain_ft']))} ft")
                _src = " `GPX`" if _tl.get("source") == "gpx" else ""
                st.caption("Actual: " + " · ".join(_tl_parts) + _src)
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
        show_rest = st.checkbox("Show rest days", value=True)

        display_df = df.copy()
        if not show_rest:
            display_df = display_df[display_df["type"] != "rest"]

        upcoming_df = display_df[display_df["date"] >= today]
        past_df = display_df[display_df["date"] < today].sort_values("date", ascending=False)

        def render_schedule_row(row):
            color = TYPE_COLORS[row["type"]]
            is_today = row["date"] == today
            date_str = row["date"].strftime("%a %m/%d")
            title = row["workout"].split("\n")[0]
            details = "\n".join(row["workout"].split("\n")[1:]).strip()
            done = row["completed"]

            col_date, col_workout, col_action = st.columns([1.5, 6, 1.5])
            with col_date:
                label = f"**{date_str}**" if is_today else date_str
                st.markdown(label)
            with col_workout:
                badge = f'<span style="color:{color}; font-weight:bold; font-size:0.8em;">{TYPE_LABELS[row["type"]].upper()}</span> '
                text = f"~~{title}~~" if done else title
                st.markdown(f'{badge}{text}', unsafe_allow_html=True)
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

        for _, row in upcoming_df.iterrows():
            render_schedule_row(row)

        if not past_df.empty:
            with st.expander(f"Past Workouts ({len(past_df)})"):
                for _, row in past_df.iterrows():
                    render_schedule_row(row)

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

# --- Run Log ---
st.subheader("Run Log")


def _fmt_pace(secs):
    if not secs or secs <= 0:
        return "--"
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}/mi"


def _fmt_duration(secs):
    if not secs or secs <= 0:
        return "--"
    secs = int(secs)
    if secs >= 3600:
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h}:{m:02d}:{s:02d}"
    m = secs // 60
    s = secs % 60
    return f"{m}:{s:02d}"


try:
    _rl_data = fetch_all("run_logs", order_col="date")
except Exception:
    _rl_data = None

if _rl_data is None:
    st.info("Create the `run_logs` table to start logging actual runs:")
    st.code(
        "create table run_logs (\n"
        "    id bigint generated by default as identity primary key,\n"
        "    date date not null,\n"
        "    distance_miles numeric not null,\n"
        "    duration_seconds integer not null,\n"
        "    pace_seconds integer,\n"
        "    elevation_gain_ft numeric,\n"
        "    splits jsonb,\n"
        "    route_name text,\n"
        "    notes text,\n"
        "    source text default 'manual',\n"
        "    created_at timestamptz default now()\n"
        ");",
        language="sql",
    )
else:
    _rl_df = pd.DataFrame(_rl_data)

    if not _rl_df.empty:
        _rl_df["date"] = pd.to_datetime(_rl_df["date"]).dt.date
        _rl_sorted = _rl_df.sort_values("date", ascending=False)

        _rl_wk_start = today - timedelta(days=today.weekday())
        _rl_wk_end = _rl_wk_start + timedelta(days=6)
        _rl_week = _rl_df[(_rl_df["date"] >= _rl_wk_start) & (_rl_df["date"] <= _rl_wk_end)]
        _rl_week_miles = _rl_week["distance_miles"].sum() if not _rl_week.empty else 0
        _rl_total_miles = _rl_df["distance_miles"].sum()
        _rl_best_pace = _rl_df["pace_seconds"].dropna()
        _rl_best_pace = int(_rl_best_pace.min()) if not _rl_best_pace.empty else 0

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("This Week", f"{_rl_week_miles:.1f} mi")
        s2.metric("Total Logged", f"{_rl_total_miles:.1f} mi")
        s3.metric("Best Pace", _fmt_pace(_rl_best_pace))
        s4.metric("Runs Logged", len(_rl_df))

        for _, _run in _rl_sorted.head(5).iterrows():
            _dist = f"{_run['distance_miles']:.2f} mi" if pd.notna(_run.get("distance_miles")) else ""
            _pace = _fmt_pace(_run.get("pace_seconds"))
            _dur = _fmt_duration(_run.get("duration_seconds"))
            _elev = f"↑{int(_run['elevation_gain_ft'])} ft" if pd.notna(_run.get("elevation_gain_ft")) and _run["elevation_gain_ft"] > 0 else ""
            _name = _run.get("route_name") or ""
            _date_str = _run["date"].strftime("%a %m/%d")
            _src = " `GPX`" if _run.get("source") == "gpx" else ""

            _parts = [f"**{_date_str}**", _dist, _dur, _pace]
            if _elev:
                _parts.append(_elev)
            if _name:
                _parts.append(_name)
            st.markdown(" · ".join(_parts) + _src)

            _sp = _run.get("splits")
            if _sp and isinstance(_sp, list) and len(_sp) > 1:
                _sp_strs = []
                for _si, _sv in enumerate(_sp):
                    _lbl = f"Mile {_si + 1}" if _si < len(_sp) - 1 else "Last"
                    _sm, _ss = divmod(int(_sv), 60)
                    _sp_strs.append(f"{_lbl}: {_sm}:{_ss:02d}")
                st.caption(" | ".join(_sp_strs))

            if pd.notna(_run.get("notes")) and str(_run.get("notes", "")).strip():
                st.caption(str(_run["notes"]))

        if len(_rl_sorted) > 5:
            with st.expander(f"All Runs ({len(_rl_sorted)})"):
                for _, _run in _rl_sorted.iloc[5:].iterrows():
                    _dist = f"{_run['distance_miles']:.2f} mi"
                    _pace = _fmt_pace(_run.get("pace_seconds"))
                    _dur = _fmt_duration(_run.get("duration_seconds"))
                    _date_str = _run["date"].strftime("%a %m/%d")
                    _name = _run.get("route_name") or ""
                    _parts = [f"**{_date_str}**", _dist, _dur, _pace]
                    if _name:
                        _parts.append(_name)
                    st.caption(" · ".join(_parts))

    if not _rl_df.empty and len(_rl_df) >= 2:
        with st.expander("Run Analytics"):
            import numpy as np

            _an_df = _rl_df.copy()
            _an_df = _an_df.sort_values("date")

            # --- Weekly Mileage + 10% Rule ---
            st.markdown("**Weekly Mileage**")
            _an_df["week"] = _an_df["date"].apply(lambda d: (d - timedelta(days=d.weekday())).isoformat())
            _wk_miles = _an_df.groupby("week")["distance_miles"].sum().reset_index()
            _wk_miles.columns = ["Week", "Miles"]
            _wk_miles = _wk_miles.sort_values("Week")

            if len(_wk_miles) >= 2:
                _wk_miles["4wk Avg"] = _wk_miles["Miles"].rolling(4, min_periods=1).mean()
                _wk_miles["10% Cap"] = _wk_miles["Miles"].shift(1) * 1.1
                _wk_miles["10% Cap"] = _wk_miles["10% Cap"].fillna(_wk_miles["Miles"].iloc[0])

                _chart_data = _wk_miles.set_index("Week")[["Miles", "4wk Avg", "10% Cap"]]
                st.line_chart(_chart_data)

                _over = _wk_miles[_wk_miles["Miles"] > _wk_miles["10% Cap"]]
                if not _over.empty:
                    st.warning(
                        f"{len(_over)} week(s) exceeded the 10% rule — "
                        f"ramp mileage gradually to avoid injury."
                    )
            else:
                st.bar_chart(_wk_miles.set_index("Week")["Miles"])

            # --- Pace Trend ---
            _pace_df = _an_df[_an_df["pace_seconds"].notna()].copy()
            if len(_pace_df) >= 2:
                st.markdown("**Pace Trend**")
                _pace_chart = _pace_df[["date", "pace_seconds"]].copy()
                _pace_chart["Pace (min/mi)"] = _pace_chart["pace_seconds"] / 60
                _pace_chart["7-Run Avg"] = _pace_chart["Pace (min/mi)"].rolling(7, min_periods=2).mean()
                _pace_chart = _pace_chart.set_index("date")[["Pace (min/mi)", "7-Run Avg"]]
                st.line_chart(_pace_chart)

                _first_5 = _pace_df.head(5)["pace_seconds"].mean()
                _last_5 = _pace_df.tail(5)["pace_seconds"].mean()
                _diff = _first_5 - _last_5
                if _diff > 0:
                    st.caption(f"Pace improved by {_diff:.0f}s/mi (first 5 vs last 5 runs)")
                elif _diff < 0:
                    st.caption(f"Pace slowed by {abs(_diff):.0f}s/mi (first 5 vs last 5 runs)")

            # --- Training Load (Acute:Chronic) ---
            st.markdown("**Training Load**")
            _load_dates = []
            _acwr_vals = []
            _acute_vals = []
            _chronic_vals = []
            _all_dates = sorted(_an_df["date"].unique())
            for _ld in _all_dates:
                _acute_start = _ld - timedelta(days=6)
                _chronic_start = _ld - timedelta(days=27)
                _ac = _an_df[(_an_df["date"] >= _acute_start) & (_an_df["date"] <= _ld)]["distance_miles"].sum()
                _ch = _an_df[(_an_df["date"] >= _chronic_start) & (_an_df["date"] <= _ld)]["distance_miles"].sum() / 4
                _load_dates.append(_ld)
                _acute_vals.append(_ac)
                _chronic_vals.append(round(_ch, 1))
                _acwr_vals.append(round(_ac / _ch, 2) if _ch > 0 else 0)

            _load_df = pd.DataFrame({
                "date": _load_dates,
                "ACWR": _acwr_vals,
            }).set_index("date")

            st.line_chart(_load_df)
            _latest_acwr = _acwr_vals[-1] if _acwr_vals else 0
            if _latest_acwr > 1.5:
                st.error(f"ACWR: {_latest_acwr:.2f} — injury risk zone. Consider dialing back this week.")
            elif _latest_acwr < 0.8:
                st.warning(f"ACWR: {_latest_acwr:.2f} — detraining zone. You can safely add more.")
            else:
                st.success(f"ACWR: {_latest_acwr:.2f} — sweet spot (0.8–1.3 is optimal).")
            st.caption("Acute:Chronic Workload Ratio — 7-day mileage ÷ 28-day weekly avg")

            # --- Effort Zones ---
            if not _pace_df.empty:
                st.markdown("**Effort Zones**")
                _all_paces = _pace_df["pace_seconds"].dropna()
                _median_pace = _all_paces.median()

                def _effort_zone(p):
                    if p <= _median_pace * 0.85:
                        return "Speed"
                    elif p <= _median_pace * 0.93:
                        return "Tempo"
                    elif p <= _median_pace * 1.05:
                        return "Moderate"
                    else:
                        return "Easy"

                _pace_df["zone"] = _pace_df["pace_seconds"].apply(_effort_zone)
                _zone_counts = _pace_df["zone"].value_counts()
                _zone_order = ["Easy", "Moderate", "Tempo", "Speed"]
                _zone_counts = _zone_counts.reindex(_zone_order).dropna().astype(int)

                st.bar_chart(_zone_counts)

                _easy_pct = _zone_counts.get("Easy", 0) / len(_pace_df) * 100 if len(_pace_df) > 0 else 0
                if _easy_pct < 70:
                    st.caption(
                        f"Easy runs: {_easy_pct:.0f}% — aim for ~80% easy to avoid overtraining"
                    )
                else:
                    st.caption(f"Easy runs: {_easy_pct:.0f}% — good balance")

            # --- Split Analysis ---
            _split_runs = _an_df[_an_df["splits"].apply(lambda x: isinstance(x, list) and len(x) > 1)]
            if not _split_runs.empty:
                st.markdown("**Split Analysis**")
                _neg_splits = 0
                _pos_splits = 0
                _even_splits = 0
                _fastest_mile = None
                _fastest_mile_run = None
                _consistencies = []

                for _, _sr in _split_runs.iterrows():
                    sp = _sr["splits"]
                    full_miles = sp[:-1] if len(sp) > 1 else sp
                    if not full_miles:
                        continue

                    first_half = full_miles[:len(full_miles) // 2]
                    second_half = full_miles[len(full_miles) // 2:]
                    if first_half and second_half:
                        avg_first = sum(first_half) / len(first_half)
                        avg_second = sum(second_half) / len(second_half)
                        if avg_second < avg_first * 0.98:
                            _neg_splits += 1
                        elif avg_second > avg_first * 1.02:
                            _pos_splits += 1
                        else:
                            _even_splits += 1

                    _std = np.std(full_miles)
                    _consistencies.append(round(_std, 1))

                    _min_split = min(full_miles)
                    if _fastest_mile is None or _min_split < _fastest_mile:
                        _fastest_mile = _min_split
                        _fastest_mile_run = _sr["date"]

                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Negative Splits", _neg_splits)
                sc2.metric("Even Splits", _even_splits)
                sc3.metric("Positive Splits", _pos_splits)

                if _fastest_mile:
                    _fm, _fs = divmod(int(_fastest_mile), 60)
                    st.caption(
                        f"Fastest mile: {_fm}:{_fs:02d} on "
                        f"{_fastest_mile_run.strftime('%b %d')}"
                    )

                if _consistencies:
                    _avg_cons = sum(_consistencies) / len(_consistencies)
                    if _avg_cons < 10:
                        st.caption(f"Avg split consistency: ±{_avg_cons:.0f}s — very even pacing")
                    elif _avg_cons < 20:
                        st.caption(f"Avg split consistency: ±{_avg_cons:.0f}s — solid pacing")
                    else:
                        st.caption(f"Avg split consistency: ±{_avg_cons:.0f}s — pacing could be more even")

            # --- Route Comparison ---
            _named = _an_df[_an_df["route_name"].notna() & (_an_df["route_name"] != "")]
            if not _named.empty:
                _route_counts = _named["route_name"].value_counts()
                _repeat_routes = _route_counts[_route_counts > 1]
                if not _repeat_routes.empty:
                    st.markdown("**Route Comparison**")
                    for _rname in _repeat_routes.index[:5]:
                        _rr = _named[_named["route_name"] == _rname].sort_values("date")
                        st.markdown(f"*{_rname}* ({len(_rr)} runs)")
                        _rc_data = _rr[["date", "pace_seconds"]].copy()
                        _rc_data["Pace (min/mi)"] = _rc_data["pace_seconds"] / 60
                        _rc_data = _rc_data.set_index("date")["Pace (min/mi)"]
                        st.line_chart(_rc_data)

                        _first_pace = _rr.iloc[0]["pace_seconds"]
                        _last_pace = _rr.iloc[-1]["pace_seconds"]
                        if _first_pace and _last_pace:
                            _imp = _first_pace - _last_pace
                            if _imp > 0:
                                st.caption(f"Improved {_imp:.0f}s/mi from first to latest")
                            elif _imp < 0:
                                st.caption(f"Slowed {abs(_imp):.0f}s/mi from first to latest")

            # --- Personal Records ---
            st.markdown("**Personal Records**")
            _pr_data = []

            _best_mile = None
            for _, _sr in _an_df.iterrows():
                sp = _sr.get("splits")
                if sp and isinstance(sp, list):
                    full_miles = sp[:-1] if len(sp) > 1 else sp
                    if full_miles:
                        _bm = min(full_miles)
                        if _best_mile is None or _bm < _best_mile[0]:
                            _best_mile = (_bm, _sr["date"])

            if _best_mile:
                _m, _s = divmod(int(_best_mile[0]), 60)
                _pr_data.append(("Fastest Mile", f"{_m}:{_s:02d}", _best_mile[1].strftime("%b %d")))

            _longest = _an_df.loc[_an_df["distance_miles"].idxmax()]
            _pr_data.append(("Longest Run", f"{_longest['distance_miles']:.2f} mi", _longest["date"].strftime("%b %d")))

            _fastest_run = _pace_df.loc[_pace_df["pace_seconds"].idxmin()] if not _pace_df.empty else None
            if _fastest_run is not None:
                _pr_data.append(("Fastest Pace", _fmt_pace(_fastest_run["pace_seconds"]), _fastest_run["date"].strftime("%b %d")))

            _most_elev = _an_df[_an_df["elevation_gain_ft"].notna()]
            if not _most_elev.empty:
                _me = _most_elev.loc[_most_elev["elevation_gain_ft"].idxmax()]
                if _me["elevation_gain_ft"] > 0:
                    _pr_data.append(("Most Elevation", f"↑{int(_me['elevation_gain_ft'])} ft", _me["date"].strftime("%b %d")))

            if _pr_data:
                _pr_cols = st.columns(len(_pr_data))
                for _ci, (_lbl, _val, _dt) in enumerate(_pr_data):
                    _pr_cols[_ci].metric(_lbl, _val, _dt)

    def _parse_gpx(file_bytes):
        import gpxpy as _gpxpy

        _gpx = _gpxpy.parse(file_bytes)
        _pts = []
        for _trk in _gpx.tracks:
            for _seg in _trk.segments:
                _pts.extend(_seg.points)

        if not _pts:
            return None

        _total_dist = _gpx.length_3d() or _gpx.length_2d() or 0
        _dist_mi = _total_dist / 1609.344

        _t0, _t1 = _pts[0].time, _pts[-1].time
        _dur_s = int((_t1 - _t0).total_seconds()) if _t0 and _t1 else 0

        _up, _ = _gpx.get_uphill_downhill()
        _elev_ft = round((_up or 0) * 3.28084)
        _pace_s = int(_dur_s / _dist_mi) if _dist_mi > 0 else 0

        _splits = []
        if _t0:
            _cum = 0
            _last_t = _t0
            _prev = _pts[0]
            _mile = 1
            for _pt in _pts[1:]:
                _d = (
                    _prev.distance_3d(_pt)
                    if _prev.elevation is not None and _pt.elevation is not None
                    else _prev.distance_2d(_pt)
                )
                _cum += _d or 0
                if _cum >= _mile * 1609.344 and _pt.time:
                    _splits.append(int((_pt.time - _last_t).total_seconds()))
                    _last_t = _pt.time
                    _mile += 1
                _prev = _pt
            _rem = _cum - (_mile - 1) * 1609.344
            if _rem > 160 and _pts[-1].time and _last_t:
                _splits.append(int((_pts[-1].time - _last_t).total_seconds()))

        _route = None
        if _gpx.tracks:
            _route = _gpx.tracks[0].name
        if not _route:
            _route = _gpx.name

        _gpx_date = _t0.date() if _t0 else today

        return {
            "date": _gpx_date,
            "distance_miles": round(_dist_mi, 2),
            "duration_seconds": _dur_s,
            "pace_seconds": _pace_s,
            "elevation_gain_ft": _elev_ft,
            "splits": _splits if _splits else None,
            "route_name": _route,
        }

    with st.expander("Log a Run"):
        _log_gpx, _log_manual, _log_bulk = st.tabs(["Upload GPX", "Manual Entry", "Bulk Import"])

        with _log_gpx:
            gpx_file = st.file_uploader("Upload .gpx file from Strava", type=["gpx"], key="single_gpx")
            if gpx_file is not None:
                try:
                    parsed = _parse_gpx(gpx_file.read())
                    if parsed is None:
                        st.error("No GPS points found in file.")
                    else:
                        st.success(
                            f"Parsed: {parsed['distance_miles']:.2f} mi · "
                            f"{_fmt_duration(parsed['duration_seconds'])} · "
                            f"{_fmt_pace(parsed['pace_seconds'])} · "
                            f"↑{parsed['elevation_gain_ft']} ft"
                        )

                        if parsed["splits"]:
                            _sp_strs = []
                            for _si, _sv in enumerate(parsed["splits"]):
                                _lbl = f"Mile {_si + 1}" if _si < len(parsed["splits"]) - 1 else "Last"
                                _sm, _ss = divmod(_sv, 60)
                                _sp_strs.append(f"{_lbl}: {_sm}:{_ss:02d}")
                            st.caption(" | ".join(_sp_strs))

                        _gpx_notes = st.text_input("Notes (optional)", key="gpx_notes")

                        if st.button("Save Run", key="save_gpx"):
                            insert_row("run_logs", {
                                "date": parsed["date"].isoformat(),
                                "distance_miles": parsed["distance_miles"],
                                "duration_seconds": parsed["duration_seconds"],
                                "pace_seconds": parsed["pace_seconds"],
                                "elevation_gain_ft": parsed["elevation_gain_ft"],
                                "splits": parsed["splits"],
                                "route_name": parsed["route_name"],
                                "notes": _gpx_notes.strip() or None,
                                "source": "gpx",
                            })
                            if _has_data:
                                _sched = df[df["date"] == parsed["date"]]
                                for _, _sr in _sched.iterrows():
                                    if not _sr["completed"]:
                                        update_row("running_schedule", int(_sr["id"]), {"completed": True})
                            st.success("Run saved!")
                            st.rerun()
                except ImportError:
                    st.error("Install gpxpy: `pip install gpxpy`")
                except Exception as e:
                    st.error(f"Error parsing GPX: {e}")

        with _log_bulk:
            st.caption(
                "Import from a Strava archive: Settings > My Account > "
                "Request Your Archive. Upload the **activities.csv** from the ZIP, "
                "or drop multiple **.gpx** files."
            )
            _bulk_fmt = st.radio(
                "Format", ["Strava CSV", "GPX Files"], horizontal=True,
                label_visibility="collapsed", key="bulk_fmt",
            )

            if _bulk_fmt == "Strava CSV":
                _csv_file = st.file_uploader(
                    "Upload activities.csv", type=["csv"], key="strava_csv",
                )
                if _csv_file is not None:
                    import csv
                    import io

                    _text = _csv_file.read().decode("utf-8")
                    _reader = csv.DictReader(io.StringIO(_text))
                    _all_rows = list(_reader)
                    _runs = [r for r in _all_rows if r.get("Activity Type") == "Run"]

                    _existing_dates = set()
                    if not _rl_df.empty:
                        _existing_dates = set(_rl_df["date"].apply(lambda d: d.isoformat()).tolist())

                    _csv_parsed = []
                    _csv_skipped = 0
                    _csv_errors = 0
                    for _cr in _runs:
                        try:
                            _raw_date = _cr.get("Activity Date", "")
                            _dt = datetime.strptime(_raw_date, "%b %d, %Y, %I:%M:%S %p")
                            _d_iso = _dt.date().isoformat()

                            _dist_m = float(_cr.get("Distance") or 0)
                            _time_s = float(_cr.get("Moving Time") or 0)
                            if _dist_m <= 0:
                                _csv_errors += 1
                                continue

                            _dist_mi = round(_dist_m / 1609.344, 2)
                            _elev_m = float(_cr.get("Elevation Gain") or 0)
                            _elev_ft = round(_elev_m * 3.28084)
                            _pace = int(_time_s / _dist_mi) if _dist_mi > 0 and _time_s > 0 else None
                            _name = _cr.get("Activity Name") or None
                            _desc = _cr.get("Activity Description") or None
                            _notes = _desc.strip() if _desc and _desc.strip() else None

                            if _d_iso in _existing_dates:
                                _csv_skipped += 1
                                continue

                            _csv_parsed.append({
                                "date": _d_iso,
                                "distance_miles": _dist_mi,
                                "duration_seconds": int(_time_s) if _time_s > 0 else None,
                                "pace_seconds": _pace,
                                "elevation_gain_ft": _elev_ft if _elev_ft > 0 else None,
                                "route_name": _name,
                                "notes": _notes,
                                "source": "strava",
                            })
                        except Exception:
                            _csv_errors += 1

                    st.markdown(
                        f"**{len(_csv_parsed)} new runs** from {len(_runs)} total "
                        f"({_csv_skipped} already logged"
                        f"{f', {_csv_errors} errors' if _csv_errors else ''})"
                    )

                    if _csv_parsed:
                        _by_year = {}
                        for _cr in _csv_parsed:
                            _yr = _cr["date"][:4]
                            _by_year.setdefault(_yr, []).append(_cr)
                        for _yr in sorted(_by_year, reverse=True):
                            _yr_runs = _by_year[_yr]
                            _yr_miles = sum(r["distance_miles"] for r in _yr_runs)
                            st.markdown(f"**{_yr}** — {len(_yr_runs)} runs, {_yr_miles:.0f} mi")
                            for _cr in sorted(_yr_runs, key=lambda r: r["date"], reverse=True)[:3]:
                                _cd = date.fromisoformat(_cr["date"])
                                st.caption(
                                    f"  {_cd.strftime('%b %d')} — "
                                    f"{_cr['distance_miles']:.2f} mi · "
                                    f"{_fmt_duration(_cr['duration_seconds'])} · "
                                    f"{_fmt_pace(_cr['pace_seconds'])}"
                                    f"{' · ' + _cr['route_name'] if _cr.get('route_name') else ''}"
                                )
                            if len(_yr_runs) > 3:
                                st.caption(f"  ... +{len(_yr_runs) - 3} more")

                        if st.button(f"Import {len(_csv_parsed)} runs", key="csv_import"):
                            insert_rows("run_logs", _csv_parsed)
                            st.success(f"Imported {len(_csv_parsed)} runs!")
                            st.rerun()

            else:
                bulk_files = st.file_uploader(
                    "Upload .gpx files", type=["gpx"], accept_multiple_files=True, key="bulk_gpx",
                )
                if bulk_files:
                    _existing_dates = set()
                    if not _rl_df.empty:
                        _existing_dates = set(_rl_df["date"].apply(lambda d: d.isoformat()).tolist())

                    _previews = []
                    _errors = []
                    for _bf in bulk_files:
                        try:
                            parsed = _parse_gpx(_bf.read())
                            if parsed:
                                _skip = parsed["date"].isoformat() in _existing_dates
                                _previews.append((parsed, _bf.name, _skip))
                            else:
                                _errors.append(f"{_bf.name}: no GPS data")
                        except Exception as e:
                            _errors.append(f"{_bf.name}: {e}")

                    _new = [p for p in _previews if not p[2]]
                    _dupes = [p for p in _previews if p[2]]

                    if _new:
                        st.markdown(f"**{len(_new)} new runs to import:**")
                        for parsed, fname, _ in _new:
                            st.caption(
                                f"{parsed['date'].strftime('%a %m/%d')} — "
                                f"{parsed['distance_miles']:.2f} mi · "
                                f"{_fmt_duration(parsed['duration_seconds'])} · "
                                f"{_fmt_pace(parsed['pace_seconds'])}"
                            )
                    if _dupes:
                        st.caption(f"{len(_dupes)} already logged (skipping)")
                    for _e in _errors:
                        st.caption(f"Error: {_e}")

                    if _new and st.button(f"Import {len(_new)} runs", key="bulk_import"):
                        _imported = 0
                        for parsed, fname, _ in _new:
                            insert_row("run_logs", {
                                "date": parsed["date"].isoformat(),
                                "distance_miles": parsed["distance_miles"],
                                "duration_seconds": parsed["duration_seconds"],
                                "pace_seconds": parsed["pace_seconds"],
                                "elevation_gain_ft": parsed["elevation_gain_ft"],
                                "splits": parsed["splits"],
                                "route_name": parsed["route_name"],
                                "source": "gpx",
                            })
                            if _has_data:
                                _sched = df[df["date"] == parsed["date"]]
                                for _, _sr in _sched.iterrows():
                                    if not _sr["completed"]:
                                        update_row("running_schedule", int(_sr["id"]), {"completed": True})
                            _imported += 1
                        st.success(f"Imported {_imported} runs!")
                        st.rerun()

        with _log_manual:
            with st.form("manual_run", clear_on_submit=True):
                mr1, mr2 = st.columns(2)
                mr_date = mr1.date_input("Date", value=today, key="mr_date")
                mr_name = mr2.text_input("Route Name", key="mr_name", placeholder="e.g., Campus Loop")

                mr3, mr4, mr5 = st.columns(3)
                mr_dist = mr3.number_input(
                    "Distance (miles)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="mr_dist",
                )
                mr_mins = mr4.number_input("Minutes", min_value=0, max_value=600, value=0, key="mr_mins")
                mr_secs = mr5.number_input("Seconds", min_value=0, max_value=59, value=0, key="mr_secs")

                mr6, mr7 = st.columns(2)
                mr_elev = mr6.number_input(
                    "Elevation Gain (ft)", min_value=0, max_value=20000, value=0, key="mr_elev",
                )
                mr_notes = mr7.text_input("Notes", key="mr_notes", placeholder="How did it feel?")

                if st.form_submit_button("Log Run"):
                    if mr_dist > 0:
                        _total_secs = mr_mins * 60 + mr_secs
                        _mr_pace = int(_total_secs / mr_dist) if _total_secs > 0 else None
                        insert_row("run_logs", {
                            "date": mr_date.isoformat(),
                            "distance_miles": round(mr_dist, 2),
                            "duration_seconds": _total_secs if _total_secs > 0 else None,
                            "pace_seconds": _mr_pace,
                            "elevation_gain_ft": mr_elev if mr_elev > 0 else None,
                            "route_name": mr_name.strip() or None,
                            "notes": mr_notes.strip() or None,
                            "source": "manual",
                        })
                        if _has_data:
                            _sched = df[df["date"] == mr_date]
                            for _, _sr in _sched.iterrows():
                                if not _sr["completed"]:
                                    update_row("running_schedule", int(_sr["id"]), {"completed": True})
                        st.success("Run logged!")
                        st.rerun()
                    else:
                        st.error("Distance is required.")

    if not _rl_df.empty:
        with st.expander("Delete Run Logs"):
            for _, _run in _rl_df.sort_values("date", ascending=False).iterrows():
                _dist = f"{_run['distance_miles']:.2f} mi"
                _date_str = _run["date"].strftime("%m/%d")
                _name = _run.get("route_name") or ""
                _label = f"{_date_str} — {_dist}"
                if _name:
                    _label += f" · {_name}"
                delete_button("run_logs", _run["id"], _label, "rl")

st.divider()

# --- Training Plan ---
with st.expander("Training Plan"):
    _tp_start = today - timedelta(days=today.weekday())
    _tp_end = _tp_start + timedelta(days=6)
    _tp_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    _tp_runs = df[(df["date"] >= _tp_start) & (df["date"] <= _tp_end)] if _has_data else pd.DataFrame()

    _tp_cols = st.columns(7)
    for _ti, _tc in enumerate(_tp_cols):
        _td = _tp_start + timedelta(days=_ti)
        _td_str = _td.isoformat()
        with _tc:
            _bold = "**" if _td == today else ""
            st.caption(f"{_bold}{_tp_labels[_ti]}{_bold} {_td.strftime('%m/%d')}")
            _found = False

            if not _tp_runs.empty:
                _tr = _tp_runs[_tp_runs["date"] == _td]
                if not _tr.empty:
                    _found = True
                    _r = _tr.iloc[0]
                    _clr = TYPE_COLORS[_r["type"]]
                    _ttl = _r["workout"].split("\n")[0]
                    _txt = f"~~{_ttl}~~" if _r["completed"] else _ttl
                    st.markdown(
                        f'<span style="color:{_clr};font-size:0.85em;">{_txt}</span>',
                        unsafe_allow_html=True,
                    )

            if not _act_df.empty:
                _ta = _act_df[_act_df["date"] == _td_str]
                for _, _a in _ta.iterrows():
                    if _a["activity_type"] == "running":
                        continue
                    _found = True
                    _at = ACTIVITY_TYPES.get(_a["activity_type"], ACTIVITY_TYPES["other"])
                    _lbl, _clr = _at
                    _done = _a.get("completed", False)
                    _raw = _a.get("title")
                    _ttl = _raw if isinstance(_raw, str) and _raw.strip() else _lbl
                    _txt = f"~~{_ttl}~~" if _done else _ttl
                    st.markdown(
                        f'<span style="color:{_clr};font-size:0.85em;">{_txt}</span>',
                        unsafe_allow_html=True,
                    )

            if not _found:
                st.caption("--")

    st.divider()
    st.markdown("**Quick Add**")
    _qa_date = st.date_input("Date", value=today, key="qa_train_date")
    _PRESETS = {
        "lifting": ["Upper Body", "Lower Body", "Full Body"],
        "cycling": ["Easy Ride", "Long Ride"],
        "frisbee_golf": ["Round"],
    }
    for _qt, _qps in _PRESETS.items():
        _ql, _qc = ACTIVITY_TYPES[_qt]
        st.markdown(
            f'<span style="color:{_qc};font-weight:bold;font-size:0.9em;">{_ql}</span>',
            unsafe_allow_html=True,
        )
        _qcols = st.columns(len(_qps))
        for _qi, _qp in enumerate(_qps):
            if _qcols[_qi].button(_qp, key=f"qa_{_qt}_{_qp}"):
                insert_row("activities", {
                    "date": _qa_date.isoformat(),
                    "activity_type": _qt,
                    "title": _qp,
                    "completed": False,
                })
                st.rerun()

with st.expander("Add Running Schedule"):
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

if _has_data:
    st.divider()
    with st.expander("Delete Workouts"):
        for _, row in df.iterrows():
            title = row["workout"].split("\n")[0]
            delete_button(
                "running_schedule", row["id"],
                f"{row['date'].strftime('%m/%d')} — {title}",
                "run",
            )
