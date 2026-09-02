import streamlit as st
import pandas as pd
import re
import pronouncing
import pyphen
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from db import fetch_all, insert_row, insert_rows, update_row, delete_row
from auth import require_login

st.set_page_config(page_title="Lyric Lab", layout="wide")
require_login()

st.title("Lyric Lab")

try:
    rhyme_data = fetch_all("rhymes", order_col="rhyme_group")
except Exception:
    rhyme_data = []
rhyme_df = pd.DataFrame(rhyme_data)

try:
    lyrics_data = fetch_all("lyrics", order_col="updated_at")
except Exception:
    lyrics_data = None
lyrics_df = pd.DataFrame(lyrics_data) if lyrics_data else pd.DataFrame()

today = datetime.now(ZoneInfo("America/Indiana/Indianapolis"))

STATUS_LABELS = {"draft": "Draft", "in_progress": "In Progress", "finished": "Finished"}
SCHEME_COLORS = [
    "#F44336", "#2196F3", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#FF5722", "#8BC34A",
    "#E91E63", "#3F51B5", "#CDDC39", "#795548",
]


_hyph = pyphen.Pyphen(lang='en_US')


def _syllabify(text):
    return re.sub(r"[a-zA-Z']+", lambda m: _hyph.inserted(m.group()).replace('-', '·'), text)


def _build_syllable_map(bars):
    occs = []
    for bi, bar in enumerate(bars):
        for m in re.finditer(r"[a-zA-Z']+", bar):
            word = m.group()
            w_clean = word.lower().strip("'")
            if not w_clean or len(w_clean) <= 1 or w_clean in _STOP_WORDS:
                continue
            syls = _hyph.inserted(word).split('-')
            phones = pronouncing.phones_for_word(w_clean)
            if not phones:
                continue
            vowels = []
            for ph in phones[0].split():
                if any(c.isdigit() for c in ph):
                    vowels.append((re.sub(r'\d', '', ph), '1' in ph or '2' in ph))
            pos = m.start()
            for si, syl in enumerate(syls):
                se = pos + len(syl)
                if si < len(vowels):
                    vowel, stressed = vowels[si]
                    if stressed and len(syl) > 1:
                        occs.append((bi, pos, se, syl.lower(), vowel))
                pos = se
    by_vowel = defaultdict(list)
    for occ in occs:
        by_vowel[occ[4]].append(occ)
    raw = []
    for members in by_vowel.values():
        unique = set(m[3] for m in members)
        bars_hit = set(m[0] for m in members)
        if len(unique) >= 3 and len(bars_hit) >= 2:
            raw.append(set(members))
    smap = {}
    for ci, cluster in enumerate(raw):
        for bi, s, e, text, vowel in cluster:
            smap[(bi, s, e)] = ci
    return smap


def _render_syl_bar(bar, bar_idx, smap):
    parts = []
    last_end = 0
    for m in re.finditer(r"[a-zA-Z']+", bar):
        if m.start() > last_end:
            parts.append(bar[last_end:m.start()])
        word = m.group()
        syls = _hyph.inserted(word).split('-')
        syl_htmls = []
        pos = m.start()
        for syl in syls:
            se = pos + len(syl)
            key = (bar_idx, pos, se)
            if key in smap:
                clr = SCHEME_COLORS[smap[key] % len(SCHEME_COLORS)]
                syl_htmls.append(f'<span style="color:{clr};font-weight:700;">{syl}</span>')
            else:
                syl_htmls.append(syl)
            pos = se
        parts.append('·'.join(syl_htmls))
        last_end = m.end()
    if last_end < len(bar):
        parts.append(bar[last_end:])
    return ''.join(parts)


# ---------- helpers ----------

def _count_syllables(word):
    word = re.sub(r'[^a-z]', '', word.lower())
    if not word:
        return 0
    phones = pronouncing.phones_for_word(word)
    if phones:
        return pronouncing.syllable_count(phones[0])
    count = 0
    prev_vowel = False
    for ch in word:
        is_v = ch in "aeiouy"
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    if word.endswith("e") and count > 1:
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
        count += 1
    return max(count, 1)


def _line_syllables(line):
    words = re.findall(r"[a-zA-Z']+", line)
    return sum(_count_syllables(w) for w in words)


def _last_word(line):
    words = re.findall(r"[a-zA-Z']+", line)
    return words[-1].lower() if words else ""


def _find_rhymes_db(word, rdf):
    if rdf.empty or not word:
        return []
    matches = rdf[rdf["word"].str.lower() == word.lower()]
    if matches.empty:
        matches = rdf[rdf["word"].str.lower().str.contains(re.escape(word.lower()), na=False)]
    if matches.empty:
        return []
    results = []
    seen = set()
    for _, m in matches.iterrows():
        gid = m["rhyme_group"]
        if gid in seen:
            continue
        seen.add(gid)
        results.extend(
            w for w in rdf[rdf["rhyme_group"] == gid]["word"].tolist()
            if w.lower() != word.lower()
        )
    return results


def _find_rhymes_cmu(word):
    if not word:
        return []
    return pronouncing.rhymes(word.lower())


def _find_rhymes(word, rdf):
    db_rhymes = _find_rhymes_db(word, rdf)
    cmu_rhymes = _find_rhymes_cmu(word)
    seen = {w.lower() for w in db_rhymes}
    combined = list(db_rhymes)
    for w in cmu_rhymes:
        if w.lower() not in seen:
            seen.add(w.lower())
            combined.append(w)
    return combined


def _stressed_vowel(word):
    phones = pronouncing.phones_for_word(word.lower())
    if not phones:
        return None
    for ph in reversed(phones[0].split()):
        if '1' in ph or '2' in ph:
            return re.sub(r'\d', '', ph)
    return None


def _words_rhyme(a, b):
    if a == b:
        return True
    if a in pronouncing.rhymes(b):
        return True
    va, vb = _stressed_vowel(a), _stressed_vowel(b)
    if va and vb and va == vb:
        return True
    return False


def _end_phrase(line, rdf, max_words=4):
    words = re.findall(r"[a-zA-Z']+", line)
    if not words or rdf.empty:
        return words[-1].lower() if words else ""
    for n in range(min(max_words, len(words)), 1, -1):
        phrase = " ".join(w.lower() for w in words[-n:])
        if any(rdf["word"].str.lower() == phrase):
            return phrase
    return words[-1].lower()


def _detect_scheme(lines, rdf):
    end_words = [_end_phrase(l, rdf) for l in lines]
    group_map = {}
    if not rdf.empty:
        for _, row in rdf.iterrows():
            group_map.setdefault(row["word"].lower(), set()).add(row["rhyme_group"])
    next_label = 0
    result = []
    for i, word in enumerate(end_words):
        if not word:
            result.append("-")
            continue
        word_groups = group_map.get(word, set())
        assigned = False
        for j in range(i):
            prev_groups = group_map.get(end_words[j], set())
            if word_groups & prev_groups and word_groups:
                result.append(result[j])
                assigned = True
                break
            if " " not in word and " " not in end_words[j] and _words_rhyme(word, end_words[j]):
                result.append(result[j])
                assigned = True
                break
        if not assigned:
            result.append(chr(65 + (next_label % 26)))
            next_label += 1
    return result


_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "is", "it", "i", "me", "my", "we", "he", "she", "be", "do",
    "so", "no", "if", "up", "as", "by", "am", "are", "was", "has", "had",
    "not", "that", "this", "with", "from", "they", "them", "their", "you",
    "your", "all", "can", "will", "just",
})


_VOWEL_PHONES = frozenset({
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
})


def _count_alliteration(bars):
    total = 0
    for bar in bars:
        words = [w.lower().strip("'") for w in re.findall(r"[a-zA-Z']+", bar)
                 if w.lower().strip("'") not in _STOP_WORDS and len(w) > 1]
        starts = defaultdict(int)
        for w in words:
            starts[w[0]] += 1
        for count in starts.values():
            if count >= 3:
                total += count
    return total


def _count_similes(bars):
    total = 0
    for bar in bars:
        total += len(re.findall(r'\blike\b', bar, re.IGNORECASE))
    return total


def _unique_ratio(bars):
    words = []
    for bar in bars:
        words.extend(w.lower().strip("'") for w in re.findall(r"[a-zA-Z']+", bar)
                     if len(w.strip("'")) > 1)
    if not words:
        return 0
    return len(set(words)) / len(words)


def _count_multisyl(bars, cmap):
    count = 0
    for (bi, s, e), ci in cmap.items():
        text = bars[bi][s:e].lower().strip("'")
        if " " in text:
            count += 1
            continue
        phones = pronouncing.phones_for_word(text)
        if phones:
            rp = pronouncing.rhyming_part(phones[0])
            rp_syls = sum(1 for ph in rp.split() if any(c.isdigit() for c in ph))
            if rp_syls >= 2:
                count += 1
    return count


def _count_consonance(bars):
    total = 0
    for bar in bars:
        words = [w.lower().strip("'") for w in re.findall(r"[a-zA-Z']+", bar)
                 if w.lower().strip("'") not in _STOP_WORDS and len(w) > 1]
        cons = defaultdict(int)
        for w in words:
            phones = pronouncing.phones_for_word(w)
            if phones:
                seen = set()
                for ph in phones[0].split():
                    c = re.sub(r'\d', '', ph)
                    if c not in _VOWEL_PHONES and c not in seen:
                        cons[c] += 1
                        seen.add(c)
        for count in cons.values():
            if count >= 3:
                total += count
    return total


def _get_stress_pattern(bar):
    result = []
    for m in re.finditer(r"[a-zA-Z']+", bar):
        word = m.group()
        w_clean = word.lower().strip("'")
        syls = _hyph.inserted(word).split('-')
        phones = pronouncing.phones_for_word(w_clean)
        if phones:
            stresses = []
            for ph in phones[0].split():
                for c in ph:
                    if c.isdigit():
                        stresses.append(int(c))
            for si, syl in enumerate(syls):
                stress = stresses[si] if si < len(stresses) else -1
                result.append((syl, stress))
        else:
            for syl in syls:
                result.append((syl, -1))
    return result


def _flow_state(bars):
    total_syls = 0
    stressed_syls = 0
    for bar in bars:
        pattern = _get_stress_pattern(bar)
        for syl, stress in pattern:
            total_syls += 1
            if stress in (1, 2):
                stressed_syls += 1
    if total_syls == 0:
        return 1.0
    return (stressed_syls / total_syls) / 0.42


def _rate_verse(bars, density, internal_n, avg_syl, cmap=None):
    n = len(bars)
    if n == 0:
        return 0.0, "?", {}

    unique_bars = len(set(b.lower().strip() for b in bars))
    repeat_ratio = unique_bars / n

    rhyme_sc = min(density / 100, 1.0) * 10
    int_per_bar = internal_n / n
    internal_sc = min(int_per_bar / 1.0, 1.0) * 10
    syls = [_line_syllables(b) for b in bars]
    mean_s = sum(syls) / n
    var = sum((s - mean_s) ** 2 for s in syls) / n
    std = var ** 0.5
    cv = std / mean_s if mean_s > 0 else 1
    flow_sc = max(0, (1 - cv * 0.5)) * 10
    words = sum(len(b.split()) for b in bars)
    syl_total = sum(syls)
    syl_per_word = syl_total / words if words > 0 else 1
    vocab_sc = min((syl_per_word - 1) / 0.7, 1.0) * 10
    n_clusters = len(set(cmap.values())) if cmap else 0
    cluster_sc = min(n_clusters / max(n * 0.4, 1), 1.0) * 10
    allit_n = _count_alliteration(bars)
    simile_n = _count_similes(bars)
    unique_r = _unique_ratio(bars)
    multi_n = _count_multisyl(bars, cmap) if cmap else 0
    conson_n = _count_consonance(bars)
    multi_sc = min(multi_n / max(n * 0.5, 1), 1.0) * 10
    allit_bonus = min(allit_n / max(n * 1.5, 1), 1.0) * 0.8
    simile_bonus = min(simile_n / max(n * 0.3, 1), 1.0) * 0.4
    conson_bonus = min(conson_n / max(n * 2, 1), 1.0) * 0.4
    raw = (rhyme_sc * 0.20 + internal_sc * 0.20 + flow_sc * 0.10
           + vocab_sc * 0.10 + cluster_sc * 0.15 + multi_sc * 0.25)
    raw += allit_bonus + simile_bonus + conson_bonus
    unique_mult = min(unique_r / 0.7, 1.0)
    repeat_mult = min(repeat_ratio / 0.8, 1.0)
    raw *= unique_mult * repeat_mult
    score = max(0, min(10, raw))
    if score >= 9:
        grade = "S"
    elif score >= 8:
        grade = "A"
    elif score >= 6.5:
        grade = "B"
    elif score >= 5:
        grade = "C"
    elif score >= 3:
        grade = "D"
    else:
        grade = "F"
    extras = {
        "allit": allit_n, "similes": simile_n, "unique": unique_r,
        "multi": multi_n, "consonance": conson_n,
        "components": [
            ("Multisyllabic", multi_sc, 0.25),
            ("End Rhyme", rhyme_sc, 0.20),
            ("Internal Rhyme", internal_sc, 0.20),
            ("Rhyme Variety", cluster_sc, 0.15),
            ("Flow", flow_sc, 0.10),
            ("Vocabulary", vocab_sc, 0.10),
        ],
        "bonuses": [
            ("Alliteration", allit_bonus, 0.8),
            ("Similes", simile_bonus, 0.4),
            ("Consonance", conson_bonus, 0.4),
        ],
        "unique_mult": unique_mult,
        "repeat_mult": repeat_mult,
    }
    return round(score, 1), grade, extras


def _rhyme_key(word):
    phones = pronouncing.phones_for_word(word.lower())
    if phones:
        return pronouncing.rhyming_part(phones[0])
    return None


def _build_rhyme_map(bars, rdf):
    occs = []
    for bi, bar in enumerate(bars):
        for m in re.finditer(r"[a-zA-Z']+", bar):
            w = m.group().lower().strip("'")
            if w and len(w) > 1 and w not in _STOP_WORDS:
                occs.append((bi, m.start(), m.end(), w))

    by_key = defaultdict(list)
    for occ in occs:
        rk = _rhyme_key(occ[3])
        if rk:
            by_key[rk].append(occ)
    for occ in occs:
        sv = _stressed_vowel(occ[3])
        if sv:
            by_key[f"_sl{sv}"].append(occ)
    if not rdf.empty:
        w2g = defaultdict(set)
        phrase_entries = []
        for _, row in rdf.iterrows():
            wl = row["word"].lower()
            w2g[wl].add(row["rhyme_group"])
            if " " in wl:
                phrase_entries.append((wl, row["rhyme_group"]))
        for occ in occs:
            for gid in w2g.get(occ[3], set()):
                by_key[f"_db{gid}"].append(occ)
        for bi, bar in enumerate(bars):
            bar_lower = bar.lower()
            for phrase, gid in phrase_entries:
                pat = r'\b' + re.escape(phrase) + r'\b'
                for m in re.finditer(pat, bar_lower):
                    occ = (bi, m.start(), m.end(), phrase)
                    by_key[f"_db{gid}"].append(occ)

    raw = []
    for key, members in by_key.items():
        unique = set(m[3] for m in members)
        bars_hit = set(m[0] for m in members)
        if key.startswith("_sl"):
            if len(unique) >= 3 and len(bars_hit) >= 2:
                raw.append(set(members))
        elif len(unique) >= 2:
            raw.append(set(members))

    changed = True
    while changed:
        changed = False
        for i in range(len(raw)):
            for j in range(i + 1, len(raw)):
                words_i = set(m[3] for m in raw[i])
                words_j = set(m[3] for m in raw[j])
                if words_i & words_j:
                    raw[i] |= raw[j]
                    raw.pop(j)
                    changed = True
                    break
            if changed:
                break

    cmap = {}
    for ci, cluster in enumerate(raw):
        for bi, s, e, w in cluster:
            cmap[(bi, s, e)] = ci
    return cmap


# ============================================================
# TOOLS — the reason you tab over from Docs
# ============================================================

tool_left, tool_right = st.columns([3, 2])

with tool_left:
    st.markdown("##### Rhyme Finder")
    _rf = st.text_input(
        "rhyme", placeholder="Type a word...",
        label_visibility="collapsed", key="rhyme_input",
    )
    if _rf.strip():
        _word = _rf.strip()
        _wsyl = _count_syllables(_word)
        _db_rhymes = _find_rhymes_db(_word, rhyme_df)
        _cmu_rhymes = _find_rhymes_cmu(_word)
        _db_set = {w.lower() for w in _db_rhymes}
        _all_rhymes = list(_db_rhymes) + [w for w in _cmu_rhymes if w.lower() not in _db_set]
        if _all_rhymes:
            _by_syl = defaultdict(list)
            for r in _all_rhymes:
                _by_syl[_count_syllables(r)].append(r)
            _src = f"{len(_db_rhymes)} yours + {len(_all_rhymes) - len(_db_rhymes)} CMU" if _db_rhymes else f"{len(_all_rhymes)} CMU"
            st.markdown(f"**{len(_all_rhymes)} rhymes** for *{_word}* ({_wsyl} syl) — {_src}")
            for sc in sorted(_by_syl.keys()):
                st.caption(f"{sc} syl — {' / '.join(_by_syl[sc])}")
            st.code(" / ".join(_all_rhymes), language=None)
        else:
            st.caption(f"No rhymes found for *{_word}* ({_wsyl} syl)")

with tool_right:
    st.markdown("##### Syllable Counter")
    _sc = st.text_input(
        "syllables", placeholder="Type or paste a bar...",
        label_visibility="collapsed", key="syl_input",
    )
    if _sc.strip():
        _wds = re.findall(r"[a-zA-Z']+", _sc)
        _pw = [(w, _count_syllables(w)) for w in _wds]
        _tot = sum(s for _, s in _pw)
        st.markdown(f"**{_tot} syllables**")
        st.caption("  ".join(f"{w}({s})" for w, s in _pw))

st.divider()

# ============================================================
# ANALYZE — paste from Docs, see everything instantly
# ============================================================

st.markdown("##### Analyze")

_loaded_id = st.session_state.get("loaded_lyric_id")
_loaded_title = st.session_state.get("loaded_lyric_title")

if "_pending_paste" in st.session_state:
    st.session_state["paste_area"] = st.session_state.pop("_pending_paste")

if _loaded_id:
    _lc1, _lc2 = st.columns([8, 1])
    _lc1.caption(f"Editing: **{_loaded_title}**")
    if _lc2.button("Clear"):
        st.session_state.pop("loaded_lyric_id", None)
        st.session_state.pop("loaded_lyric_title", None)
        st.session_state["paste_area"] = ""
        st.rerun()

_paste = st.text_area(
    "paste", height=280, placeholder="Paste from Google Docs...",
    key="paste_area", label_visibility="collapsed",
)

if _paste.strip():
    _bars = [re.sub(r'\([^)]*\)', '', l).strip() for l in _paste.split("\n")]
    _bars = [b for b in _bars if b]
    if _bars:
        _wc = sum(len(b.split()) for b in _bars)
        _ts = sum(_line_syllables(b) for b in _bars)
        _avg = _ts / len(_bars)

        _scheme = _detect_scheme(_bars, rhyme_df)
        _cmap = _build_rhyme_map(_bars, rhyme_df)
        _cluster_words = defaultdict(set)
        for (_bi_c, _s_c, _e_c), _ci_c in _cmap.items():
            _cluster_words[_ci_c].add(_bars[_bi_c][_s_c:_e_c].lower().strip("'"))
        _smap = _build_syllable_map(_bars)
        _rhy_n = sum(1 for l in _scheme if _scheme.count(l) > 1 and l != "-") if _scheme else 0
        _density = _rhy_n / len(_scheme) * 100 if _scheme else 0

        _last_word_pos = set()
        for _bi_m, _bar_m in enumerate(_bars):
            _mts = list(re.finditer(r"[a-zA-Z']+", _bar_m))
            if _mts:
                _last_word_pos.add((_bi_m, _mts[-1].start(), _mts[-1].end()))
        _internal_n = sum(1 for pos in _cmap if pos not in _last_word_pos)

        _score, _grade, _extras = _rate_verse(_bars, _density, _internal_n, _avg, _cmap)
        _grade_clrs = {"S": "#FFD700", "A": "#4CAF50", "B": "#2196F3", "C": "#FF9800", "D": "#F44336", "F": "#9E9E9E"}
        _gclr = _grade_clrs.get(_grade, "#666")

        _fs = _flow_state(_bars)
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Bars", len(_bars))
        s2.metric("Words", _wc)
        s3.metric("Avg/Bar", f"{_avg:.1f}")
        s4.metric("Flow State", f"{_fs:.2f}x")
        s5.markdown(
            f'<div style="text-align:center;padding:4px 0;">'
            f'<div style="font-size:0.85em;color:#888;margin-bottom:2px;">Verdict</div>'
            f'<span style="font-size:2em;font-weight:800;color:{_gclr};">{_grade}</span>'
            f'<span style="font-size:0.8em;color:#888;margin-left:4px;">{_score * 10:.0f}/100</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        t1, t2, t3, t4, t5, t6, t7 = st.columns(7)
        t1.metric("End Rhyme", f"{_density:.0f}%")
        t2.metric("Internal", _internal_n)
        t3.metric("Multi-syl", _extras["multi"])
        t4.metric("Allit.", _extras["allit"])
        t5.metric("Similes", _extras["similes"])
        t6.metric("Conson.", _extras["consonance"])
        t7.metric("Unique", f"{_extras['unique']:.0%}")

        with st.expander("Score Breakdown"):
            _comps = _extras["components"]
            _bons = _extras["bonuses"]
            _comps_sorted = sorted(_comps, key=lambda x: x[1])
            _breakdown_html = []
            for name, sc, weight in _comps_sorted:
                pct = sc / 10 * 100
                wt_pct = int(weight * 100)
                if pct >= 80:
                    bar_clr = "#4CAF50"
                elif pct >= 50:
                    bar_clr = "#FF9800"
                else:
                    bar_clr = "#F44336"
                _breakdown_html.append(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                    f'<span style="min-width:120px;font-size:0.85em;">{name} ({wt_pct}%)</span>'
                    f'<div style="flex:1;background:#333;border-radius:4px;height:16px;overflow:hidden;">'
                    f'<div style="width:{pct:.0f}%;height:100%;background:{bar_clr};border-radius:4px;'
                    f'transition:width 0.3s;"></div></div>'
                    f'<span style="min-width:40px;text-align:right;font-size:0.85em;color:#888;">'
                    f'{sc:.1f}/10</span></div>'
                )
            _bon_parts = []
            for name, val, mx in _bons:
                if val > 0:
                    _bon_parts.append(f'{name} +{val:.1f}')
            if _bon_parts:
                _breakdown_html.append(
                    f'<div style="margin-top:6px;font-size:0.82em;color:#888;">'
                    f'Bonuses: {" · ".join(_bon_parts)}</div>'
                )
            _um = _extras["unique_mult"]
            _rm = _extras["repeat_mult"]
            if _um < 1.0 or _rm < 1.0:
                _pen_parts = []
                if _um < 1.0:
                    _pen_parts.append(f'Low unique words ({_um:.0%})')
                if _rm < 1.0:
                    _pen_parts.append(f'Repeated lines ({_rm:.0%})')
                _breakdown_html.append(
                    f'<div style="margin-top:4px;font-size:0.82em;color:#F44336;">'
                    f'Penalties: {" · ".join(_pen_parts)}</div>'
                )
            _weakest = _comps_sorted[0]
            _breakdown_html.append(
                f'<div style="margin-top:8px;padding:8px;background:#1a1a2e;border-radius:6px;'
                f'border-left:3px solid #F44336;font-size:0.85em;">'
                f'Biggest opportunity: <b>{_weakest[0]}</b> — scoring {_weakest[1]:.1f}/10 '
                f'at {int(_weakest[2]*100)}% weight</div>'
            )
            st.markdown("\n".join(_breakdown_html), unsafe_allow_html=True)

        _syl_mode = st.checkbox("Show syllables", key="syl_toggle")

        for i, bar in enumerate(_bars):
            _s = _line_syllables(bar)
            _lbl = _scheme[i] if i < len(_scheme) else "-"
            _ci = ord(_lbl) - 65 if _lbl != "-" else -1
            _lclr = SCHEME_COLORS[_ci % len(SCHEME_COLORS)] if _ci >= 0 else "#666"

            if _syl_mode:
                _bar_html = _render_syl_bar(bar, i, _smap)
            else:
                _hl = sorted([(s, e, c) for (b, s, e), c in _cmap.items() if b == i])
                _parts = []
                _pos = 0
                for _hs, _he, _hc in _hl:
                    if _hs > _pos:
                        _parts.append(bar[_pos:_hs])
                    _hclr = SCHEME_COLORS[_hc % len(SCHEME_COLORS)]
                    _conn = len(_cluster_words.get(_hc, set())) - 1
                    _conn_badge = f'<sup style="color:#888;font-size:0.65em;margin-left:1px;">+{_conn}</sup>' if _conn > 0 else ''
                    _parts.append(f'<span style="color:{_hclr};font-weight:700;">{bar[_hs:_he]}</span>{_conn_badge}')
                    _pos = _he
                if _pos < len(bar):
                    _parts.append(bar[_pos:])
                _bar_html = "".join(_parts)

            st.markdown(
                f'<div style="display:flex;align-items:baseline;gap:10px;margin:3px 0;'
                f'font-family:monospace;font-size:0.95em;">'
                f'<span style="color:{_lclr};font-weight:700;min-width:18px;text-align:center;">{_lbl}</span>'
                f'<span style="color:#888;min-width:30px;text-align:right;font-size:0.85em;">{_s}s</span>'
                f'<span>{_bar_html}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with st.expander("Stress Pattern Grid"):
            _stress_cells = []
            for i, bar in enumerate(_bars):
                pattern = _get_stress_pattern(bar)
                cells = []
                for syl, stress in pattern:
                    if stress == 1:
                        bg, fg = "#FF6B35", "#fff"
                    elif stress == 2:
                        bg, fg = "#FFB74D", "#000"
                    elif stress == 0:
                        bg, fg = "#444", "#aaa"
                    else:
                        bg, fg = "#333", "#555"
                    cells.append(
                        f'<span style="display:inline-block;padding:2px 4px;margin:1px;'
                        f'border-radius:3px;background:{bg};color:{fg};'
                        f'font-size:0.75em;font-family:monospace;line-height:1.4;">{syl}</span>'
                    )
                _lbl_s = _scheme[i] if i < len(_scheme) else "-"
                _stress_cells.append(
                    f'<div style="display:flex;flex-wrap:wrap;align-items:center;margin:2px 0;">'
                    f'<span style="color:#888;min-width:28px;font-size:0.75em;font-family:monospace;">'
                    f'{i + 1:02d}</span>{"".join(cells)}</div>'
                )
            _legend = (
                '<div style="margin-bottom:8px;">'
                '<span style="display:inline-block;padding:2px 6px;margin:2px;border-radius:3px;'
                'background:#FF6B35;color:#fff;font-size:0.75em;">Primary</span>'
                '<span style="display:inline-block;padding:2px 6px;margin:2px;border-radius:3px;'
                'background:#FFB74D;color:#000;font-size:0.75em;">Secondary</span>'
                '<span style="display:inline-block;padding:2px 6px;margin:2px;border-radius:3px;'
                'background:#444;color:#aaa;font-size:0.75em;">Unstressed</span>'
                '</div>'
            )
            st.markdown(_legend + "\n".join(_stress_cells), unsafe_allow_html=True)

        with st.expander("Syllable Balance"):
            st.bar_chart(
                pd.DataFrame({
                    "Bar": [f"{i + 1:02d}" for i in range(len(_bars))],
                    "Syllables": [_line_syllables(b) for b in _bars],
                }),
                x="Bar", y="Syllables", color="#FF6B35",
            )

        with st.expander("Literary Devices"):
            _dev_sections = []

            _sim_hits = []
            for i, bar in enumerate(_bars):
                for m in re.finditer(r'\blike\b', bar, re.IGNORECASE):
                    ctx = bar[max(0, m.start() - 20):m.end() + 30].strip()
                    _sim_hits.append((i + 1, ctx))
            if _sim_hits:
                _dev_sections.append("**Similes**")
                for bnum, ctx in _sim_hits:
                    _dev_sections.append(f"- Bar {bnum}: *\"...{ctx}...\"*")

            _al_hits = []
            for i, bar in enumerate(_bars):
                words = [w for w in re.findall(r"[a-zA-Z']+", bar)
                         if w.lower().strip("'") not in _STOP_WORDS and len(w) > 1]
                starts = defaultdict(list)
                for w in words:
                    starts[w[0].lower()].append(w)
                for letter, ws in starts.items():
                    if len(ws) >= 3:
                        _al_hits.append((i + 1, letter.upper(), ws))
            if _al_hits:
                _dev_sections.append("**Alliteration**")
                for bnum, letter, ws in _al_hits:
                    _dev_sections.append(f"- Bar {bnum} ({letter}): {', '.join(ws)}")

            _con_hits = []
            for i, bar in enumerate(_bars):
                words = [w.lower().strip("'") for w in re.findall(r"[a-zA-Z']+", bar)
                         if w.lower().strip("'") not in _STOP_WORDS and len(w) > 1]
                cons = defaultdict(list)
                for w in words:
                    phones = pronouncing.phones_for_word(w)
                    if phones:
                        seen = set()
                        for ph in phones[0].split():
                            c = re.sub(r'\d', '', ph)
                            if c not in _VOWEL_PHONES and c not in seen:
                                cons[c].append(w)
                                seen.add(c)
                for sound, ws in cons.items():
                    if len(ws) >= 3:
                        unique = list(dict.fromkeys(ws))
                        _con_hits.append((i + 1, sound, unique))
            if _con_hits:
                _dev_sections.append("**Consonance**")
                for bnum, sound, ws in _con_hits:
                    _dev_sections.append(f"- Bar {bnum} (/{sound}/): {', '.join(ws)}")

            _ms_hits = []
            for (bi, s, e), ci in _cmap.items():
                text = _bars[bi][s:e]
                if " " in text:
                    _ms_hits.append((bi + 1, text))
                    continue
                phones = pronouncing.phones_for_word(text.lower())
                if phones:
                    rp = pronouncing.rhyming_part(phones[0])
                    rp_syls = sum(1 for ph in rp.split() if any(c.isdigit() for c in ph))
                    if rp_syls >= 2:
                        _ms_hits.append((bi + 1, text))
            if _ms_hits:
                _dev_sections.append("**Multisyllabic Rhymes**")
                _ms_by_bar = defaultdict(list)
                for bnum, word in _ms_hits:
                    _ms_by_bar[bnum].append(word)
                for bnum in sorted(_ms_by_bar):
                    _dev_sections.append(f"- Bar {bnum}: {', '.join(_ms_by_bar[bnum])}")

            _asson_clusters = defaultdict(list)
            for (bi, s, e), ci in _cmap.items():
                word = _bars[bi][s:e].lower().strip("'")
                if " " not in word:
                    sv = _stressed_vowel(word)
                    if sv:
                        _asson_clusters[sv].append(word)
            _asson_show = {v: list(dict.fromkeys(ws)) for v, ws in _asson_clusters.items() if len(set(ws)) >= 3}
            if _asson_show:
                _dev_sections.append("**Assonance (vowel patterns)**")
                for vowel, ws in sorted(_asson_show.items(), key=lambda x: -len(x[1])):
                    _dev_sections.append(f"- /{vowel}/: {', '.join(ws[:12])}")

            if _dev_sections:
                st.markdown("\n".join(_dev_sections))
            else:
                st.caption("No notable devices detected.")

        _unrhymed = []
        for i, bar in enumerate(_bars):
            lw = _last_word(bar)
            if not lw:
                continue
            lbl = _scheme[i] if i < len(_scheme) else "-"
            if not (_scheme.count(lbl) > 1 and lbl != "-"):
                _unrhymed.append(lw)
        if _unrhymed:
            with st.expander(f"Rhyme Suggestions ({len(_unrhymed)} unrhymed endings)"):
                for word in _unrhymed[-8:]:
                    rh = _find_rhymes(word, rhyme_df)
                    if rh:
                        st.code(f"{word} → {' / '.join(rh[:10])}", language=None)
                    else:
                        st.caption(f"**{word}** — no rhymes found")

        # --- save / update ---
        _save_col1, _save_col2 = st.columns(2)
        if _loaded_id:
            if _save_col1.button("Update in Archive"):
                update_row("lyrics", _loaded_id, {
                    "content": _paste,
                    "updated_at": today.isoformat(),
                })
                st.success(f"Updated '{_loaded_title}'.")
                st.rerun()
        if lyrics_data is not None:
            with _save_col2.popover("Save as New"):
                with st.form("save_lyric"):
                    _sv_t = st.text_input("Title")
                    _sv_s = st.selectbox(
                        "Status", list(STATUS_LABELS.keys()),
                        format_func=lambda x: STATUS_LABELS[x],
                    )
                    if st.form_submit_button("Save"):
                        if _sv_t.strip():
                            insert_row("lyrics", {
                                "title": _sv_t.strip(),
                                "content": _paste,
                                "status": _sv_s,
                            })
                            st.success(f"Saved '{_sv_t.strip()}'")
                            st.rerun()
                        else:
                            st.error("Title required.")

st.divider()

# ============================================================
# ARCHIVE
# ============================================================

_arch_label = f"Archive ({len(lyrics_df)})" if not lyrics_df.empty else "Archive"
with st.expander(_arch_label):
    if lyrics_data is None:
        st.warning("Create the `lyrics` table in Supabase:")
        st.code(
            "create table lyrics (\n"
            "    id bigint generated by default as identity primary key,\n"
            "    title text not null,\n"
            "    content text default '',\n"
            "    status text default 'draft',\n"
            "    created_at timestamptz default now(),\n"
            "    updated_at timestamptz default now()\n"
            ");\n\n"
            "alter table lyrics enable row level security;\n"
            "create policy \"Allow All\" on lyrics\n"
            "  for all using (true) with check (true);",
            language="sql",
        )
    elif lyrics_df.empty:
        st.caption("No saved lyrics yet. Paste bars above and save them.")
    else:
        for _, _ly in lyrics_df.iterrows():
            _st = STATUS_LABELS.get(_ly.get("status", "draft"), "Draft")
            _ct = _ly.get("content") or ""
            _bn = len([l for l in _ct.split("\n") if l.strip()])
            _wn = len(_ct.split())
            _sn = sum(_line_syllables(l) for l in _ct.split("\n") if l.strip())

            ac1, ac2, ac3 = st.columns([7, 1, 1])
            ac1.markdown(f"**{_ly['title']}** — {_st} · {_bn} bars · {_wn} words · {_sn} syl")
            if ac2.button("Load", key=f"ld_{_ly['id']}"):
                st.session_state["loaded_lyric_id"] = int(_ly["id"])
                st.session_state["loaded_lyric_title"] = _ly["title"]
                st.session_state["_pending_paste"] = _ct
                st.rerun()

            _dk = f"cdla_{_ly['id']}"
            if st.session_state.get(_dk):
                st.warning(f"Delete **{_ly['title']}**?")
                yc, nc = st.columns(2)
                if yc.button("Yes", key=f"ya_{_ly['id']}"):
                    delete_row("lyrics", _ly["id"])
                    st.session_state.pop(_dk, None)
                    if _loaded_id == int(_ly["id"]):
                        st.session_state.pop("loaded_lyric_id", None)
                        st.session_state.pop("loaded_lyric_title", None)
                    st.rerun()
                if nc.button("No", key=f"na_{_ly['id']}"):
                    st.session_state.pop(_dk, None)
                    st.rerun()
            elif ac3.button("\U0001f5d1️", key=f"da_{_ly['id']}"):
                st.session_state[_dk] = True
                st.rerun()

# ============================================================
# RHYME DATABASE
# ============================================================

def _sound_label(word):
    if " " in word:
        parts = word.split()
        last = parts[-1]
    else:
        last = word
    phones = pronouncing.phones_for_word(last.lower())
    if phones:
        rp = pronouncing.rhyming_part(phones[0])
        return "/" + re.sub(r'\d', '', rp) + "/"
    return None


def _entry_tag(word):
    if " " in word:
        return "phrase"
    if not pronouncing.phones_for_word(word.lower()):
        return "slang"
    return None


_rdb_ct = f" ({len(rhyme_df)} entries, {rhyme_df['rhyme_group'].nunique()} sets)" if not rhyme_df.empty else ""
with st.expander(f"Custom Rhymes{_rdb_ct}"):
    st.caption("Teach the analyzer rhymes it can't detect: phrases, slang, your pronunciation.")

    with st.form("add_rhyme_set"):
        _nw = st.text_input(
            "Add rhyme set",
            placeholder="orange, door hinge, four inch",
        )
        if st.form_submit_button("Add"):
            _words = [w.strip() for w in _nw.split(",") if w.strip()]
            if len(_words) >= 2:
                _ng = int(rhyme_df["rhyme_group"].max()) + 1 if not rhyme_df.empty else 1
                for w in _words:
                    insert_row("rhymes", {"word": w, "rhyme_group": _ng})
                st.success(f"Added: {' / '.join(_words)}")
                st.rerun()
            elif _words:
                st.error("Need at least 2 words/phrases to form a rhyme set.")

    if not rhyme_df.empty:
        _dbq = st.text_input("Filter", placeholder="Search...", key="rdb_search")

        _sound_groups = defaultdict(list)
        for gid, gdf in rhyme_df.groupby("rhyme_group"):
            words = gdf["word"].tolist()
            first_label = None
            for w in words:
                first_label = _sound_label(w)
                if first_label:
                    break
            _sound_groups[first_label or "?"].append((gid, gdf, words))

        _shown = 0
        for sound_key in sorted(_sound_groups, key=lambda x: (x == "?", x)):
            sets_in_sound = _sound_groups[sound_key]
            if _dbq:
                sets_in_sound = [(gid, gdf, ws) for gid, gdf, ws in sets_in_sound
                                 if any(_dbq.lower() in w.lower() for w in ws)]
            if not sets_in_sound:
                continue

            st.markdown(f"**{sound_key}**")
            for gid, gdf, words in sets_in_sound:
                _shown += 1
                tags = []
                for w in words:
                    t = _entry_tag(w)
                    tag_str = f" `{t}`" if t else ""
                    if _dbq and _dbq.lower() in w.lower():
                        tags.append(f"**{w}**{tag_str}")
                    else:
                        tags.append(f"{w}{tag_str}")
                gc1, gc2, gc3 = st.columns([7, 1, 1])
                gc1.markdown(" / ".join(tags))
                with gc2.popover("Edit"):
                    for _, row in gdf.iterrows():
                        ec1, ec2, ec3 = st.columns([4, 2, 1])
                        nw = ec1.text_input("W", value=row["word"], key=f"erw_{row['id']}", label_visibility="collapsed")
                        if ec2.button("Save", key=f"srw_{row['id']}"):
                            if nw.strip() and nw.strip() != row["word"]:
                                update_row("rhymes", row["id"], {"word": nw.strip()})
                                st.rerun()
                        ck = f"cdrw_{row['id']}"
                        if st.session_state.get(ck):
                            st.warning(f"Delete **{row['word']}**?")
                            yc, nc = st.columns(2)
                            if yc.button("Yes", key=f"yrw_{row['id']}"):
                                delete_row("rhymes", row["id"])
                                st.session_state.pop(ck, None)
                                st.rerun()
                            if nc.button("No", key=f"nrw_{row['id']}"):
                                st.session_state.pop(ck, None)
                                st.rerun()
                        elif ec3.button("X", key=f"drw_{row['id']}"):
                            st.session_state[ck] = True
                            st.rerun()
                _add_key = f"add_to_{gid}"
                with gc3.popover("+"):
                    _aw = st.text_input("Add word/phrase", key=f"aw_{gid}")
                    if st.button("Add", key=f"ab_{gid}"):
                        if _aw.strip():
                            insert_row("rhymes", {"word": _aw.strip(), "rhyme_group": gid})
                            st.rerun()

        if _dbq and _shown == 0:
            st.caption("No matches.")

        st.download_button(
            "Download CSV",
            rhyme_df[["rhyme_group", "word"]].rename(columns={"rhyme_group": "Group", "word": "Word"}).to_csv(index=False),
            "rhymes.csv", "text/csv", key="dl_rhymes",
        )
