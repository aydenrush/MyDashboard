import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import urllib.request
from db import fetch_all, fetch_games, insert_row, delete_row, update_row
from auth import require_login
from colors import get_nfl_colors
from constants import ROUND_ORDER, AWARD_COLS

st.set_page_config(page_title="My Dashboard", layout="wide")
require_login()

st.title("Dashboard")
st.link_button("Ayden Music", "https://aydenmusic.streamlit.app")

NFL_COLORS = get_nfl_colors()

today = datetime.now(ZoneInfo("America/Indiana/Indianapolis")).date()

ACTIVITY_TYPES = {
    "running": ("Running", "#F44336"),
    "lifting": ("Lifting", "#FF9800"),
    "cycling": ("Cycling", "#4CAF50"),
    "frisbee_golf": ("Frisbee Golf", "#2196F3"),
    "rap_writing": ("Rap Writing", "#9C27B0"),
    "other": ("Other", "#607D8B"),
}

TIME_SLOTS = ["Morning", "Midday", "Afternoon", "Evening"]
TIME_DISPLAY = {"Morning": "8 AM", "Midday": "11 AM", "Afternoon": "2 PM", "Evening": "5:30 PM"}

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
    except Exception:
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


def render_day_column(col, i, day, clickable=True):
    day_str = day.isoformat()
    is_today = day == today
    with col:
        if clickable:
            btn_label = f"**{day_names[i]} {day.strftime('%m/%d')}**" if is_today else f"{day_names[i]} {day.strftime('%m/%d')}"
            if st.button(btn_label, key=f"sel_day_{day_str}", use_container_width=True):
                st.session_state["focus_day"] = day_str
                st.rerun()
        else:
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
                title = act.get("title") or label_text
                slot = act.get("time_slot", "")
                time_str = TIME_DISPLAY.get(slot, slot) if slot else ""
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

st.divider()

# --- Day Focus ---
if "focus_day" not in st.session_state:
    st.session_state["focus_day"] = today.isoformat()

focus_str = st.session_state["focus_day"]
focus_date = date.fromisoformat(focus_str)
focus_weekday = day_names[focus_date.weekday()]

fc1, fc2 = st.columns([6, 1])
fc1.subheader(f"{focus_weekday} {focus_date.strftime('%B %d')}")
if focus_str != today.isoformat():
    if fc2.button("Back to today", key="focus_today"):
        st.session_state["focus_day"] = today.isoformat()
        st.rerun()

focus_cal = [e for e in cal_events if e["date"] == focus_str]
focus_classes = [cls for cls in SCHOOL_SCHEDULE
                 if date.fromisoformat(cls["range_start"]) <= focus_date <= date.fromisoformat(cls["range_end"])
                 and focus_date.weekday() in cls["days"]]
focus_acts = activities_df[activities_df["date"] == focus_str] if not activities_df.empty else pd.DataFrame()
focus_runs = running_df[running_df["date"] == focus_date] if not running_df.empty else pd.DataFrame()

if not focus_cal and not focus_classes and focus_acts.empty and focus_runs.empty:
    st.info("Nothing scheduled.")
else:
    for event in sorted(focus_cal, key=lambda e: e["start_time"]):
        time_label = event["start_time"]
        if event["end_time"]:
            time_label += f" - {event['end_time']}"
        st.caption(f"**{time_label}** — {event['title']}")

    for cls in focus_classes:
        st.caption(f"**{cls['time']}** — {cls['name']} ({cls['room']})")

    for _, run in focus_runs.iterrows():
        workout = run["workout"]
        if not isinstance(workout, str) or not workout.strip():
            continue
        title = workout.split("\n")[0]
        rc1, rc2 = st.columns([6, 1])
        if run["completed"]:
            rc1.markdown(f"~~Running: {title}~~ — Done")
        else:
            rc1.markdown(f"**Running:** {title}")
            if rc2.button("Done", key=f"focus_run_{run['id']}"):
                update_row("running_schedule", int(run["id"]), {"completed": True})
                st.rerun()

    for _, act in focus_acts.iterrows():
        atype = ACTIVITY_TYPES.get(act["activity_type"], ACTIVITY_TYPES["other"])
        label_text, _ = atype
        title = act.get("title") or label_text
        slot = act.get("time_slot", "")
        time_str = TIME_DISPLAY.get(slot, slot) if slot else ""
        ac1, ac2 = st.columns([6, 1])
        if act.get("completed"):
            ac1.markdown(f"~~{time_str + ' · ' if time_str else ''}{label_text}: {title}~~ — Done")
        else:
            ac1.markdown(f"**{time_str + ' · ' if time_str else ''}{label_text}:** {title}")
            if ac2.button("Done", key=f"focus_act_{act['id']}"):
                update_row("activities", int(act["id"]), {"completed": True})
                st.rerun()

st.divider()

# --- Add Activity ---
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

# --- Plan the Week ---
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

# --- Sync to phone ---
with st.expander("Sync to phone"):
    ICAL_FEED_URL = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/ical/training_plan.ics"

    TIME_HOURS = {"Morning": (8, 0), "Midday": (11, 0), "Afternoon": (14, 0), "Evening": (17, 30)}
    DURATION_MAP = {
        "lifting": 45, "cycling": 60, "frisbee_golf": 120,
        "rap_writing": 90, "running": 45, "other": 60,
    }

    def build_ics():
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MyDashboard//Planner//EN",
            "CALSCALE:GREGORIAN",
            "X-WR-CALNAME:Training Plan",
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
                    f"DTSTART:{dtstart}",
                    f"DTEND:{dtend}",
                    f"SUMMARY:{summary}",
                    "END:VEVENT",
                ])

        def ical_fold(line):
            """Fold long lines per RFC 5545 (max 75 octets)."""
            result = []
            while len(line.encode("utf-8")) > 75:
                cut = 75
                while cut > 0 and len(line[:cut].encode("utf-8")) > 75:
                    cut -= 1
                result.append(line[:cut])
                line = " " + line[cut:]
            result.append(line)
            return "\r\n".join(result)

        def ical_escape(text):
            return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        if not running_df.empty:
            for _, run in running_df.iterrows():
                workout = run["workout"]
                if not isinstance(workout, str) or not workout.strip():
                    continue
                title = workout.split("\n")[0]
                details = ical_escape(workout)
                d = run["date"].strftime("%Y%m%d")
                event = [
                    "BEGIN:VEVENT",
                    f"UID:run-{run['id']}@mydashboard",
                    f"DTSTART:{d}T063000",
                    f"DTEND:{d}T073000",
                    ical_fold(f"SUMMARY:Running: {title}"),
                    ical_fold(f"DESCRIPTION:{details}"),
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

st.divider()

# --- Books ---
st.subheader("Books")
try:
    book_data = fetch_all("books")
    if book_data:
        bdf = pd.DataFrame(book_data)
        reading_books = bdf[bdf["status"] == "reading"]
        completed_books = bdf[bdf["status"] == "completed"]
        b1, b2, b3 = st.columns(3)
        b1.metric("Reading", len(reading_books))
        b2.metric("Completed", len(completed_books))
        b3.metric("Want to Read", len(bdf[bdf["status"] == "want_to_read"]))
        for _, book in reading_books.iterrows():
            line = f"**{book['title']}**"
            if book.get("author"):
                line += f" — {book['author']}"
            st.caption(line)
    else:
        st.info("No books logged yet.")
except Exception:
    st.info("No books logged yet.")

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

st.divider()

# --- CFB Dynasty ---
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

st.subheader("CFB Dynasty")

if not picks_df.empty:
    cfb_m1, cfb_m2, cfb_m3, cfb_m4 = st.columns(4)
    cfb_m1.metric("Total Picks", len(picks_df))
    first_rd = picks_df[picks_df["round"] == "1st"]
    cfb_m2.metric("1st Rounders", len(first_rd))
    cfb_m3.metric("Draft Classes", picks_df["year"].nunique())
    top_pos = picks_df["position"].value_counts().idxmax() if "position" in picks_df.columns else "—"
    cfb_m4.metric("Top Position", top_pos)

    with st.expander("Details"):
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

    with st.expander("Details"):
        mad_left, mad_right = st.columns(2)
        with mad_left:
            st.markdown("**Award Leaders**")
            leaders = []
            for col_name, lbl in AWARD_COLS.items():
                if col_name in seasons_df.columns:
                    counts = seasons_df[col_name].dropna().value_counts()
                    if not counts.empty:
                        leaders.append({"Award": lbl, "Leader": counts.index[0], "Times": counts.iloc[0]})
            if leaders:
                st.dataframe(pd.DataFrame(leaders), use_container_width=True, hide_index=True)
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
else:
    st.info("No Madden data loaded.")
