# MyDashboard

Personal Streamlit dashboard with a Supabase (PostgreSQL) backend. Tracks gaming franchise data, fitness, reading, music, wardrobe coordination, weather, and daily planning.

## Pages

| # | Page | What it does |
|---|------|-------------|
| — | **Dashboard** (app.py) | Today-first planner: focused day view with Google Calendar + iCal integration, school schedule, running workouts, activity tracking, currently reading progress, and active to-dos. Weekly grid with collapsible past days, streak tracker, quick-add, iCal feed publishing, year-in-review analytics. |
| 1 | **CFB Dynasty** | College Football draft pick tracker. Per-school analytics: picks by round/year/position/class, measurables, filters, bulk import. |
| 2 | **Madden Franchise** | Full franchise tracker: season awards, team win records with division standings, All-Pro teams rendered as a football formation, 99 Club tracking, player career tracker, parity index. End-of-season form for one-shot data entry. |
| 3 | **Rhymes** | Rhyme group reference for rap writing. Search, inline edit/delete, group analytics, bulk import. |
| 4 | **Training** | Running schedule with workout types (speed, tempo, long, easy, hills), run logging (manual, GPX upload, bulk GPX, Strava CSV import), today's weather-based best run time, weekly view, auto-complete on log, and 7 analytics modules (weekly mileage, pace trend, training load, effort zones, splits, route comparison, PRs). |
| 5 | **Books** | Reading log with page tracking, pace stats, start/finish dates, inline notes & highlights per book. Currently reading progress bars, want-to-read queue, genre/decade/pages analytics. |
| 6 | **Wardrobe** | Closet digitizer: upload photos of clothing items, auto-extract dominant colors, tag weather suitability and layering pieces. Color theory matcher with complementary/analogous/split-complementary palettes shows matching items from your closet. Weather-aware outfit suggestions pairing tops, bottoms, and layers by color compatibility. |
| 7 | **Minecraft** | Coordinate tracker with dimension-colored cards, Nether/Overworld conversion, inline editing, and Chunkbase seed map link. |
| 8 | **To Do** | Priority-based task list (high/medium/low). Per-item copy via code block, inline edit (task + priority), delete on complete. |
| 9 | **Lyrics** | Rap writing workspace with inline rhyme lookup from the Rhymes database. Save drafts, track status (draft/in progress/finished), bar/word counts. |
| 10 | **Weather** | 3-day forecast with hourly temperature, humidity, and rain charts. Current conditions, best time to go outside, best time to run (weighted against humidity), adjustable run deadline slider, high-humidity warnings. Shares location with Training and Wardrobe pages. |

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
constants.py        # Shared constants (NFL divisions, positions, activity types, priorities)
ui_helpers.py       # Reusable UI components (save_edits, delete_button)
weather.py          # Open-Meteo API: forecast, geocoding, best-time calculations
pages/              # Streamlit multipage app pages
requirements.txt    # Python dependencies
```

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Supabase (PostgreSQL + Row Level Security)
- **Weather**: Open-Meteo API (free, no key required)
- **Calendar**: iCalendar parsing with `icalendar` + `recurring-ical-events`
- **GPS**: GPX file parsing with `gpxpy`
- **Auth**: Streamlit's built-in user email check
