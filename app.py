import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import urllib.request
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login
from constants import ACTIVITY_TYPES, TIME_SLOTS, TIME_DISPLAY

st.set_page_config(page_title="My Dashboard", layout="wide")
require_login()

today = datetime.now(ZoneInfo("America/Indiana/Indianapolis")).date()

SCHOOL_SCHEDULE = [
    {"name": "CS 25000 Lab", "days": [3], "time": "9:30 - 11:20 AM", "range_start": "2026-08-27", "range_end": "2026-12-10", "room": "SL 251"},
    {"name": "CS 25100 Pso", "days": [2], "time": "11:30 AM - 12:20 PM", "range_start": "2026-08-26", "range_end": "2026-12-09", "room": "SL 247"},
    {"name": "CS 25000", "days": [1, 3], "time": "1:30 - 2:45 PM", "range_start": "2026-08-25", "range_end": "2026-12-10", "room": "ES 2107"},
    {"name": "CS 25100", "days": [0, 2, 4], "time": "2:30 - 3:20 PM", "range_start": "2026-08-24", "range_end": "2026-12-11", "room": "ES 2107"},
    {"name": "MA 26500", "days": [0, 2, 4], "time": "4:30 - 5:20 PM", "range_start": "2026-08-24", "range_end": "2026-12-11", "room": "SL 011"},
]

day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
class_keywords = [c["name"].split()[0] + " " + c["name"].split()[1] for c in SCHOOL_SCHEDULE]


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
    except Exception:
        return []


# --- Week state ---
if "planner_week_offset" not in st.session_state:
    st.session_state["planner_week_offset"] = 0
week_offset = st.session_state["planner_week_offset"]
week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
week_end = week_start + timedelta(days=6)

# --- Load all data ---
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

try:
    book_data = fetch_all("books")
except Exception:
    book_data = []
books_df = pd.DataFrame(book_data)
reading_books = books_df[books_df["status"] == "reading"] if not books_df.empty else pd.DataFrame()

try:
    todo_data = fetch_all("todos", order_col="created_at")
except Exception:
    todo_data = []
todos_df = pd.DataFrame(todo_data)
active_todos = todos_df[todos_df["completed"] == False] if not todos_df.empty else pd.DataFrame()

# --- Streak ---
_completed_dates = set()
if not activities_df.empty:
    _completed_dates.update(activities_df[activities_df["completed"] == True]["date"].tolist())
if not running_df.empty:
    _completed_dates.update(
        running_df[running_df["completed"] == True]["date"].apply(lambda d: d.isoformat()).tolist()
    )


def _compute_streak():
    s = 0
    check = today
    if today.isoformat() not in _completed_dates:
        check = today - timedelta(days=1)
    while s < 365:
        if check.isoformat() in _completed_dates:
            s += 1
            check -= timedelta(days=1)
        else:
            break
    return s


_streak = _compute_streak()

_wk_s, _wk_e = week_start.isoformat(), week_end.isoformat()
_wk_act_total, _wk_act_done = 0, 0
if not activities_df.empty:
    _wa = activities_df[(activities_df["date"] >= _wk_s) & (activities_df["date"] <= _wk_e)]
    _wk_act_total = len(_wa)
    _wk_act_done = len(_wa[_wa["completed"] == True])
_wk_run_total, _wk_run_done = 0, 0
if not running_df.empty:
    _wr = running_df[(running_df["date"] >= week_start) & (running_df["date"] <= week_end)]
    _wr_real = _wr[~_wr["workout"].str.startswith("Rest", na=False)]
    _wk_run_total = len(_wr_real)
    _wk_run_done = len(_wr_real[_wr_real["completed"] == True])


# ============================================================
# TODAY
# ============================================================
if "focus_day" not in st.session_state:
    st.session_state["focus_day"] = today.isoformat()

focus_str = st.session_state["focus_day"]
focus_date = date.fromisoformat(focus_str)
is_viewing_today = focus_date == today

hdr1, hdr2 = st.columns([5, 1])
day_label = day_names[focus_date.weekday()]
hdr1.title(f"{day_label}, {focus_date.strftime('%B %d')}")
if is_viewing_today:
    hdr2.link_button("Ayden Music", "https://ayden-music.onrender.com/")
else:
    if hdr2.button("Back to today"):
        st.session_state["focus_day"] = today.isoformat()
        st.rerun()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Streak", f"{_streak} day{'s' if _streak != 1 else ''}")
m2.metric("Activities", f"{_wk_act_done}/{_wk_act_total}" if _wk_act_total else "0")
m3.metric("Runs", f"{_wk_run_done}/{_wk_run_total}" if _wk_run_total else "0")
m4.metric("Reading", len(reading_books))

st.divider()

# --- Schedule for focused day ---
focus_cal = [e for e in cal_events if e["date"] == focus_str
             and not any(kw in e["title"] for kw in class_keywords)]
focus_classes = [cls for cls in SCHOOL_SCHEDULE
                 if date.fromisoformat(cls["range_start"]) <= focus_date <= date.fromisoformat(cls["range_end"])
                 and focus_date.weekday() in cls["days"]]
focus_acts = activities_df[activities_df["date"] == focus_str] if not activities_df.empty else pd.DataFrame()
focus_runs = running_df[running_df["date"] == focus_date] if not running_df.empty else pd.DataFrame()

has_schedule = bool(focus_cal or focus_classes or not focus_acts.empty or not focus_runs.empty)

if has_schedule:
    for event in sorted(focus_cal, key=lambda e: e["start_time"]):
        time_label = event["start_time"]
        if event["end_time"]:
            time_label += f" - {event['end_time']}"
        st.markdown(
            f'<div style="border-left: 3px solid #e94560; padding: 4px 8px; '
            f'margin: 2px 0; border-radius: 3px;">'
            f'<span style="color: #e94560; font-size: 0.85em;">{time_label}</span> '
            f'{event["title"]}</div>',
            unsafe_allow_html=True,
        )

    for cls in focus_classes:
        st.markdown(
            f'<div style="border-left: 3px solid #FF6F00; padding: 4px 8px; '
            f'margin: 2px 0; border-radius: 3px; background: rgba(255,111,0,0.08);">'
            f'<span style="color: #FF6F00; font-size: 0.85em;">{cls["time"]}</span> '
            f'{cls["name"]} — {cls["room"]}</div>',
            unsafe_allow_html=True,
        )

    for _, run in focus_runs.iterrows():
        workout = run["workout"]
        if not isinstance(workout, str) or not workout.strip():
            continue
        title = workout.split("\n")[0]
        color = ACTIVITY_TYPES["running"][1]
        rc1, rc2 = st.columns([6, 1])
        if run["completed"]:
            rc1.markdown(
                f'<div style="border-left: 3px solid {color}; padding: 4px 8px; '
                f'margin: 2px 0; border-radius: 3px; opacity: 0.5;">'
                f'<span style="color: {color}; font-size: 0.85em;">Running</span> '
                f'~~{title}~~</div>',
                unsafe_allow_html=True,
            )
        else:
            rc1.markdown(
                f'<div style="border-left: 3px solid {color}; padding: 4px 8px; '
                f'margin: 2px 0; border-radius: 3px;">'
                f'<span style="color: {color}; font-size: 0.85em;">Running</span> '
                f'**{title}**</div>',
                unsafe_allow_html=True,
            )
            if rc2.button("Done", key=f"focus_run_{run['id']}"):
                update_row("running_schedule", int(run["id"]), {"completed": True})
                st.rerun()

    for _, act in focus_acts.iterrows():
        atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
        label_text, color = atype
        raw_title = act.get("title")
        title = raw_title if isinstance(raw_title, str) and raw_title.strip() else label_text
        slot = act.get("time_slot", "")
        time_str = TIME_DISPLAY.get(slot, slot) if isinstance(slot, str) and slot else ""
        time_prefix = f"{time_str} " if time_str else ""
        ac1, ac2 = st.columns([6, 1])
        if act.get("completed"):
            ac1.markdown(
                f'<div style="border-left: 3px solid {color}; padding: 4px 8px; '
                f'margin: 2px 0; border-radius: 3px; opacity: 0.5;">'
                f'<span style="color: {color}; font-size: 0.85em;">{time_prefix}{label_text}</span> '
                f'~~{title}~~</div>',
                unsafe_allow_html=True,
            )
        else:
            ac1.markdown(
                f'<div style="border-left: 3px solid {color}; padding: 4px 8px; '
                f'margin: 2px 0; border-radius: 3px;">'
                f'<span style="color: {color}; font-size: 0.85em;">{time_prefix}{label_text}</span> '
                f'**{title}**</div>',
                unsafe_allow_html=True,
            )
            if ac2.button("Done", key=f"focus_act_{act['id']}"):
                update_row("activities", int(act["id"]), {"completed": True})
                st.rerun()
else:
    st.caption("Nothing scheduled.")

# --- Currently Reading ---
if is_viewing_today and not reading_books.empty:
    st.markdown("")
    st.caption("Currently Reading")
    for _, book in reading_books.iterrows():
        cur = int(book["current_page"]) if pd.notna(book.get("current_page")) else 0
        total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
        line = f"**{book['title']}**"
        if book.get("author"):
            line += f" — {book['author']}"
        if total > 0:
            pct = cur / total
            line += f" · p.{cur}/{total} ({pct:.0%})"
        elif cur > 0:
            line += f" · p.{cur}"

        bc1, bc2, bc3 = st.columns([5, 2, 1])
        bc1.markdown(line)
        if total > 0:
            bc1.progress(min(cur / total, 1.0))
        new_page = bc2.number_input(
            "Page", min_value=0, max_value=max(total, 9999),
            value=cur, key=f"dash_page_{book['id']}",
            label_visibility="collapsed",
        )
        if new_page != cur:
            delta = new_page - cur
            btn_label = f"+{delta}p" if delta > 0 else "Set"
            if bc3.button(btn_label, key=f"dash_upd_{book['id']}"):
                updates = {"current_page": new_page}
                if total > 0 and new_page >= total:
                    updates["status"] = "completed"
                    updates["end_date"] = today.isoformat()
                    updates["current_page"] = total
                update_row("books", int(book["id"]), updates)
                st.rerun()

# --- Active To-Dos ---
if is_viewing_today and not active_todos.empty:
    from constants import PRIORITY_COLORS
    st.markdown("")
    st.caption("To Do")
    for priority in ["high", "medium", "low"]:
        group = active_todos[active_todos["priority"] == priority] if "priority" in active_todos.columns else pd.DataFrame()
        for _, row in group.iterrows():
            color = PRIORITY_COLORS.get(row.get("priority", "medium"), "#FF9800")
            tc1, tc2 = st.columns([8, 1])
            tc1.markdown(
                f'<span style="border-left:3px solid {color};padding-left:8px;">'
                f'{row["task"]}</span>',
                unsafe_allow_html=True,
            )
            if tc2.button("Done", key=f"dash_todo_{row['id']}"):
                delete_row("todos", int(row["id"]))
                st.rerun()

# --- Quick Add ---
st.markdown("")
with st.form("quick_add", clear_on_submit=True):
    qa1, qa2, qa3, qa4 = st.columns([2, 3, 2, 1])
    qa_type = qa1.selectbox(
        "Type", list(ACTIVITY_TYPES.keys()),
        format_func=lambda x: ACTIVITY_TYPES[x][0],
        label_visibility="collapsed",
    )
    qa_title = qa2.text_input("Title", placeholder="Title (optional)", label_visibility="collapsed")
    qa_date = qa3.date_input("Date", value=focus_date, label_visibility="collapsed")
    if qa4.form_submit_button("Add"):
        insert_row("activities", {
            "date": qa_date.isoformat(),
            "activity_type": qa_type,
            "title": qa_title.strip() or None,
            "completed": False,
        })
        st.rerun()


# ============================================================
# THIS WEEK
# ============================================================
st.divider()

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("< Prev Week"):
        st.session_state["planner_week_offset"] -= 1
        st.rerun()
with nav3:
    if st.button("Next Week >"):
        st.session_state["planner_week_offset"] += 1
        st.rerun()
with nav2:
    label = "This Week" if week_offset == 0 else f"Week of {week_start.strftime('%b %d')}"
    st.markdown(f"<h4 style='text-align:center; margin:0;'>{label}</h4>", unsafe_allow_html=True)
    if week_offset != 0:
        if st.button("Today", key="go_today"):
            st.session_state["planner_week_offset"] = 0
            st.rerun()


def render_day_column(col, i, day):
    day_str = day.isoformat()
    is_today = day == today
    with col:
        btn_label = f"**{day_names[i]} {day.strftime('%m/%d')}**" if is_today else f"{day_names[i]} {day.strftime('%m/%d')}"
        if st.button(btn_label, key=f"sel_day_{day_str}", use_container_width=True):
            st.session_state["focus_day"] = day_str
            st.rerun()

        day_cal = [e for e in cal_events if e["date"] == day_str
                   and not any(kw in e["title"] for kw in class_keywords)]
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
                workout = run["workout"]
                if not isinstance(workout, str) or not workout.strip():
                    continue
                title = workout.split("\n")[0]
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
                raw_title = act.get("title")
                title = raw_title if isinstance(raw_title, str) and raw_title.strip() else label_text
                slot = act.get("time_slot", "")
                time_str = TIME_DISPLAY.get(slot, slot) if isinstance(slot, str) and slot else ""
                st.markdown(
                    f'<div style="border-left: 3px solid {color}; padding: 4px 6px; '
                    f'margin: 2px 0; border-radius: 3px; font-size: 0.75em; '
                    f'opacity: {"0.5" if done else "1"};">'
                    f'<div style="color: {color}; font-size: 0.85em;">{label_text}'
                    f'{" - " + time_str if time_str else ""}</div>'
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


# ============================================================
# TOOLS
# ============================================================
st.divider()

with st.expander("Add Activity"):
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
                raw_title = act.get("title")
                title = raw_title if isinstance(raw_title, str) and raw_title.strip() else label_text
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

with st.expander("Plan the Week"):
    st.caption("Quickly add multiple activities for the week.")
    for i in range(7):
        day = week_start + timedelta(days=i)
        qc1, qc2, qc3 = st.columns([2, 3, 1])
        qc1.markdown(f"**{day_names[i]} {day.strftime('%m/%d')}**")
        q_type = qc2.selectbox(
            "Activity", ["---"] + list(ACTIVITY_TYPES.keys()),
            format_func=lambda x: "---" if x == "---" else ACTIVITY_TYPES[x][0],
            key=f"qplan_{i}",
            label_visibility="collapsed",
        )
        q_title = qc3.text_input("Title", key=f"qtitle_{i}", label_visibility="collapsed", placeholder="Title")
        st.session_state[f"qplan_data_{i}"] = (day.isoformat(), q_type, q_title)

    if st.button("Add All", key="plan_week_add"):
        added = 0
        for i in range(7):
            day_iso, q_type, q_title = st.session_state.get(f"qplan_data_{i}", ("", "---", ""))
            if q_type != "---" and day_iso:
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

with st.expander("Sync to phone"):
    ICAL_FEED_URL = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/ical/training_plan.ics"

    TIME_HOURS = {"Morning": (8, 0), "Midday": (11, 0), "Afternoon": (14, 0), "Evening": (17, 30)}
    DURATION_MAP = {
        "lifting": 45, "cycling": 60, "frisbee_golf": 120,
        "rap_writing": 90, "running": 45, "other": 60,
    }

    TZ_ID = "America/Indiana/Indianapolis"

    def build_ics():
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MyDashboard//Planner//EN",
            "CALSCALE:GREGORIAN",
            "X-WR-CALNAME:Training Plan",
            f"X-WR-TIMEZONE:{TZ_ID}",
        ]

        if not activities_df.empty:
            for _, act in activities_df.iterrows():
                atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
                label_text, _ = atype
                title = act.get("title") or label_text
                summary = f"{label_text}: {title}" if act.get("title") else label_text
                slot = act.get("time_slot", "Morning")
                h, m = TIME_HOURS.get(slot, (8, 0))
                dur = act.get("duration_min") or DURATION_MAP.get(act["activity_type"], 60)
                d = act["date"].replace("-", "")
                dtstart = f"{d}T{h:02d}{m:02d}00"
                end_h, end_m = divmod(h * 60 + m + dur, 60)
                dtend = f"{d}T{end_h:02d}{end_m:02d}00"
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:act-{act['id']}@mydashboard",
                    f"DTSTART;TZID={TZ_ID}:{dtstart}",
                    f"DTEND;TZID={TZ_ID}:{dtend}",
                    f"SUMMARY:{summary}",
                    "END:VEVENT",
                ])

        if not running_df.empty:
            for _, run in running_df.iterrows():
                workout = run["workout"]
                if not isinstance(workout, str) or not workout.strip():
                    continue
                parts = workout.strip().split("\n")
                title = parts[0].strip()
                detail_lines = [p.strip().lstrip("- ") for p in parts[1:] if p.strip()]
                description = " | ".join(detail_lines) if detail_lines else title
                d = run["date"].strftime("%Y%m%d")
                event = [
                    "BEGIN:VEVENT",
                    f"UID:run-{run['id']}@mydashboard",
                    f"DTSTART;TZID={TZ_ID}:{d}T210000",
                    f"DTEND;TZID={TZ_ID}:{d}T220000",
                    f"SUMMARY:Running: {title}",
                    f"DESCRIPTION:{description}",
                    "END:VEVENT",
                ]
                lines.extend(event)

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    def publish_feed():
        from db import get_supabase
        sb = get_supabase()
        ics_bytes = build_ics().encode("utf-8")
        try:
            sb.storage.from_("ical").update(
                "training_plan.ics", ics_bytes,
                {"content-type": "text/calendar", "cache-control": "max-age=300"},
            )
        except Exception:
            sb.storage.from_("ical").upload(
                "training_plan.ics", ics_bytes,
                {"content-type": "text/calendar", "cache-control": "max-age=300"},
            )

    if st.button("Publish feed", key="publish_ical"):
        try:
            publish_feed()
            st.success("Published! Subscribe on your phone using the URL below.")
        except Exception as e:
            st.error(f"Failed — run ical_bucket.sql in Supabase first: {e}")

    webcal_url = ICAL_FEED_URL.replace("https://", "webcal://")
    st.code(webcal_url, language=None)
    st.caption("Add this URL as a calendar subscription on your phone. It refreshes automatically.")

with st.expander(f"{today.year} in Review"):
    _year_start = date(today.year, 1, 1).isoformat()
    yr1, yr2, yr3 = st.columns(3)

    _yr_act_count = 0
    if not activities_df.empty:
        _yr_acts = activities_df[(activities_df["date"] >= _year_start) & (activities_df["completed"] == True)]
        _yr_act_count = len(_yr_acts)
    yr1.metric("Activities", _yr_act_count)

    _yr_run_count = 0
    if not running_df.empty:
        _yr_runs = running_df[running_df["date"] >= date(today.year, 1, 1)]
        _yr_runs_real = _yr_runs[~_yr_runs["workout"].str.startswith("Rest", na=False)]
        _yr_run_count = len(_yr_runs_real[_yr_runs_real["completed"] == True])
    yr2.metric("Run Workouts", _yr_run_count)

    if not books_df.empty:
        completed_books = books_df[books_df["status"] == "completed"]
        if not completed_books.empty and "end_date" in completed_books.columns:
            _yr_finished = completed_books[completed_books["end_date"].fillna("") >= _year_start]
            yr3.metric("Books Read", len(_yr_finished))
            _yr_pages = int(_yr_finished["total_pages"].dropna().sum()) if "total_pages" in _yr_finished.columns else 0
            if _yr_pages > 0:
                yr3.caption(f"{_yr_pages:,} pages")
        else:
            yr3.metric("Books Read", 0)
    else:
        yr3.metric("Books Read", 0)

    if not activities_df.empty:
        _yr_all = activities_df[(activities_df["date"] >= _year_start) & (activities_df["completed"] == True)]
        if not _yr_all.empty:
            st.markdown("**Activity Breakdown**")
            _type_chart = _yr_all["activity_type"].map(
                lambda x: ACTIVITY_TYPES.get(x, ACTIVITY_TYPES["other"])[0]
            ).value_counts()
            st.bar_chart(_type_chart)
