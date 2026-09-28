"""Tiered reward tables shared by their page and the sidebar completion."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TierSpec:
    category: str
    key: str
    groups: dict | list
    columns: list[tuple[str, str, str]]  # (label, currency key, pool suffix)
    tier_label: str = "Tier"
    group_names: tuple[str, ...] = ("Group", "Tier")
    group_icons: tuple[str, ...] = ("layers", "stairs")


NIGHTMARE_LEVELS = [f"Level {lv}" for lv in range(1, 11)]
NIGHTMARE = TierSpec(
    category="Nightmare", key="nightmare_levels", tier_label="Level", group_names=("Layer", "Tier"),
    groups={f"Layer {n}": {f"Tier {t}": NIGHTMARE_LEVELS for t in range(1, 4)} for n in range(1, 5)},
    # "|gs" / "|first" suffixes: stored for reference, never counted in the plan.
    columns=[("Suggested item level", "gear_score", "|gs"),
             ("Phantasmal Fragments (repeat)", "nightmare_currency", ""),
             ("First clear (one-time)", "nightmare_currency", "|first")],
)

# page file -> spec whose tables decide the page's completion
AUTO_DONE = {"nightmare": NIGHTMARE}
