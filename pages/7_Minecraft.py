import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row, update_row
from auth import require_login
from ui_helpers import save_edits

st.set_page_config(page_title="Minecraft", layout="wide")
require_login()

TABLE = "minecraft_coords"
SEED = "7338286372832099621"
CHUNKBASE_URL = "https://www.chunkbase.com/apps/seed-map#seed=7338286372832099621&platform=bedrock_26_0&dimension=overworld&x=895&z=-7&zoom=0.927"

try:
    data = fetch_all(TABLE, order_col="created_at")
except Exception:
    data = []
df = pd.DataFrame(data)

# --- Coordinates ---
coords_df = df[df["label"] != "__seed__"] if not df.empty else pd.DataFrame()

DIM_COLORS = {"overworld": "#4CAF50", "nether": "#F44336", "end": "#9C27B0"}
DIM_BG = {"overworld": "rgba(76,175,80,0.08)", "nether": "rgba(244,67,54,0.08)", "end": "rgba(156,39,176,0.08)"}
DIM_ICONS = {"overworld": "\U0001F333", "nether": "\U0001F525", "end": "⭐"}

st.subheader("Important Coordinates")

if coords_df.empty:
    st.info("No coordinates saved yet. Add one below.")
else:
    st.markdown("""
    <style>
    .mc-card {
        border-left: 4px solid;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .mc-card .mc-label {
        font-size: 1.1rem;
        font-weight: 700;
        min-width: 140px;
    }
    .mc-card .mc-coords {
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        opacity: 0.9;
        min-width: 120px;
    }
    .mc-card .mc-dim {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.7;
        min-width: 90px;
    }
    .mc-card .mc-convert {
        font-size: 0.8rem;
        opacity: 0.5;
        font-style: italic;
        min-width: 140px;
    }
    </style>
    """, unsafe_allow_html=True)

    for dim_name in ["overworld", "nether", "end"]:
        dim_rows = coords_df[coords_df["dimension"].str.lower() == dim_name] if not coords_df.empty else pd.DataFrame()
        if dim_rows.empty:
            continue
        for _, row in dim_rows.iterrows():
            dim = dim_name
            color = DIM_COLORS[dim]
            bg = DIM_BG[dim]
            icon = DIM_ICONS[dim]

            convert = ""
            try:
                ix, iz = int(float(row["x"])), int(float(row["z"]))
                if dim == "nether":
                    convert = f"Overworld: ~{ix * 8}, ~{iz * 8}"
                elif dim == "overworld":
                    convert = f"Nether: ~{round(ix / 8)}, ~{round(iz / 8)}"
            except (ValueError, TypeError):
                pass

            card_col, btn_col = st.columns([12, 1])
            card_col.markdown(
                f'<div class="mc-card" style="border-color:{color};background:{bg};">'
                f'<span class="mc-label" style="color:{color};">{icon} {row["label"]}</span>'
                f'<span class="mc-coords">X: {row["x"]}  Z: {row["z"]}</span>'
                f'<span class="mc-dim">{dim.title()}</span>'
                f'<span class="mc-convert">{convert}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if btn_col.button("\U0001F5D1", key=f"del_{row['id']}"):
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

st.divider()

st.markdown(
    f'<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
    f'<span style="opacity:0.6;font-size:0.85rem;">Seed: <code>{SEED}</code></span>'
    f'<a href="{CHUNKBASE_URL}" target="_blank" style="'
    'display:inline-flex;align-items:center;gap:6px;'
    'background:linear-gradient(135deg,#2d7d32,#66bb6a);'
    'color:white;padding:6px 16px;border-radius:6px;'
    'text-decoration:none;font-weight:600;font-size:0.85rem;'
    '">'
    '\U0001F5FA Chunkbase'
    '</a>'
    '</div>',
    unsafe_allow_html=True,
)
