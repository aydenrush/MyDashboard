import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login

st.set_page_config(page_title="Minecraft", layout="wide")
require_login()

st.title("Minecraft")

TABLE = "minecraft_coords"

try:
    data = fetch_all(TABLE, order_col="created_at")
except Exception:
    data = []
df = pd.DataFrame(data)

# --- World Seed ---
seed_rows = df[df["label"] == "__seed__"] if not df.empty else pd.DataFrame()
current_seed = seed_rows.iloc[0]["x"] if not seed_rows.empty else ""

with st.expander("World Seed", expanded=bool(current_seed)):
    if current_seed:
        st.code(current_seed, language=None)
    with st.form("seed_form"):
        new_seed = st.text_input("Seed", value=current_seed)
        if st.form_submit_button("Save Seed"):
            if seed_rows.empty:
                insert_row(TABLE, {"label": "__seed__", "x": new_seed.strip(), "z": "", "dimension": ""})
            else:
                update_row(TABLE, int(seed_rows.iloc[0]["id"]), {"x": new_seed.strip()})
            st.rerun()

st.divider()

# --- Coordinates ---
coords_df = df[df["label"] != "__seed__"] if not df.empty else pd.DataFrame()

DIM_COLORS = {"overworld": "#4CAF50", "nether": "#F44336", "end": "#9C27B0"}

st.subheader("Important Coordinates")

if coords_df.empty:
    st.info("No coordinates saved yet. Add one below.")
else:
    for _, row in coords_df.iterrows():
        dim = (row.get("dimension") or "overworld").lower()
        color = DIM_COLORS.get(dim, "#888")
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.markdown(
            f'<span style="color:{color};font-weight:600;">{row["label"]}</span>',
            unsafe_allow_html=True,
        )
        c2.caption(f"X: {row['x']}  Z: {row['z']}")
        c3.caption(dim.title())
        if c4.button("X", key=f"del_{row['id']}"):
            delete_row(TABLE, row["id"])
            st.rerun()

st.divider()

with st.form("add_coord"):
    st.markdown("**Add Coordinate**")
    ac1, ac2, ac3, ac4 = st.columns([3, 2, 2, 2])
    label = ac1.text_input("Label")
    x = ac2.text_input("X")
    z = ac3.text_input("Z")
    dimension = ac4.selectbox("Dimension", ["Overworld", "Nether", "End"])
    if st.form_submit_button("Add"):
        if label.strip():
            insert_row(TABLE, {
                "label": label.strip(),
                "x": x.strip(),
                "z": z.strip(),
                "dimension": dimension.lower(),
            })
            st.rerun()
        else:
            st.error("Label is required.")
