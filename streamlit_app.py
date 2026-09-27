import importlib
import uuid
from pathlib import Path

import streamlit as st

from aion import calc, db, progress, research_content, research_data, research_dungeons, seed, sessions, ui

st.set_page_config(page_title="AION 2 Planner", page_icon=":material/swords:", layout="wide")

_DATA_CODE = [Path(m.__file__) for m in (db, seed, sessions, research_data, research_content, research_dungeons)]


@st.cache_resource(max_entries=1)
def _init_db(code_stamp: tuple) -> bool:
    """Create/migrate tables. Re-runs whenever the schema/seed code changes (no restart needed)."""
    for module in (research_data, research_content, research_dungeons, seed, db, sessions):
        importlib.reload(module)
    db.init_db()
    return True


_init_db(tuple(p.stat().st_mtime for p in _DATA_CODE))
# Reload data from SQLite on every rerun so edits are always reflected.
st.session_state["_run_id"] = uuid.uuid4().hex

pages = {pd.file: st.Page(f"app_pages/{pd.file}.py", title=pd.title, icon=f":material/{pd.icon}:")
         for pd in progress.PAGES.values()}
# Built-in menu hidden: the sidebar below adds progress bars and done checks.
page = st.navigation(list(pages.values()), position="hidden")
current = next(pd for f, pd in progress.PAGES.items() if pages[f].url_path == page.url_path)

m = progress.marks()
with st.sidebar:
    overall = progress.overall_fraction(m)
    st.progress(overall, text=f"**Overall completion · {overall:.0%}**")
    for section, section_pages in progress.SECTIONS.items():
        frac = progress.section_fraction(section, m)
        st.progress(frac, text=f"{section} · {frac:.0%}")
        for pd in section_pages:
            f = progress.page_fraction(pd, m)
            label = pd.title + (f" · {sum(bool(m.get(f'{pd.file}:{t}')) for t in pd.tabs)}/{len(pd.tabs)}"
                                if pd.tabs and 0 < f < 1 else "")
            st.page_link(pages[pd.file], label=f"{label} {progress.mark(f >= 1)}", icon=f":material/{pd.icon}:")
    st.divider()
    with st.expander("Global parameters", icon=":material/tune:"):
        ui.s_toggle("Membership (account)", "account_membership", where="sb")
        labels = {r[0]: r[1] for r in seed.RULESETS}
        ui.s_multiselect("Rulesets used in calculations", "allowed_rulesets", list(labels), format_func=labels.get, where="sb")
        ui.s_number("Daily leveling hours", "daily_play_hours", min_value=0.5, max_value=24.0, step=0.5, where="sb")
        ui.s_select("Reset day", "reset_day", calc.WEEKDAYS, where="sb")
        ui.s_select("Kinah value mode", "kinah_value_mode", calc.KINAH_VALUE_MODES, where="sb")
        ui.s_toggle("Include bound Kinah", "include_bound_kinah", where="sb")
        ui.s_toggle("Include alts", "include_alts", where="sb")
        ui.s_toggle("Use shop Odyle", "use_shop_odyle", where="sb", help="KR/TW reference limits — not Global-confirmed.")
        ui.s_toggle("Use morph Odyle", "use_morph_odyle", where="sb", help="KR/TW reference limits — not Global-confirmed.")

with st.container(horizontal=True, vertical_alignment="center"):
    st.title(page.title)
    if not current.tabs:  # pages with tabs get one toggle per tab instead
        progress.done_toggle(current.file)
page.run()
