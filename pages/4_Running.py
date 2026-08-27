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

st.title("Training")

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

            if _run.get("notes"):
                st.caption(_run["notes"])

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

    with st.expander("Log a Run"):
        _log_gpx, _log_manual = st.tabs(["Upload GPX", "Manual Entry"])

        with _log_gpx:
            gpx_file = st.file_uploader("Upload .gpx file from Strava", type=["gpx"])
            if gpx_file is not None:
                try:
                    import gpxpy as _gpxpy

                    _gpx = _gpxpy.parse(gpx_file.read())
                    _pts = []
                    for _trk in _gpx.tracks:
                        for _seg in _trk.segments:
                            _pts.extend(_seg.points)

                    if not _pts:
                        st.error("No GPS points found in file.")
                    else:
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

                        st.success(
                            f"Parsed: {_dist_mi:.2f} mi · {_fmt_duration(_dur_s)} · "
                            f"{_fmt_pace(_pace_s)} · ↑{_elev_ft} ft"
                        )

                        if _splits:
                            _sp_strs = []
                            for _si, _sv in enumerate(_splits):
                                _lbl = f"Mile {_si + 1}" if _si < len(_splits) - 1 else "Last"
                                _sm, _ss = divmod(_sv, 60)
                                _sp_strs.append(f"{_lbl}: {_sm}:{_ss:02d}")
                            st.caption(" | ".join(_sp_strs))

                        _gpx_notes = st.text_input("Notes (optional)", key="gpx_notes")

                        if st.button("Save Run", key="save_gpx"):
                            insert_row("run_logs", {
                                "date": _gpx_date.isoformat(),
                                "distance_miles": round(_dist_mi, 2),
                                "duration_seconds": _dur_s,
                                "pace_seconds": _pace_s,
                                "elevation_gain_ft": _elev_ft,
                                "splits": _splits if _splits else None,
                                "route_name": _route,
                                "notes": _gpx_notes.strip() or None,
                                "source": "gpx",
                            })
                            st.success("Run saved!")
                            st.rerun()
                except ImportError:
                    st.error("Install gpxpy: `pip install gpxpy`")
                except Exception as e:
                    st.error(f"Error parsing GPX: {e}")

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
