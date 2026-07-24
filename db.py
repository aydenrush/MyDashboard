import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def fetch_all(table, order_col=None, filters=None):
    q = get_supabase().table(table).select("*")
    if filters:
        for col, val in filters.items():
            if isinstance(val, list):
                q = q.in_(col, val)
            else:
                q = q.eq(col, val)
    if order_col:
        q = q.order(order_col)
    rows = []
    offset = 0
    while True:
        batch = q.range(offset, offset + 999).execute().data
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def insert_row(table, data):
    return get_supabase().table(table).insert(data).execute()


def insert_rows(table, rows):
    for i in range(0, len(rows), 500):
        get_supabase().table(table).insert(rows[i:i+500]).execute()


def delete_row(table, row_id):
    return get_supabase().table(table).delete().eq("id", row_id).execute()


def upsert_config(game, franchise, primary_team):
    get_supabase().table("franchise_config").upsert(
        {"game": game, "franchise": franchise, "primary_team": primary_team},
        on_conflict="game,franchise",
    ).execute()


def get_config(game, franchise):
    rows = get_supabase().table("franchise_config").select("*").eq(
        "game", game
    ).eq("franchise", franchise).execute().data
    return rows[0] if rows else None
