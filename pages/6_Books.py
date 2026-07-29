import streamlit as st
import pandas as pd
from datetime import date
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

STATUS_LABELS = {
    "reading": "Currently Reading",
    "completed": "Completed",
    "want_to_read": "Want to Read",
}

today = date.today()

# --- Currently Reading ---
reading = df[df["status"] == "reading"] if not df.empty else pd.DataFrame()

if not reading.empty:
    st.subheader("Currently Reading")
    for _, book in reading.iterrows():
        title_line = f"**{book['title']}**"
        if book.get("author"):
            title_line += f" — {book['author']}"
        if book.get("genre"):
            title_line += f" · {book['genre']}"

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
            line = f"**{book['title']}**"
            if book.get("author"):
                line += f" — {book['author']}"
            if book.get("genre"):
                line += f" · {book['genre']}"
            total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
            if total > 0:
                line += f" · {total}p"
            if book.get("rating") and pd.notna(book["rating"]):
                stars = int(book["rating"])
                line += f" · {'*' * stars}"
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
            line = f"**{book['title']}**"
            if book.get("author"):
                line += f" — {book['author']}"
            if book.get("genre"):
                line += f" · {book['genre']}"
            total = int(book["total_pages"]) if pd.notna(book.get("total_pages")) else 0
            if total > 0:
                line += f" · {total}p"
            wc1.markdown(line)
            if wc2.button("Start", key=f"start_{book['id']}"):
                update_row("books", int(book["id"]), {
                    "status": "reading",
                    "start_date": today.isoformat(),
                    "current_page": 0,
                })
                st.rerun()

st.divider()

# --- Add Book ---
st.subheader("Add Book")
with st.form("add_book"):
    fc1, fc2 = st.columns(2)
    new_title = fc1.text_input("Title")
    new_author = fc2.text_input("Author")
    fc3, fc4, fc5 = st.columns(3)
    new_status = fc3.selectbox(
        "Status",
        list(STATUS_LABELS.keys()),
        format_func=lambda x: STATUS_LABELS[x],
    )
    new_genre = fc4.text_input("Genre", placeholder="e.g., Fiction, Self-help, CS")
    new_pages = fc5.number_input("Total Pages", min_value=0, max_value=9999, value=0, help="0 = unknown")
    fc6, fc7 = st.columns(2)
    new_rating = fc6.slider("Rating", 0, 5, 0, help="0 = no rating")
    new_notes = fc7.text_input("Notes (optional)")

    if st.form_submit_button("Add"):
        if new_title.strip():
            row = {
                "title": new_title.strip(),
                "author": new_author.strip() or None,
                "status": new_status,
                "genre": new_genre.strip() or None,
                "total_pages": new_pages if new_pages > 0 else None,
                "current_page": 0,
                "rating": new_rating if new_rating > 0 else None,
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
            mc1.caption(f"{book['title']} — {status_label}")

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
                    ed_rating = ec5.slider("Rating", 0, 5, int(book["rating"]) if pd.notna(book.get("rating")) else 0, key=f"edr_{book['id']}")
                    ed_notes = st.text_input("Notes", value=book.get("notes") or "", key=f"edn_{book['id']}")

                    if st.form_submit_button("Save"):
                        update_row("books", int(book["id"]), {
                            "title": ed_title.strip(),
                            "author": ed_author.strip() or None,
                            "genre": ed_genre.strip() or None,
                            "total_pages": ed_pages if ed_pages > 0 else None,
                            "rating": ed_rating if ed_rating > 0 else None,
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

            rated = completed[completed["rating"].notna()]
            if not rated.empty:
                st.markdown("**Rating Distribution**")
                rating_dist = rated["rating"].value_counts().sort_index()
                st.bar_chart(rating_dist)

            if "total_pages" in completed.columns:
                pages_data = completed[completed["total_pages"].notna()]
                if not pages_data.empty:
                    st.markdown("**Pages by Book**")
                    pages_chart = pages_data.set_index("title")["total_pages"].sort_values(ascending=False)
                    st.bar_chart(pages_chart)
