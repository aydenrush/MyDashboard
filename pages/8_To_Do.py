import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login

st.set_page_config(page_title="To Do", layout="wide")
require_login()

from constants import PRIORITY_COLORS

TABLE = "todos"

try:
    data = fetch_all(TABLE, order_col="created_at")
except Exception:
    data = []
df = pd.DataFrame(data)

active = df[df["completed"] == False] if not df.empty else pd.DataFrame()

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
            _editing = st.session_state.get(f"edit_{row['id']}", False)

            if _editing:
                with st.form(key=f"editform_{row['id']}"):
                    ec1, ec2 = st.columns([8, 2])
                    _new_task = ec1.text_input("Task", value=row["task"], label_visibility="collapsed")
                    _new_pri = ec2.selectbox(
                        "Priority", ["high", "medium", "low"],
                        index=["high", "medium", "low"].index(row.get("priority", "medium")),
                        label_visibility="collapsed",
                    )
                    sc1, sc2 = st.columns(2)
                    if sc1.form_submit_button("Save"):
                        update_row(TABLE, int(row["id"]), {"task": _new_task.strip(), "priority": _new_pri})
                        st.session_state[f"edit_{row['id']}"] = False
                        st.rerun()
                    if sc2.form_submit_button("Cancel"):
                        st.session_state[f"edit_{row['id']}"] = False
                        st.rerun()
            else:
                c1, c2, c3, c4 = st.columns([1, 8, 1, 1])
                if c1.button("✅", key=f"done_{row['id']}"):
                    delete_row(TABLE, int(row["id"]))
                    st.rerun()
                c2.markdown(
                    f'<span style="border-left:3px solid {color};padding-left:8px;">'
                    f'{row["task"]}</span>',
                    unsafe_allow_html=True,
                )
                if c3.button("✏️", key=f"ed_{row['id']}"):
                    st.session_state[f"edit_{row['id']}"] = True
                    st.rerun()
                c4.code(row["task"], language=None)
