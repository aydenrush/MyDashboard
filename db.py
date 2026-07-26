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


def update_row(table, row_id, data):
    return get_supabase().table(table).update(data).eq("id", row_id).execute()


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


_GAME_DEFAULTS = {
    "cfb": {"CFB 25": "cfb25", "CFB 26": "cfb26", "CFB 27": "cfb27"},
    "madden": {"Madden 24": "m24", "Madden 25": "m25", "Madden 26": "m26"},
}


def fetch_games(game_type):
    try:
        rows = get_supabase().table("game_registry").select("*").eq(
            "game_type", game_type
        ).order("display_name").execute().data
        if rows:
            return {r["display_name"]: r["table_prefix"] for r in rows}
    except Exception:
        pass
    return dict(_GAME_DEFAULTS.get(game_type, {}))


def add_game(game_type, display_name, table_prefix):
    return get_supabase().table("game_registry").insert({
        "game_type": game_type,
        "display_name": display_name,
        "table_prefix": table_prefix,
    }).execute()


def fetch_custom_colors():
    try:
        return get_supabase().table("custom_colors").select("*").execute().data
    except Exception:
        return []


def save_custom_color(color_type, key, primary_color, secondary_color, display_name=None):
    data = {
        "color_type": color_type,
        "key": key,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "display_name": display_name,
    }
    return get_supabase().table("custom_colors").upsert(
        data, on_conflict="color_type,key",
    ).execute()
