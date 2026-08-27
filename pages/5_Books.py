import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
from db import fetch_all, insert_row, update_row, delete_row
from auth import require_login

st.set_page_config(page_title="Books", layout="wide")
require_login()

st.title("Reading Log")

try:
    data = fetch_all("books", order_col="created_at")
except Exception:
    data = []
df = pd.DataFrame(data)

try:
    _notes_data = fetch_all("book_notes", order_col="created_at")
except Exception:
    _notes_data = None

STATUS_LABELS = {
    "reading": "Currently Reading",
    "completed": "Completed",
    "want_to_read": "Want to Read",
}

today = datetime.now(ZoneInfo("America/Indiana/Indianapolis")).date()


def book_line(book, include_pages=True):
    line = f"**{book['title']}**"
    if book.get("author"):
        line += f" — {book['author']}"
    if book.get("genre"):
        line += f" · {book['genre']}"
    yr = int(book["year_published"]) if pd.notna(book.get("year_published")) else 0
    if yr > 0:
        line += f" · {yr}"
    if include_pages:
        total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
        if total > 0:
            line += f" · {total}p"
    return line

# --- Currently Reading ---
reading = df[df["status"] == "reading"] if not df.empty else pd.DataFrame()

if not reading.empty:
    st.subheader("Currently Reading")
    for _, book in reading.iterrows():
        title_line = book_line(book, include_pages=False)

        cur = int(book["current_page"]) if pd.notna(book.get("current_page")) else 0
        total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0

        if total > 0:
            pct = cur / total
            title_line += f" · p.{cur}/{total} ({pct:.0%})"
        elif cur > 0:
            title_line += f" · p.{cur}"

        if book.get("start_date"):
            started = book["start_date"]
            if isinstance(started, str):
                started = date.fromisoformat(started)
            days = (today - started).days
            title_line += f" · {days}d in"
            if days > 0 and cur > 0:
                title_line += f" · {cur / days:.0f} pg/day"

        bc1, bc2, bc3 = st.columns([5, 2, 1])
        bc1.markdown(title_line)

        if total > 0:
            bc1.progress(min(cur / total, 1.0))

        new_page = bc2.number_input(
            "Page", min_value=0, max_value=max(total, 9999),
            value=cur, key=f"page_{book['id']}",
            label_visibility="collapsed",
        )
        if new_page != cur:
            delta = new_page - cur
            if bc2.button(f"Update (+{delta}p)" if delta > 0 else "Update", key=f"upd_page_{book['id']}"):
                updates = {"current_page": new_page}
                if total > 0 and new_page >= total:
                    updates["status"] = "completed"
                    updates["end_date"] = today.isoformat()
                    updates["current_page"] = total
                update_row("books", int(book["id"]), updates)
                st.rerun()

        if bc3.button("Finish", key=f"finish_{book['id']}"):
            updates = {"status": "completed", "end_date": today.isoformat()}
            if total > 0:
                updates["current_page"] = total
            update_row("books", int(book["id"]), updates)
            st.rerun()

        if _notes_data is not None:
            _bn = [n for n in _notes_data if n.get("book_id") == book["id"]]
            with st.expander(f"Notes ({len(_bn)})" if _bn else "Notes"):
                if _bn:
                    for _note in sorted(_bn, key=lambda n: n.get("created_at", ""), reverse=True):
                        _pg = f" · p.{_note['page_number']}" if _note.get("page_number") else ""
                        st.markdown(f"> {_note['content']}{_pg}")
                with st.form(f"add_note_{book['id']}", clear_on_submit=True):
                    _nc1, _nc2 = st.columns([4, 1])
                    _note_text = _nc1.text_input(
                        "Note", placeholder="Add a note or highlight...",
                        label_visibility="collapsed", key=f"nt_{book['id']}",
                    )
                    _note_pg = _nc2.number_input(
                        "Pg", min_value=0, value=cur,
                        label_visibility="collapsed", key=f"np_{book['id']}",
                    )
                    if st.form_submit_button("Add Note"):
                        if _note_text.strip():
                            insert_row("book_notes", {
                                "book_id": int(book["id"]),
                                "content": _note_text.strip(),
                                "page_number": _note_pg if _note_pg > 0 else None,
                            })
                            st.rerun()
    st.divider()

# --- Stats ---
completed = df[df["status"] == "completed"] if not df.empty else pd.DataFrame()
want = df[df["status"] == "want_to_read"] if not df.empty else pd.DataFrame()

if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reading", len(reading))
    m2.metric("Completed", len(completed))
    m3.metric("Want to Read", len(want))

    total_pages_read = 0
    if not completed.empty and "total_pages" in completed.columns:
        total_pages_read += int(completed["total_pages"].dropna().sum())
    if not reading.empty and "current_page" in reading.columns:
        total_pages_read += int(reading["current_page"].dropna().sum())
    m4.metric("Pages Read", f"{total_pages_read:,}" if total_pages_read > 0 else "—")

# --- Completed ---
if not completed.empty:
    with st.expander(f"Completed ({len(completed)})", expanded=True):
        for _, book in completed.sort_values("end_date", ascending=False).iterrows():
            line = book_line(book)
            total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
            if book.get("start_date") and book.get("end_date"):
                s = book["start_date"]
                e = book["end_date"]
                if isinstance(s, str):
                    s = date.fromisoformat(s)
                if isinstance(e, str):
                    e = date.fromisoformat(e)
                days = (e - s).days
                line += f" · {days}d"
                if total > 0 and days > 0:
                    line += f" ({total / days:.0f} pg/day)"
                line += f" · finished {e.strftime('%b %d')}"
            elif book.get("end_date"):
                e = book["end_date"]
                if isinstance(e, str):
                    e = date.fromisoformat(e)
                line += f" · finished {e.strftime('%b %d')}"
            st.markdown(line)

# --- Want to Read ---
if not want.empty:
    with st.expander(f"Want to Read ({len(want)})"):
        for _, book in want.iterrows():
            wc1, wc2 = st.columns([6, 1])
            line = book_line(book)
            wc1.markdown(line)
            if wc2.button("Start", key=f"start_{book['id']}"):
                update_row("books", int(book["id"]), {
                    "status": "reading",
                    "start_date": today.isoformat(),
                    "current_page": 0,
                })
                st.rerun()

# --- Notes & Highlights ---
if _notes_data is not None:
    if _notes_data:
        with st.expander(f"Notes & Highlights ({len(_notes_data)})"):
            _notes_by_book = {}
            for _n in _notes_data:
                _notes_by_book.setdefault(_n["book_id"], []).append(_n)

            for _bid, _bnotes in _notes_by_book.items():
                _brow = df[df["id"] == _bid] if not df.empty else pd.DataFrame()
                _btitle = _brow.iloc[0]["title"] if not _brow.empty else f"Book #{_bid}"
                st.markdown(f"**{_btitle}**")
                for _note in sorted(_bnotes, key=lambda n: n.get("created_at", ""), reverse=True):
                    _pg = f" · p.{_note['page_number']}" if _note.get("page_number") else ""
                    _nc1, _nc2 = st.columns([8, 1])
                    _nc1.markdown(f"> {_note['content']}{_pg}")
                    _ck = f"confirm_del_note_{_note['id']}"
                    if st.session_state.get(_ck):
                        with _nc2:
                            _yc, _xc = st.columns(2)
                            if _yc.button("Yes", key=f"yes_note_{_note['id']}"):
                                delete_row("book_notes", _note["id"])
                                st.session_state.pop(_ck, None)
                                st.rerun()
                            if _xc.button("No", key=f"no_note_{_note['id']}"):
                                st.session_state.pop(_ck, None)
                                st.rerun()
                    else:
                        if _nc2.button("Del", key=f"del_note_{_note['id']}"):
                            st.session_state[_ck] = True
                            st.rerun()
else:
    st.info("Add a `book_notes` table to save highlights while reading:")
    st.code(
        "create table book_notes (\n"
        "    id bigint generated by default as identity primary key,\n"
        "    book_id bigint not null,\n"
        "    content text not null,\n"
        "    page_number integer,\n"
        "    created_at timestamptz default now()\n"
        ");",
        language="sql",
    )

st.divider()

# --- Add Book ---
st.subheader("Add Book")
with st.form("add_book"):
    fc1, fc2 = st.columns(2)
    new_title = fc1.text_input("Title")
    new_author = fc2.text_input("Author")
    fc3, fc4, fc5, fc6 = st.columns(4)
    new_status = fc3.selectbox(
        "Status",
        list(STATUS_LABELS.keys()),
        format_func=lambda x: STATUS_LABELS[x],
    )
    new_genre = fc4.text_input("Genre", placeholder="e.g., Fiction, Self-help, CS")
    new_pages = fc5.number_input("Total Pages", min_value=0, max_value=9999, value=0, help="0 = unknown")
    new_year = fc6.number_input("Year Published", min_value=0, max_value=2030, value=0, help="0 = unknown")
    new_notes = st.text_input("Notes (optional)")

    if st.form_submit_button("Add"):
        if new_title.strip():
            row = {
                "title": new_title.strip(),
                "author": new_author.strip() or None,
                "status": new_status,
                "genre": new_genre.strip() or None,
                "total_pages": new_pages if new_pages > 0 else None,
                "current_page": 0,
                "year_published": new_year if new_year > 0 else None,
                "notes": new_notes.strip() or None,
            }
            if new_status == "reading":
                row["start_date"] = today.isoformat()
            elif new_status == "completed":
                row["start_date"] = today.isoformat()
                row["end_date"] = today.isoformat()
                if new_pages > 0:
                    row["current_page"] = new_pages
            insert_row("books", row)
            st.success(f"Added '{new_title.strip()}'")
            st.rerun()
        else:
            st.error("Title is required.")

# --- Manage Books ---
if not df.empty:
    with st.expander("Manage Books"):
        for _, book in df.iterrows():
            mc1, mc2, mc3, mc4 = st.columns([5, 1, 1, 1])
            status_label = STATUS_LABELS.get(book["status"], book["status"])
            cap_line = f"{book['title']}"
            if book.get("author"):
                cap_line += f" — {book['author']}"
            yr = int(book["year_published"]) if pd.notna(book.get("year_published")) else 0
            if yr > 0:
                cap_line += f" ({yr})"
            cap_line += f" · {status_label}"
            mc1.caption(cap_line)

            if book["status"] != "reading":
                if mc2.button("Read", key=f"mgmt_read_{book['id']}"):
                    update_row("books", int(book["id"]), {
                        "status": "reading",
                        "start_date": today.isoformat(),
                        "current_page": 0,
                    })
                    st.rerun()
            elif book["status"] == "reading":
                if mc2.button("Done", key=f"mgmt_done_{book['id']}"):
                    updates = {"status": "completed", "end_date": today.isoformat()}
                    total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
                    if total > 0:
                        updates["current_page"] = total
                    update_row("books", int(book["id"]), updates)
                    st.rerun()

            if mc3.button("Edit", key=f"mgmt_edit_{book['id']}"):
                st.session_state[f"editing_book_{book['id']}"] = True
                st.rerun()

            ck = f"confirm_del_book_{book['id']}"
            if st.session_state.get(ck):
                with mc4:
                    st.warning("Sure?")
                    yc, nc = st.columns(2)
                    if yc.button("Yes", key=f"yes_book_{book['id']}"):
                        delete_row("books", book["id"])
                        st.session_state.pop(ck, None)
                        st.rerun()
                    if nc.button("No", key=f"no_book_{book['id']}"):
                        st.session_state.pop(ck, None)
                        st.rerun()
            else:
                if mc4.button("Del", key=f"del_book_{book['id']}"):
                    st.session_state[ck] = True
                    st.rerun()

            if st.session_state.get(f"editing_book_{book['id']}"):
                with st.form(f"edit_book_{book['id']}"):
                    ec1, ec2 = st.columns(2)
                    ed_title = ec1.text_input("Title", value=book["title"], key=f"edt_{book['id']}")
                    ed_author = ec2.text_input("Author", value=book.get("author") or "", key=f"eda_{book['id']}")
                    ec3, ec4, ec5 = st.columns(3)
                    ed_genre = ec3.text_input("Genre", value=book.get("genre") or "", key=f"edg_{book['id']}")
                    ed_pages = ec4.number_input(
                        "Total Pages", min_value=0, max_value=9999,
                        value=int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0,
                        key=f"edp_{book['id']}",
                    )
                    ed_year = ec5.number_input(
                        "Year Published", min_value=0, max_value=2030,
                        value=int(book["year_published"]) if pd.notna(book.get("year_published")) else 0,
                        key=f"edy_{book['id']}",
                    )
                    ed_notes = st.text_input("Notes", value=book.get("notes") or "", key=f"edn_{book['id']}")

                    if st.form_submit_button("Save"):
                        update_row("books", int(book["id"]), {
                            "title": ed_title.strip(),
                            "author": ed_author.strip() or None,
                            "genre": ed_genre.strip() or None,
                            "total_pages": ed_pages if ed_pages > 0 else None,
                            "year_published": ed_year if ed_year > 0 else None,
                            "notes": ed_notes.strip() or None,
                        })
                        st.session_state.pop(f"editing_book_{book['id']}", None)
                        st.rerun()

    # --- Analytics ---
    if not completed.empty and len(completed) >= 2:
        with st.expander("Analytics"):
            if "genre" in completed.columns:
                genre_counts = completed["genre"].dropna().value_counts()
                if not genre_counts.empty:
                    st.markdown("**Books by Genre**")
                    st.bar_chart(genre_counts)

            if "year_published" in completed.columns:
                year_data = completed[completed["year_published"].notna()]
                if not year_data.empty:
                    st.markdown("**Books by Decade**")
                    year_data = year_data.copy()
                    year_data["decade"] = (year_data["year_published"] // 10 * 10).astype(int).astype(str) + "s"
                    decade_counts = year_data["decade"].value_counts().sort_index()
                    st.bar_chart(decade_counts)

                    oldest = year_data.loc[year_data["year_published"].idxmin()]
                    newest = year_data.loc[year_data["year_published"].idxmax()]
                    y1, y2 = st.columns(2)
                    y1.metric("Oldest Read", f"{oldest['title']} ({int(oldest['year_published'])})")
                    y2.metric("Newest Read", f"{newest['title']} ({int(newest['year_published'])})")

            if "total_pages" in completed.columns:
                pages_data = completed[completed["total_pages"].notna()]
                if not pages_data.empty:
                    st.markdown("**Pages by Book**")
                    pages_chart = pages_data.set_index("title")["total_pages"].sort_values(ascending=False)
                    st.bar_chart(pages_chart)
