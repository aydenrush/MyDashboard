import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import urllib.request
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login

st.set_page_config(page_title="Planner", layout="wide")
require_login()

st.title("Weekly Planner")

today = date.today()

ACTIVITY_TYPES = {
    "running": ("Running", "#F44336"),
    "lifting": ("Lifting", "#FF9800"),
    "cycling": ("Cycling", "#4CAF50"),
    "frisbee_golf": ("Frisbee Golf", "#2196F3"),
    "rap_writing": ("Rap Writing", "#9C27B0"),
    "other": ("Other", "#607D8B"),
}

TIME_SLOTS = ["Morning", "Midday", "Afternoon", "Evening"]

SCHOOL_SCHEDULE = [
    {"name": "CS 25000 Lab", "days": [3], "time": "9:30 - 11:20 AM", "range_start": "2026-08-27", "range_end": "2026-12-10", "room": "SL 251"},
    {"name": "CS 25100 Pso", "days": [2], "time": "11:30 AM - 12:20 PM", "range_start": "2026-08-26", "range_end": "2026-12-09", "room": "SL 247"},
    {"name": "CS 25000", "days": [1, 3], "time": "1:30 - 2:45 PM", "range_start": "2026-08-25", "range_end": "2026-12-10", "room": "ES 2107"},
    {"name": "CS 25100", "days": [0, 2, 4], "time": "2:30 - 3:20 PM", "range_start": "2026-08-24", "range_end": "2026-12-11", "room": "ES 2107"},
    {"name": "MA 26500", "days": [0, 2, 4], "time": "4:30 - 5:20 PM", "range_start": "2026-08-24", "range_end": "2026-12-11", "room": "SL 011"},
]


@st.cache_data(ttl=300)
def fetch_calendar(url, start_str, end_str):
    from icalendar import Calendar
    import recurring_ical_events

    https_url = url.replace("webcal://", "https://")
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    try:
        req = urllib.request.Request(https_url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=10)
        cal = Calendar.from_ical(response.read())
        events = recurring_ical_events.of(cal).between(
            datetime(start.year, start.month, start.day),
            datetime(end.year, end.month, end.day, 23, 59, 59),
        )
        result = []
        for event in events:
            summary = str(event.get("SUMMARY", ""))
            dtstart = event.get("DTSTART")
            if not dtstart:
                continue
            dtstart = dtstart.dt
            dtend = event.get("DTEND")
            dtend = dtend.dt if dtend else None

            if isinstance(dtstart, datetime):
                event_date = dtstart.date()
                start_time = dtstart.strftime("%I:%M %p").lstrip("0")
                end_time = dtend.strftime("%I:%M %p").lstrip("0") if dtend and isinstance(dtend, datetime) else ""
            else:
                event_date = dtstart
                start_time = "All day"
                end_time = ""
            result.append({
                "date": event_date.isoformat(),
                "title": summary,
                "start_time": start_time,
                "end_time": end_time,
            })
        return result
    except Exception as e:
        st.warning(f"Could not load calendar: {e}")
        return []


# --- Week navigation ---
if "planner_week_offset" not in st.session_state:
    st.session_state["planner_week_offset"] = 0

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("< Prev Week"):
        st.session_state["planner_week_offset"] -= 1
        st.rerun()
with nav3:
    if st.button("Next Week >"):
        st.session_state["planner_week_offset"] += 1
        st.rerun()

week_offset = st.session_state["planner_week_offset"]
week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
week_end = week_start + timedelta(days=6)

with nav2:
    label = "This Week" if week_offset == 0 else f"Week of {week_start.strftime('%b %d')}"
    st.markdown(f"<h4 style='text-align:center; margin:0;'>{label}</h4>", unsafe_allow_html=True)
    if week_offset != 0:
        if st.button("Today", key="go_today"):
            st.session_state["planner_week_offset"] = 0
            st.rerun()

# --- Load data ---
cal_events = []
ical_urls = st.secrets.get("ICAL_URLS", [])
if not ical_urls:
    single = st.secrets.get("ICAL_URL", "")
    if single:
        ical_urls = [single]
for ical_url in ical_urls:
    cal_events.extend(fetch_calendar(ical_url, week_start.isoformat(), week_end.isoformat()))

try:
    activities_data = fetch_all("activities", order_col="date")
except Exception:
    activities_data = []
activities_df = pd.DataFrame(activities_data)

try:
    running_data = fetch_all("running_schedule", order_col="date")
except Exception:
    running_data = []
running_df = pd.DataFrame(running_data)
if not running_df.empty:
    running_df["date"] = pd.to_datetime(running_df["date"]).dt.date

# --- Weekly grid ---
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render_day_column(col, i, day):
    day_str = day.isoformat()
    is_today = day == today
    with col:
        header = f"**{day_names[i]} {day.strftime('%m/%d')}**" if is_today else f"{day_names[i]} {day.strftime('%m/%d')}"
        st.markdown(header)

        day_cal = [e for e in cal_events if e["date"] == day_str]
        for event in sorted(day_cal, key=lambda e: e["start_time"]):
            time_label = event["start_time"]
            if event["end_time"]:
                time_label += f" - {event['end_time']}"
            st.markdown(
                f'<div style="border-left: 3px solid #e94560; padding: 4px 6px; '
                f'margin: 2px 0; border-radius: 3px; font-size: 0.75em;">'
                f'<div style="color: #e94560; font-size: 0.85em;">{time_label}</div>'
                f'{event["title"]}</div>',
                unsafe_allow_html=True,
            )

        for cls in SCHOOL_SCHEDULE:
            s = date.fromisoformat(cls["range_start"])
            e = date.fromisoformat(cls["range_end"])
            if s <= day <= e and day.weekday() in cls["days"]:
                st.markdown(
                    f'<div style="border-left: 3px solid #FF6F00; padding: 4px 6px; '
                    f'margin: 2px 0; border-radius: 3px; font-size: 0.75em; '
                    f'background: rgba(255,111,0,0.08);">'
                    f'<div style="color: #FF6F00; font-size: 0.85em;">{cls["time"]}</div>'
                    f'{cls["name"]} — {cls["room"]}</div>',
                    unsafe_allow_html=True,
                )

        if not running_df.empty:
            day_runs = running_df[running_df["date"] == day]
            for _, run in day_runs.iterrows():
                title = run["workout"].split("\n")[0]
                done = run["completed"]
                color = ACTIVITY_TYPES["running"][1]
                text = f"~~{title}~~" if done else title
                st.markdown(
                    f'<div style="border-left: 3px solid {color}; padding: 4px 6px; '
                    f'margin: 2px 0; border-radius: 3px; font-size: 0.75em; '
                    f'opacity: {"0.5" if done else "1"};">'
                    f'<div style="color: {color}; font-size: 0.85em;">Running</div>'
                    f'{text}</div>',
                    unsafe_allow_html=True,
                )

        if not activities_df.empty:
            day_acts = activities_df[activities_df["date"] == day_str]
            for _, act in day_acts.iterrows():
                atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
                label_text, color = atype
                done = act.get("completed", False)
                title = act.get("title") or label_text
                slot = act.get("time_slot", "")
                st.markdown(
                    f'<div style="border-left: 3px solid {color}; padding: 4px 6px; '
                    f'margin: 2px 0; border-radius: 3px; font-size: 0.75em; '
                    f'opacity: {"0.5" if done else "1"};">'
                    f'<div style="color: {color}; font-size: 0.85em;">{label_text}'
                    f'{" - " + slot if slot else ""}</div>'
                    f'{"~~" + title + "~~" if done else title}</div>',
                    unsafe_allow_html=True,
                )

        if is_today:
            st.markdown("---")


past_days = [i for i in range(7) if (week_start + timedelta(days=i)) < today]
current_future = [i for i in range(7) if (week_start + timedelta(days=i)) >= today]

if past_days and current_future:
    with st.expander(f"Earlier this week ({day_names[past_days[0]]} – {day_names[past_days[-1]]})", expanded=False):
        past_cols = st.columns(len(past_days))
        for ci, i in enumerate(past_days):
            render_day_column(past_cols[ci], i, week_start + timedelta(days=i))

    cols = st.columns(len(current_future))
    for ci, i in enumerate(current_future):
        render_day_column(cols[ci], i, week_start + timedelta(days=i))
else:
    cols = st.columns(7)
    for i in range(7):
        render_day_column(cols[i], i, week_start + timedelta(days=i))

st.divider()

# --- Today's Focus ---
st.subheader("Today")
today_str = today.isoformat()

today_cal = [e for e in cal_events if e["date"] == today_str]
today_classes = [cls for cls in SCHOOL_SCHEDULE
                 if date.fromisoformat(cls["range_start"]) <= today <= date.fromisoformat(cls["range_end"])
                 and today.weekday() in cls["days"]]
today_acts = activities_df[activities_df["date"] == today_str] if not activities_df.empty else pd.DataFrame()
today_runs = running_df[running_df["date"] == today] if not running_df.empty else pd.DataFrame()

if not today_cal and not today_classes and today_acts.empty and today_runs.empty:
    st.info("Nothing scheduled for today.")
else:
    for event in sorted(today_cal, key=lambda e: e["start_time"]):
        time_label = event["start_time"]
        if event["end_time"]:
            time_label += f" - {event['end_time']}"
        st.caption(f"**{time_label}** — {event['title']}")

    for cls in today_classes:
        st.caption(f"**{cls['time']}** — {cls['name']} ({cls['room']})")

    for _, run in today_runs.iterrows():
        title = run["workout"].split("\n")[0]
        rc1, rc2 = st.columns([6, 1])
        if run["completed"]:
            rc1.markdown(f"~~Running: {title}~~ — Done")
        else:
            rc1.markdown(f"**Running:** {title}")
            if rc2.button("Done", key=f"today_run_{run['id']}"):
                update_row("running_schedule", int(run["id"]), {"completed": True})
                st.rerun()

    for _, act in today_acts.iterrows():
        atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
        label_text, _ = atype
        title = act.get("title") or label_text
        ac1, ac2 = st.columns([6, 1])
        if act.get("completed"):
            ac1.markdown(f"~~{label_text}: {title}~~ — Done")
        else:
            ac1.markdown(f"**{label_text}:** {title}")
            if ac2.button("Done", key=f"today_act_{act['id']}"):
                update_row("activities", int(act["id"]), {"completed": True})
                st.rerun()

st.divider()

# --- Add Activity ---
st.subheader("Add Activity")
with st.form("add_activity"):
    ac1, ac2, ac3 = st.columns(3)
    act_type = ac1.selectbox(
        "Type",
        list(ACTIVITY_TYPES.keys()),
        format_func=lambda x: ACTIVITY_TYPES[x][0],
    )
    act_date = ac2.date_input("Date", value=today)
    act_slot = ac3.selectbox("Time of Day", [""] + TIME_SLOTS)

    ac4, ac5 = st.columns(2)
    act_title = ac4.text_input("Title (optional)", placeholder="e.g., Upper body, Beat session")
    act_duration = ac5.number_input("Duration (min)", min_value=0, max_value=300, value=0)
    act_notes = st.text_input("Notes (optional)")

    if st.form_submit_button("Add"):
        insert_row("activities", {
            "date": act_date.isoformat(),
            "activity_type": act_type,
            "title": act_title.strip() or None,
            "time_slot": act_slot or None,
            "duration_min": act_duration if act_duration > 0 else None,
            "notes": act_notes.strip() or None,
            "completed": False,
        })
        st.success(f"Added {ACTIVITY_TYPES[act_type][0]} on {act_date.strftime('%m/%d')}.")
        st.rerun()

# --- Quick Add (multiple at once) ---
with st.expander("Plan the Week"):
    st.caption("Quickly add multiple activities for the week.")
    for i in range(7):
        day = week_start + timedelta(days=i)
        qc1, qc2, qc3 = st.columns([2, 3, 1])
        qc1.markdown(f"**{day_names[i]} {day.strftime('%m/%d')}**")
        q_type = qc2.selectbox(
            "Activity", ["—"] + list(ACTIVITY_TYPES.keys()),
            format_func=lambda x: "—" if x == "—" else ACTIVITY_TYPES[x][0],
            key=f"qplan_{i}",
            label_visibility="collapsed",
        )
        q_title = qc3.text_input("Title", key=f"qtitle_{i}", label_visibility="collapsed", placeholder="Title")
        st.session_state[f"qplan_data_{i}"] = (day.isoformat(), q_type, q_title)

    if st.button("Add All", key="plan_week_add"):
        added = 0
        for i in range(7):
            day_iso, q_type, q_title = st.session_state.get(f"qplan_data_{i}", ("", "—", ""))
            if q_type != "—" and day_iso:
                insert_row("activities", {
                    "date": day_iso,
                    "activity_type": q_type,
                    "title": q_title.strip() or None,
                    "completed": False,
                })
                added += 1
        if added:
            st.success(f"Added {added} activities.")
            st.rerun()
        else:
            st.info("No activities selected.")

# --- Manage Activities ---
if not activities_df.empty:
    with st.expander("Manage Activities"):
        week_acts = activities_df[
            (activities_df["date"] >= week_start.isoformat())
            & (activities_df["date"] <= week_end.isoformat())
        ]
        if week_acts.empty:
            st.info("No activities this week.")
        else:
            for _, act in week_acts.iterrows():
                atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
                label_text, color = atype
                title = act.get("title") or label_text
                day_label = datetime.strptime(act["date"], "%Y-%m-%d").strftime("%a %m/%d")

                mc1, mc2, mc3 = st.columns([5, 1, 1])
                mc1.caption(f"{day_label} — {label_text}: {title}")

                if not act.get("completed"):
                    if mc2.button("Done", key=f"mgmt_done_{act['id']}"):
                        update_row("activities", int(act["id"]), {"completed": True})
                        st.rerun()
                else:
                    mc2.caption("Done")

                ck = f"confirm_del_act_{act['id']}"
                if st.session_state.get(ck):
                    with mc3:
                        st.warning("Sure?")
                        yc, nc = st.columns(2)
                        if yc.button("Yes", key=f"yes_act_{act['id']}"):
                            delete_row("activities", act["id"])
                            st.session_state.pop(ck, None)
                            st.rerun()
                        if nc.button("No", key=f"no_act_{act['id']}"):
                            st.session_state.pop(ck, None)
                            st.rerun()
                else:
                    if mc3.button("Del", key=f"del_act_{act['id']}"):
                        st.session_state[ck] = True
                        st.rerun()
