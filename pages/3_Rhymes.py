import streamlit as st
import pandas as pd
from db import fetch_all, insert_row, insert_rows

st.set_page_config(page_title="Rhymes", layout="wide")
st.title("Rhyme Reference")

data = fetch_all("rhymes", order_col="rhyme_group")
df = pd.DataFrame(data)

if df.empty:
    st.info("No rhyme data loaded yet. Run upload_data.py to populate.")

search = st.text_input("Search for a word")

if not df.empty:
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

add_single, add_bulk = st.tabs(["Add to Group", "Bulk Add Groups"])

with add_single:
    col1, col2 = st.columns(2)

    with col1:
        with st.form("add_rhyme_group"):
            st.subheader("New Group")
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

    with col2:
        if not df.empty:
            with st.form("add_word"):
                st.subheader("Add to Existing Group")
                groups_dict = {}
                for gid, gdf in df.groupby("rhyme_group"):
                    preview = ", ".join(gdf["word"].tolist()[:4])
                    groups_dict[f"Group {gid}: {preview}"] = gid
                sel_group = st.selectbox("Group", list(groups_dict.keys()))
                new_word = st.text_input("New word")
                if st.form_submit_button("Add Word"):
                    if new_word:
                        insert_row("rhymes", {
                            "word": new_word.strip(),
                            "rhyme_group": groups_dict[sel_group],
                        })
                        st.success(f"Added '{new_word.strip()}'")
                        st.rerun()

with add_bulk:
    st.markdown("Paste one group per line. Words separated by commas.")
    st.code("cat, hat, bat, mat\ndog, log, fog\nrun, fun, sun, bun")
    bulk_text = st.text_area("Paste groups here", height=200, key="bulk_rhymes")

    if st.button("Preview", key="preview_rhymes"):
        if bulk_text.strip():
            preview_groups = []
            for line in bulk_text.strip().split("\n"):
                words = [w.strip() for w in line.split(",") if w.strip()]
                if words:
                    preview_groups.append(words)
            if preview_groups:
                for i, g in enumerate(preview_groups):
                    st.markdown(f"**Group:** {' / '.join(g)}")
                st.session_state["bulk_rhymes_parsed"] = preview_groups

    if st.button("Upload", key="upload_rhymes"):
        parsed = st.session_state.get("bulk_rhymes_parsed", [])
        if not parsed:
            st.error("Preview first to validate the data.")
        else:
            next_id = int(df["rhyme_group"].max()) + 1 if not df.empty else 1
            db_rows = []
            for group_words in parsed:
                for word in group_words:
                    db_rows.append({"word": word, "rhyme_group": next_id})
                next_id += 1
            if db_rows:
                insert_rows("rhymes", db_rows)
                st.success(f"Uploaded {len(parsed)} groups ({len(db_rows)} words).")
                st.session_state.pop("bulk_rhymes_parsed", None)
                st.rerun()
