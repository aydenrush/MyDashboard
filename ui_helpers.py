import streamlit as st
import pandas as pd
from db import update_row, delete_row


def save_edits(table, edit_df, edited_df, col_mapping):
    reverse = {v: k for k, v in col_mapping.items()}
    changed = 0
    for row_id in edited_df.index:
        orig = edit_df[edit_df["id"] == row_id]
        if orig.empty:
            continue
        orig_row = orig.iloc[0]
        updates = {}
        for disp_col in edited_df.columns:
            db_col = reverse.get(disp_col, disp_col)
            new_val = edited_df.loc[row_id, disp_col]
            old_val = orig_row.get(disp_col)
            if str(new_val) != str(old_val):
                updates[db_col] = new_val if pd.notna(new_val) and str(new_val).strip() else None
        if updates:
            update_row(table, int(row_id), updates)
            changed += 1
    if changed:
        st.success(f"Saved {changed} change(s).")
    else:
        st.info("No changes detected.")
    st.rerun()


def delete_with_confirm(table, row_id, label, key_prefix):
    confirm_key = f"confirm_del_{key_prefix}_{row_id}"
    if st.session_state.get(confirm_key):
        st.warning(f"Delete **{label}**?")
        yc, nc = st.columns(2)
        if yc.button("Yes", key=f"yes_{key_prefix}_{row_id}"):
            delete_row(table, row_id)
            st.session_state.pop(confirm_key, None)
            st.rerun()
        if nc.button("No", key=f"no_{key_prefix}_{row_id}"):
            st.session_state.pop(confirm_key, None)
            st.rerun()
        return True
    return False


def delete_button(table, row_id, label, key_prefix):
    confirm_key = f"confirm_del_{key_prefix}_{row_id}"
    dc1, dc2 = st.columns([6, 1])
    dc1.caption(label)
    if st.session_state.get(confirm_key):
        with dc2:
            st.warning("Sure?")
            yc, nc = st.columns(2)
            if yc.button("Yes", key=f"yes_{key_prefix}_{row_id}"):
                delete_row(table, row_id)
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if nc.button("No", key=f"no_{key_prefix}_{row_id}"):
                st.session_state.pop(confirm_key, None)
                st.rerun()
    else:
        if dc2.button("Delete", key=f"del_{key_prefix}_{row_id}"):
            st.session_state[confirm_key] = True
            st.rerun()
