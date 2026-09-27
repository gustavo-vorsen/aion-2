"""Page registry, manual "done filling" marks and completion percentages."""
from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st

from aion import db


@dataclass(frozen=True)
class PageDef:
    file: str
    title: str
    icon: str
    tabs: tuple[str, ...] = field(default_factory=tuple)  # tab keys that each get their own "done" mark


SECTIONS: dict[str, list[PageDef]] = {
    "Overview": [
        PageDef("dashboard", "Dashboard", "dashboard"),
        PageDef("main_loop", "Main loop", "star"),
        PageDef("alt_loop", "Alt loop", "people"),
        PageDef("gear", "Gear & upgrade priority", "shield"),
    ],
    "Planner": [
        PageDef("characters", "Characters", "group"),
        PageDef("leveling", "Leveling", "trending_up", ("main", "alt")),
        PageDef("leveling_schedule", "Leveling schedule", "calendar_month"),
        PageDef("planner", "Weekly planner", "auto_awesome"),
    ],
    "Content": [
        PageDef("odyle_budget", "Odyle budget", "battery_charging_full"),
        PageDef("expeditions", "Expedition", "bolt"),
        PageDef("transcendence", "Transcendence", "auto_awesome_motion"),
        PageDef("nightmare", "Nightmare", "dark_mode"),
        PageDef("ascension", "Ascension Trial", "military_tech"),
        PageDef("abyss", "Abyss", "public"),
        PageDef("abyss_commands", "Abyss commands", "assignment", ("normal", "abyss")),
        PageDef("pvp", "PvP / battlefields", "sports_kabaddi"),
        PageDef("awakening", "Awakening Battle", "sports_martial_arts"),
        PageDef("subjugation", "Subjugation", "groups"),
        PageDef("field_bosses", "Field bosses", "skull"),
        PageDef("shugo", "Shugo Festival", "celebration"),
        PageDef("invasion", "Dimensional Invasion", "crisis_alert"),
        PageDef("daily_weekly", "Daily & weekly content", "event_repeat"),
        PageDef("progression", "Progression", "workspace_premium",
                ("skills", "daevanion", "side_quests", "strongholds", "hidden_dungeons", "feathers", "genus",
                 "titles", "wardrobe", "wings", "amulet_belt", "pantheon", "arcana")),
    ],
    "Economy": [
        PageDef("economy", "Economy / shops", "storefront", ("calculator", "all")),
        PageDef("rewards", "Rewards & currencies", "paid", ("registry", "matrix")),
        PageDef("analytics", "Analytics", "insights",
                ("time", "kinah", "ap", "odyle", "materials", "mva", "frontier")),
    ],
    "Data": [
        PageDef("settings", "Settings / ruleset", "settings", ("general", "rulesets", "sources", "data")),
    ],
}

PAGES = {p.file: p for pages in SECTIONS.values() for p in pages}


def marks() -> dict[str, bool]:
    if "_progress" not in st.session_state or st.session_state.get("_progress_run") != st.session_state.get("_run_id"):
        df = db.read_table("progress")
        st.session_state["_progress"] = {k: bool(v) for k, v in zip(df["key"], df["done"])}
        st.session_state["_progress_run"] = st.session_state.get("_run_id")
    return st.session_state["_progress"]


def page_fraction(page: PageDef, m: dict[str, bool]) -> float:
    if page.tabs:
        return sum(bool(m.get(f"{page.file}:{t}")) for t in page.tabs) / len(page.tabs)
    return 1.0 if m.get(page.file) else 0.0


def section_fraction(section: str, m: dict[str, bool]) -> float:
    pages = SECTIONS[section]
    return sum(page_fraction(p, m) for p in pages) / len(pages)


def overall_fraction(m: dict[str, bool]) -> float:
    pages = list(PAGES.values())
    return sum(page_fraction(p, m) for p in pages) / len(pages)


def _save(key: str, widget_key: str) -> None:
    db.upsert("progress", {"key": key}, {"done": bool(st.session_state[widget_key])})
    st.session_state.pop("_progress_run", None)  # reload marks on this rerun


def done_toggle(key: str, label: str = "Done filling") -> bool:
    wk = f"progress__{key}"
    return st.toggle(label, value=bool(marks().get(key)), key=wk, on_change=_save, args=(key, wk),
                     help="Mark as done when you have finished filling this in. Drives the sidebar progress.")


def tab_done(page_file: str, tab: str, label: str = "Done filling this tab") -> bool:
    return done_toggle(f"{page_file}:{tab}", label)


DONE_MARK = ":green[:material/check_circle:]"
TODO_MARK = ":orange[:material/error:]"


def mark(done: bool) -> str:
    return DONE_MARK if done else TODO_MARK


def tab_label(page_file: str, tab: str, label: str) -> str:
    """Inner-tab label with a green tick when done, an exclamation mark otherwise."""
    return f"{label} {mark(bool(marks().get(f'{page_file}:{tab}')))}"


def _remember_tab(page_file: str, widget_key: str, key_by_label: dict[str, str]) -> None:
    st.session_state[f"_active_tab__{page_file}"] = key_by_label.get(st.session_state[widget_key])


def tabs(page_file: str, spec: list[tuple[str, str]]):
    """st.tabs whose labels carry done/todo marks and whose selection survives label changes.

    spec: [(tab_key, label), ...]. The active tab is remembered by tab_key, not by label.
    """
    labels = [tab_label(page_file, k, lab) for k, lab in spec]
    key_by_label = dict(zip(labels, [k for k, _ in spec]))
    wk = f"tabs__{page_file}"
    active = st.session_state.get(f"_active_tab__{page_file}")
    if active is not None:
        st.session_state[wk] = labels[[k for k, _ in spec].index(active)]
    return st.tabs(labels, key=wk, on_change=_remember_tab, args=(page_file, wk, key_by_label))
