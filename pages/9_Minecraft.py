import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login
from ui_helpers import save_edits
from mc_biomes import get_biome, find_nearest_biome, list_biomes

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

st.link_button("Open Seed Map (Chunkbase)", "https://www.chunkbase.com/apps/seed-map#seed=7338286372832099621&platform=bedrock_26_0&dimension=overworld&x=895&z=-7&zoom=0.927")

st.divider()

# --- Biome Finder ---
st.subheader("Biome Finder")
st.caption("Find the nearest biome from any coordinate")

bf1, bf2, bf3 = st.columns([3, 2, 2])
target_biome = bf1.selectbox("Find biome", list_biomes())
start_x = bf2.number_input("From X", value=0, step=100)
start_z = bf3.number_input("From Z", value=0, step=100)

bc1, bc2 = st.columns([1, 3])
search_radius = bc1.select_slider("Search radius", [2000, 5000, 10000, 20000], value=5000)

if bc2.button("Search", type="primary"):
    with st.spinner(f"Searching for {target_biome}..."):
        result = find_nearest_biome(target_biome, start_x, start_z, max_radius=search_radius, step=64)
    if result:
        x, z, dist = result
        st.success(f"**{target_biome}** found at **X: {x}  Z: {z}** — {dist:.0f} blocks away")
        if st.button(f"Save this coordinate", key="save_biome_result"):
            insert_row(TABLE, {
                "label": target_biome,
                "x": str(x),
                "z": str(z),
                "dimension": "overworld",
            })
            st.rerun()
    else:
        st.warning(f"No {target_biome} found within {search_radius} blocks.")

with st.expander("What biome is here?"):
    wh1, wh2 = st.columns(2)
    check_x = wh1.number_input("X", value=0, step=100, key="check_x")
    check_z = wh2.number_input("Z", value=0, step=100, key="check_z")
    if st.button("Check"):
        biome = get_biome(check_x, check_z)
        st.info(f"**{biome}** at X: {check_x}  Z: {check_z}")

st.caption("Results are approximate — noise parameters are estimated, not exact Bedrock values.")

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

    with st.expander("Edit Coordinates"):
        edit_df = coords_df[["id", "label", "x", "z", "dimension"]].copy()
        edit_df.rename(columns={"label": "Label", "x": "X", "z": "Z", "dimension": "Dimension"}, inplace=True)
        edited = st.data_editor(
            edit_df.set_index("id"),
            use_container_width=True,
            key="edit_coords",
        )
        if st.button("Save Changes", key="save_coords"):
            save_edits(TABLE, edit_df, edited, {"label": "Label", "x": "X", "z": "Z", "dimension": "Dimension"})

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
