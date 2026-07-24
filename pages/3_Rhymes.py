import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, delete_row

st.set_page_config(page_title="Rhymes", layout="wide")
st.title("Rhyme Reference")

data = fetch_all("rhymes", order_col="rhyme_group")
df = pd.DataFrame(data)

if df.empty:
    st.info("No rhyme data loaded yet. Run upload_data.py to populate.")
    st.stop()

search = st.text_input("Search for a word")

groups = df.groupby("rhyme_group")
for group_id, group_df in groups:
    words = group_df["word"].tolist()
    if search and not any(search.lower() in w.lower() for w in words):
        continue
    highlighted = []
    for w in words:
        if search and search.lower() in w.lower():
            highlighted.append(f"**{w}**")
        else:
            highlighted.append(w)
    st.markdown(f"**Group {group_id}:** {' / '.join(highlighted)}")

st.divider()
with st.expander("Add Rhyme Group"):
    with st.form("add_rhyme"):
        new_words = st.text_input("Words (comma-separated)", placeholder="cat, hat, bat, mat")
        next_group = int(df["rhyme_group"].max()) + 1 if not df.empty else 1
        if st.form_submit_button("Add Group"):
            if new_words:
                for word in new_words.split(","):
                    word = word.strip()
                    if word:
                        insert_row("rhymes", {"word": word, "rhyme_group": next_group})
                st.success("Rhyme group added.")
                st.rerun()

with st.expander("Add Word to Existing Group"):
    with st.form("add_word"):
        group_options = {}
        for gid, gdf in groups:
            preview = ", ".join(gdf["word"].tolist()[:4])
            group_options[f"Group {gid}: {preview}"] = gid
        sel_group = st.selectbox("Group", list(group_options.keys()))
        new_word = st.text_input("New word")
        if st.form_submit_button("Add Word"):
            if new_word:
                insert_row("rhymes", {
                    "word": new_word.strip(),
                    "rhyme_group": group_options[sel_group],
                })
                st.success(f"Added '{new_word.strip()}'")
                st.rerun()
