# MyDashboard

Personal Streamlit dashboard with a Supabase (PostgreSQL) backend. Tracks gaming franchise data, fitness, reading, music, wardrobe coordination, and daily planning.

## Pages

| # | Page | What it does |
|---|------|-------------|
| — | **Dashboard** (app.py) | Weekly planner with Google Calendar + iCal integration, school schedule, running workouts, and activity tracking. Streak tracker, weekly stats, day focus view, quick-add activities, iCal feed publishing, and year-in-review analytics. |
| 1 | **CFB Dynasty** | College Football draft pick tracker. Per-school analytics: picks by round/year/position/class, measurables, filters, bulk import. |
| 2 | **Madden Franchise** | Full franchise tracker: season awards, team win records with division standings, All-Pro teams rendered as a football formation, 99 Club tracking, player career tracker, parity index. End-of-season form for one-shot data entry. |
| 3 | **Rhymes** | Rhyme group reference for rap writing. Search, edit, group analytics. |
| 4 | **Training** | Multi-activity training planner. Running schedule with workout types (speed, tempo, long, easy, hills), unified weekly view across all activities, quick-add presets for lifting/cycling/frisbee golf, progress stats, and CSV export. |
| 5 | **Books** | Reading log with page tracking, pace stats, start/finish dates. Currently reading progress bars, want-to-read queue, genre/decade analytics. |
| 6 | **Wardrobe** | Color theory tool. Pick a color, see complementary/analogous/triadic/split-complementary palettes, neutrals, and outfit pairing advice. |
| 7 | **Minecraft** | Coordinate tracker with dimension-colored cards, Nether/Overworld conversion, and Chunkbase seed map link. |
| 8 | **To Do** | Priority-based task list (high/medium/low) with completion and undo. |
| 9 | **Lyrics** | Rap writing workspace with inline rhyme group lookup from the Rhymes database. Save drafts, track status, bar/word counts. Requires `lyrics` table (SQL provided on first load). |

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Supabase** — create `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```

3. **Optional: Calendar integration** — add iCal URLs to secrets:
   ```toml
   ICAL_URLS = [
       "webcal://your-calendar-url",
       "https://calendar.google.com/calendar/ical/..."
   ]
   ```

4. **Run**
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
app.py              # Dashboard home + planner + iCal sync
auth.py             # Email-based access control
db.py               # Supabase client, CRUD helpers, game registry
colors.py           # NFL/college team colors, theme application
constants.py        # Shared constants (NFL divisions, positions, activity types)
ui_helpers.py       # Reusable UI components (save_edits, delete_button)
pages/              # Streamlit multipage app pages
requirements.txt    # Python dependencies
```

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Supabase (PostgreSQL + Row Level Security)
- **Calendar**: iCalendar parsing with `icalendar` + `recurring-ical-events`
- **Auth**: Streamlit's built-in user email check
