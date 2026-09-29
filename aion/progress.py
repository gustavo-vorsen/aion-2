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
    tag: str = ""  # short note shown right-aligned in the sidebar; "{n}" = weekly entries of `entries`
    entries: str = ""  # activity category whose weekly entry limit fills "{n}"


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
    # Split by reset cycle: only Daily Duties / daily Supply Requests reset daily; everything else is weekly.
    "Daily content": [
        PageDef("daily_duties", "Daily duties", "task_alt"),
        PageDef("supply_requests", "Supply requests", "local_shipping"),
    ],
    "Weekly content": [
        PageDef("shugo", "Shugo Festival", "celebration", tag="{n} keys", entries="Shugo Festival"),
        PageDef("ascension", "Ascension Trial", "military_tech", tag="{n} entries", entries="Ascension Trial"),
        PageDef("nightmare", "Nightmare", "dark_mode", tag="{n} entries", entries="Nightmare"),
        PageDef("odyle_budget", "Odyle budget", "battery_charging_full"),
        PageDef("expeditions", "Expedition", "bolt"),
        PageDef("transcendence", "Transcendence", "auto_awesome_motion"),
        PageDef("invasion", "Dimensional Invasion", "crisis_alert", tag="{n} claims", entries="Dimensional Invasion"),
        PageDef("abyss", "Abyss", "public"),
        PageDef("abyss_commands", "Abyss commands", "assignment", ("normal", "abyss")),
        PageDef("pvp", "PvP / battlefields", "sports_kabaddi"),
        PageDef("awakening", "Awakening Battle", "sports_martial_arts", tag="{n} entries", entries="Awakening Battle"),
        PageDef("subjugation", "Subjugation", "groups", tag="{n} entries", entries="Subjugation"),
        PageDef("season_weekly", "Season weekly missions", "event_repeat"),
        PageDef("weekly_content", "Dungeons & raid", "date_range"),
    ],
    "Season content": [
        PageDef("season", "Season", "calendar_month"),
    ],
    "One-time content": [
        PageDef("feathers", "Feathers", "flight"),
        PageDef("hidden_dungeons", "Hidden dungeons", "door_front"),
        PageDef("strongholds", "Strongholds", "fort"),
    ],
    "Bosses": [
        PageDef("bosses", "Bosses", "skull", ("field", "world")),
    ],
    "Progression": [
        PageDef("progression", "Progression", "workspace_premium",
                ("skills", "daevanion", "side_quests", "genus", "titles", "wardrobe", "wings", "amulet_belt", "pantheon", "arcana")),
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


# Fill percentages: every editable table reports its filled / total required cells while the page renders;
# the totals are stored per page and per tab and drive the sidebar, the title badge and the tab labels.

def fills() -> dict[str, tuple[float, float]]:
    if "_fills" not in st.session_state or st.session_state.get("_fills_run") != st.session_state.get("_run_id"):
        df = db.read_table("fill")
        st.session_state["_fills"] = {k: (f, t) for k, f, t in zip(df["key"], df["filled"], df["total"])}
        st.session_state["_fills_run"] = st.session_state.get("_run_id")
    return st.session_state["_fills"]


def fraction(key: str) -> float | None:
    """Stored fill fraction; None when the page / tab has nothing to fill. Not visited yet = 0."""
    filled, total = fills().get(key, (0.0, 1.0))
    return None if total <= 0 else min(filled / total, 1.0)


def begin(page_file: str) -> None:
    st.session_state["_fill_acc"] = {}
    st.session_state["_fill_page"] = page_file
    st.session_state["_fill_ctx"] = page_file


def track(filled: float, total: float) -> None:
    """Called by editable widgets / tables: add their filled and total required cells to the current page / tab."""
    ctx = st.session_state.get("_fill_ctx")
    if ctx is None or total <= 0:
        return
    acc = st.session_state["_fill_acc"]
    f, t = acc.get(ctx, (0.0, 0.0))
    acc[ctx] = (f + filled, t + total)


def pause_tracking() -> None:
    """Tables drawn until resume_tracking() don't count (their cells were already counted elsewhere)."""
    st.session_state["_fill_paused"] = st.session_state.get("_fill_ctx")
    st.session_state["_fill_ctx"] = None


def resume_tracking() -> None:
    st.session_state["_fill_ctx"] = st.session_state.pop("_fill_paused", None)


def finish() -> None:
    """Store this page's fill counts; rerun once when they changed so badges and labels are current."""
    page = st.session_state.get("_fill_page")
    if page is None:
        return
    acc = dict(st.session_state.get("_fill_acc", {}))
    acc.setdefault(page, (0.0, 0.0))
    acc[page] = (sum(f for f, _ in acc.values()), sum(t for _, t in acc.values()))
    auto = auto_fraction(page)
    if auto is not None:
        acc[page] = (auto, 1.0)
    old = fills()
    changed = False
    for key, (f, t) in acc.items():
        if old.get(key) != (f, t):
            db.upsert("fill", {"key": key}, {"filled": f, "total": t})
            changed = True
    st.session_state["_fill_page"] = None
    if changed:
        st.session_state.pop("_fills_run", None)
        st.rerun()


def auto_fraction(page_file: str) -> float | None:
    """Completion computed from the page's full tier tables (all layers), not only the visible one."""
    from aion import tier_specs, ui

    spec = tier_specs.AUTO_DONE.get(page_file)
    if spec is None:
        return None
    done = ui.tier_completion(spec.category, spec.key, spec.groups, spec.columns)
    return sum(done.values()) / len(done) if done else 0.0


def page_fraction(page: PageDef) -> float | None:
    if page.tabs:
        parts = [x for x in (fraction(f"{page.file}:{t}") for t in page.tabs) if x is not None]
        return sum(parts) / len(parts) if parts else None
    return fraction(page.file)


def _mean(pages) -> float:
    parts = [x for x in (page_fraction(p) for p in pages) if x is not None]
    return sum(parts) / len(parts) if parts else 0.0


def section_fraction(section: str) -> float:
    return _mean(SECTIONS[section])


def overall_fraction() -> float:
    return _mean(PAGES.values())


def fill_badge(frac: float | None, key: str | None = None) -> None:
    """Fill badge; at 100 % it is yellow until validated (then green), with the Validated switch beside it."""
    if frac is None:
        return
    ok = validated(key) if key else True
    color = "orange" if frac < 1 else ("green" if ok else "yellow")
    st.badge(f"{frac:.0%} filled", icon=":material/check_circle:" if frac >= 1 else ":material/error:", color=color)
    if key and frac >= 1:
        validate_toggle(key)


def tab_done(page_file: str, tab: str) -> None:
    """Start of a tab's content: its tables count toward this tab; shows the tab's fill badge."""
    st.session_state["_fill_ctx"] = f"{page_file}:{tab}"
    with st.container(horizontal=True, vertical_alignment="center"):
        fill_badge(fraction(f"{page_file}:{tab}"), key=f"{page_file}:{tab}")


DONE_MARK = ":green[:material/check_circle:]"
FILLED_MARK = ":yellow[:material/check_circle:]"  # 100 % filled, not validated yet
TODO_MARK = ":orange[:material/error:]"

# Validation phase: a complete page / tab / table shows a yellow tick until you validate it (green).
VALID_PREFIX = "valid:"


def validations() -> set[str]:
    if st.session_state.get("_valid_run") != st.session_state.get("_run_id") or "_valid" not in st.session_state:
        df = db.read_table("progress")
        st.session_state["_valid"] = {k[len(VALID_PREFIX):] for k, v in zip(df["key"], df["done"])
                                      if str(k).startswith(VALID_PREFIX) and v}
        st.session_state["_valid_run"] = st.session_state.get("_run_id")
    return st.session_state["_valid"]


def validated(key: str) -> bool:
    return key in validations()


def _save_validation(key: str, wk: str) -> None:
    db.upsert("progress", {"key": VALID_PREFIX + key}, {"done": bool(st.session_state[wk])})
    st.session_state.pop("_valid_run", None)


def validate_toggle(key: str, label: str = "Validated") -> None:
    """Switch that turns a complete item's yellow tick green."""
    wk = f"validate__{key}"
    st.toggle(label, value=validated(key), key=wk, on_change=_save_validation, args=(key, wk),
              help="Turn on after checking the values: the yellow tick becomes green.")


def page_tag(page: PageDef, data) -> str:
    """Sidebar tag; "{n}" becomes the weekly entries for this account's membership setting."""
    if not page.entries:
        return page.tag
    from aion import calc

    acts = data.activities[data.activities["category"] == page.entries]
    if acts.empty:
        return ""
    n = calc.weekly_max_attempts(acts.iloc[0], bool(data.settings.get("account_membership", True)), data.settings)
    return page.tag.format(n=f"{n:g}" if n is not None else "∞")


def mark(done: bool, key: str | None = None) -> str:
    """! while incomplete; when complete: yellow until `key` is validated, then green."""
    if not done:
        return TODO_MARK
    return DONE_MARK if key is None or validated(key) else FILLED_MARK


def tab_label(page_file: str, tab: str, label: str) -> str:
    """Inner-tab label led by a green tick when filled, an exclamation mark otherwise, plus its fill %."""
    frac = fraction(f"{page_file}:{tab}")
    if frac is None:
        return label
    return f"{mark(frac >= 1, f'{page_file}:{tab}')} {label} · {frac:.0%}"


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
