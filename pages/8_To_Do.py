import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login

st.set_page_config(page_title="To Do", layout="wide")
require_login()

TABLE = "todos"
PRIORITY_COLORS = {"high": "#F44336", "medium": "#FF9800", "low": "#4CAF50"}

try:
    data = fetch_all(TABLE, order_col="created_at")
except Exception:
    data = []
df = pd.DataFrame(data)

active = df[df["completed"] == False] if not df.empty else pd.DataFrame()
done = df[df["completed"] == True] if not df.empty else pd.DataFrame()

# --- Add task ---
with st.form("add_todo", clear_on_submit=True):
    tc1, tc2, tc3 = st.columns([6, 2, 1])
    task = tc1.text_input("Task", placeholder="What needs doing?", label_visibility="collapsed")
    priority = tc2.selectbox("Priority", ["high", "medium", "low"], index=1, label_visibility="collapsed")
    submitted = tc3.form_submit_button("Add")
    if submitted and task.strip():
        insert_row(TABLE, {"task": task.strip(), "priority": priority, "completed": False})
        st.rerun()

st.divider()

# --- Active tasks ---
if active.empty:
    st.info("Nothing to do. Nice.")
else:
    for priority in ["high", "medium", "low"]:
        group = active[active["priority"] == priority] if "priority" in active.columns else pd.DataFrame()
        if group.empty:
            continue
        for _, row in group.iterrows():
            color = PRIORITY_COLORS.get(row.get("priority", "medium"), "#FF9800")
            c1, c2, c3 = st.columns([1, 10, 1])
            if c1.button("✅", key=f"done_{row['id']}"):
                update_row(TABLE, int(row["id"]), {"completed": True})
                st.rerun()
            c2.markdown(
                f'<span style="border-left:3px solid {color};padding-left:8px;">'
                f'{row["task"]}</span>',
                unsafe_allow_html=True,
            )
            if c3.button("\U0001F5D1", key=f"del_{row['id']}"):
                delete_row(TABLE, row["id"])
                st.rerun()

# --- Completed ---
if not done.empty:
    with st.expander(f"Completed ({len(done)})"):
        for _, row in done.iterrows():
            c1, c2, c3 = st.columns([1, 10, 1])
            if c1.button("↩", key=f"undo_{row['id']}"):
                update_row(TABLE, int(row["id"]), {"completed": False})
                st.rerun()
            c2.markdown(f"~~{row['task']}~~")
            if c3.button("\U0001F5D1", key=f"deld_{row['id']}"):
                delete_row(TABLE, row["id"])
                st.rerun()
