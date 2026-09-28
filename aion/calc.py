"""Weekly plan, Odyle budget, Abyss/AP and efficiency calculations.

Pure pandas: every gameplay value comes from the database, nothing is hard-coded.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

from aion import db

# The account is bound to one server, so per-server is also per-account. Unknown is treated like per-server
# (never multiplied by character count).
SERVER_SCOPES = {"per_server", "unknown"}
SCOPES = ["per_character", "per_server", "unknown"]
CADENCES = ["none", "daily", "weekly", "seasonal", "regenerating", "event", "opportunity"]
SOURCE_STATUSES = ["confirmed", "provisional", "unknown"]
AP_CAP_CATEGORIES = ["none", "pve", "pvp", "excluded"]
CLASSES = ["Gladiator", "Chanter", "Cleric", "Assassin", "Ranger", "Sorcerer", "Spiritmaster", "Templar"]
FACTIONS = ["Asmodian", "Elyos"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
OBJECTIVES = {
    "balanced": "Balanced",
    "maximize_unbound_kinah": "Maximize unbound Kinah",
    "maximize_ap": "Maximize AP",
    "maximize_combat_progression": "Maximize combat progression",
    "maximize_custom_value_score": "Maximize custom value score",
}
KINAH_VALUE_MODES = ["Unbound only", "Unbound + bound", "Estimated Kinah value (all rewards)"]


@dataclass
class Data:
    settings: dict
    characters: pd.DataFrame
    activities: pd.DataFrame
    rewards: pd.DataFrame  # wide: index activity_id, columns currency keys
    currencies: pd.DataFrame
    char_act: pd.DataFrame
    odyle_sources: pd.DataFrame
    rulesets: pd.DataFrame


TIER_PREFIX = "tier:"


def load() -> Data:
    rewards_long = db.read_table("activity_rewards")
    if not rewards_long.empty:  # expected value per claim = amount × draws × drop chance
        rewards_long["amount"] = (rewards_long["amount"] * rewards_long["draws"].fillna(1.0)
                                  * rewards_long["chance"].fillna(100.0) / 100.0)
    currencies = db.read_table("currencies", order="sort_order, key")
    activities = db.read_table("activities", order="sort_order, id")
    if not rewards_long.empty:
        # With a chosen tier only that tier's rows count; without one, only the untiered rows
        # (tier rows have pool "tier:<label>").
        tier = rewards_long["activity_id"].map(activities.set_index("id")["reward_tier"])
        tiered = rewards_long["pool"].fillna("").str.startswith(TIER_PREFIX)
        rewards_long = rewards_long[(tier.isna() & ~tiered) | (rewards_long["pool"] == TIER_PREFIX + tier.fillna(""))]
    wide = (
        rewards_long.pivot_table(index="activity_id", columns="currency_key", values="amount", aggfunc="sum")
        if not rewards_long.empty else pd.DataFrame()
    )
    wide = wide.reindex(index=activities["id"], columns=currencies["key"]).fillna(0.0)
    return Data(
        settings=db.get_settings(),
        characters=db.read_table("characters", order="sort_order, id"),
        activities=activities,
        rewards=wide,
        currencies=currencies,
        char_act=db.read_table("character_activity"),
        odyle_sources=db.read_table("odyle_sources", order="id"),
        rulesets=db.read_table("rulesets"),
    )


# ------------------------------------------------------------------ helpers

def _num(v, default=0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
            return default
    except (TypeError, ValueError):
        pass
    return float(v)


def status_label(ruleset: str, source_status: str) -> str:
    if source_status == "unknown":
        return "Unknown"
    return {
        "global": "Confirmed Global" if source_status == "confirmed" else "Global (provisional)",
        "global_lst": "Global LST / pre-launch",
        "kr_tw_reference": "KR/TW reference",
        "user_override": "User override",
    }.get(ruleset, "Unknown")


STATUS_COLORS = {
    "Confirmed Global": "green",
    "Global (provisional)": "blue",
    "Global LST / pre-launch": "blue",
    "KR/TW reference": "orange",
    "User override": "violet",
    "Unknown": "gray",
}


def week_start(settings: dict, now: dt.datetime | None = None) -> dt.date:
    """Date of the most recent weekly reset."""
    now = now or dt.datetime.now()
    day = WEEKDAYS.index(settings.get("reset_day", "Wednesday"))
    hh, mm = (int(x) for x in str(settings.get("reset_time", "05:00")).split(":")[:2])
    candidate = dt.datetime.combine(now.date(), dt.time(hh, mm)) - dt.timedelta(days=(now.weekday() - day) % 7)
    if candidate > now:
        candidate -= dt.timedelta(days=7)
    return candidate.date()


def weekly_max_attempts(act: pd.Series, membership: bool, settings: dict) -> float | None:
    """Maximum attempts per week. None = unbounded (limited by Odyle / plan)."""
    sfx = "_membership" if membership else ""
    hours = act.get(f"recharge_hours{sfx}")
    if hours is not None and pd.notna(hours) and float(hours) > 0:
        return _num(act.get(f"recharge_amount{sfx}")) * 168.0 / float(hours)
    base = act.get("attempts_per_reset")
    bonus = _num(act.get("membership_bonus_attempts")) if membership else 0.0
    cad = act.get("cadence")
    if cad == "none":
        return 0.0
    if cad == "regenerating":
        return _num(act.get("charges_per_day")) * 7 + bonus
    if base is None or pd.isna(base):
        return None if cad in ("opportunity", "event") else 0.0
    per_reset = float(base) + bonus
    if cad == "daily":
        return per_reset * 7
    if cad == "seasonal":
        return per_reset / max(_num(settings.get("season_weeks"), 12), 1)
    return per_reset


def claims_per_attempt(act: pd.Series, membership: bool, use_extra: bool) -> float:
    extra = _num(act.get("membership_extra_claims")) if (membership and use_extra) else 0.0
    return _num(act.get("reward_claims_per_attempt"), 1.0) + extra


def currency_values(data: Data, objective: str) -> dict[str, pd.Series]:
    """Per-currency value vectors used for scoring rewards."""
    cur = data.currencies.set_index("key")
    s = data.settings
    zero = pd.Series(0.0, index=cur.index)

    kinah = zero.copy()
    mode = s.get("kinah_value_mode", "Unbound + bound")
    if mode == "Estimated Kinah value (all rewards)":
        kinah = cur["estimated_kinah_value"].fillna(0.0).astype(float)
    else:
        kinah.loc[kinah.index == "kinah_unbound"] = 1.0
        if mode == "Unbound + bound":
            kinah.loc[kinah.index == "kinah_bound"] = 1.0
    if not s.get("include_bound_kinah", True):
        kinah.loc[kinah.index == "kinah_bound"] = 0.0

    unbound = zero.copy()
    unbound.loc[unbound.index == "kinah_unbound"] = 1.0
    ap = zero.copy()
    ap.loc[ap.index == "abyss_points"] = 1.0
    weight = cur["weight"].fillna(0.0).astype(float)
    progression = weight.where(cur["category"].isin(["material", "progress", "gear"]), 0.0)
    return {
        "kinah_value": kinah,
        "maximize_unbound_kinah": unbound,
        "maximize_ap": ap,
        "maximize_combat_progression": progression,
        "maximize_custom_value_score": weight,
        "value_score": weight,
    }


# ------------------------------------------------------------------ Odyle

def odyle_natural_per_week(settings: dict, membership: bool) -> float:
    if membership:
        amt, hrs = settings["odyle_regen_amount"], settings["odyle_regen_interval_hours"]
    else:
        amt, hrs = settings["odyle_regen_amount_no_membership"], settings["odyle_regen_interval_hours_no_membership"]
    return _num(amt) * (24.0 / max(_num(hrs, 3), 0.01)) * 7


def _odyle_sources(data: Data, respect_toggles: bool, include_shop: bool | None = None,
                   include_morph: bool | None = None) -> pd.DataFrame:
    s = data.settings
    shop = s["use_shop_odyle"] if include_shop is None else include_shop
    morph = s["use_morph_odyle"] if include_morph is None else include_morph
    src = data.odyle_sources.copy()
    if respect_toggles:
        src = src[src["source_type"].map(lambda t: {"shop": shop, "morph": morph}.get(t, True))]
    return src


def odyle_budget(data: Data, respect_toggles: bool = True, membership: bool | None = None) -> pd.DataFrame:
    """Weekly Odyle available per active character, by source type.

    With respect_toggles=False, purchasable/craftable amounts are shown even when the
    sidebar 'Use shop/morph Odyle' toggles are off (what each character *could* get).
    membership overrides each character's own membership for natural regeneration.
    """
    s = data.settings
    chars = active_characters(data)
    out = pd.DataFrame(index=chars["id"], columns=["natural", "shop", "morph", "other"], data=0.0)
    if chars.empty:
        return out.assign(total=0.0)
    src = _odyle_sources(data, respect_toggles)
    for _, c in chars.iterrows():
        mem = bool(c["membership"]) if membership is None else membership
        out.loc[c["id"], "natural"] = odyle_natural_per_week(s, mem)
        for _, r in src[src["scope"] == "per_character"].iterrows():
            col = r["source_type"] if r["source_type"] in out.columns else "other"
            out.loc[c["id"], col] += _num(r["purchases"]) * _num(r["odyle_each"])
    pools = src[src["scope"] != "per_character"]
    for server, group in chars.groupby("server"):
        for _, r in pools.iterrows():
            amount = _num(r["purchases"]) * _num(r["odyle_each"])
            col = r["source_type"] if r["source_type"] in out.columns else "other"
            out.loc[_server_owner(group)["id"], col] += amount  # per-server purchases go to the main
    out["total"] = out[["natural", "shop", "morph", "other"]].sum(axis=1)
    return out


def dungeon_gold_curves(data: Data, max_chars: int, include_shop: bool, include_morph: bool,
                        kinah: str = "total", category: str = "Expedition") -> pd.DataFrame:
    """Weekly Kinah from spending all Odyle of N characters in one dungeon (one curve per dungeon/mode).

    Odyle(N) = N × per-character Odyle (regen + per-character shop/morph) + the shared server pool.
    Each claim costs its own Odyle, so Kinah = Odyle(N) / Odyle-per-claim × Kinah-per-claim.
    """
    s = data.settings
    src = _odyle_sources(data, True, include_shop, include_morph)
    mem = bool(s.get("account_membership", True))
    amount = src["purchases"].fillna(0).astype(float) * src["odyle_each"].fillna(0).astype(float)
    per_char = odyle_natural_per_week(s, mem) + amount[src["scope"] == "per_character"].sum()
    pool = amount[src["scope"] != "per_character"].sum()
    acts = data.activities[(data.activities["category"] == category) & (data.activities["odyle_per_claim"].fillna(0) > 0)]
    rows = []
    for _, a in acts.iterrows():
        r = data.rewards.loc[a["id"]] if a["id"] in data.rewards.index else pd.Series(dtype=float)
        per_claim = {"unbound": r.get("kinah_unbound", 0.0), "bound": r.get("kinah_bound", 0.0)}
        per_claim["total"] = per_claim["unbound"] + per_claim["bound"]
        for n in range(1, max_chars + 1):
            odyle = n * per_char + pool
            rows.append(dict(characters=n, dungeon=a["name"], mode=a["mode"] or "", odyle=odyle,
                             gold=odyle / float(a["odyle_per_claim"]) * per_claim[kinah]))
    return pd.DataFrame(rows)


ODYLE_COST_COLUMNS = ["kinah_cost_each", "odyle_cost_each", "pure_odyle_cost_each", "refined_odyle_cost_each"]


def odyle_source_costs(data: Data, source_type: str | None = None, respect_toggles: bool = False) -> pd.Series:
    """Weekly cost of buying/crafting Odyle sources across all active characters, per material.

    By default covers the full budget; respect_toggles=True keeps only what the plan uses
    (sidebar 'Use shop/morph Odyle').
    """
    chars = active_characters(data)
    src = _odyle_sources(data, respect_toggles)
    if source_type is not None:
        src = src[src["source_type"] == source_type]
    mult = src["scope"].map(lambda sc: len(chars) if sc == "per_character" else chars["server"].nunique()).astype(float)
    weekly = src["purchases"].fillna(0).astype(float) * mult
    return pd.Series({c: (weekly * src[c].fillna(0).astype(float)).sum() for c in ODYLE_COST_COLUMNS})


# ------------------------------------------------------------------ plan

def active_characters(data: Data) -> pd.DataFrame:
    c = data.characters[data.characters["active"].astype(bool)].copy()
    if not data.settings.get("include_alts", True):
        c = c[c["is_main"].astype(bool)]
    return c


def _server_owner(group: pd.DataFrame) -> pd.Series:
    """Character that performs server-wide content: the main, else the highest item level."""
    g = group.sort_values(["is_main", "item_level", "sort_order"], ascending=[False, False, True])
    return g.iloc[0]


def _setting_for(data: Data, char_id: int, act_id: int) -> dict:
    ca = data.char_act
    row = ca[(ca["character_id"] == char_id) & (ca["activity_id"] == act_id)]
    return row.iloc[0].to_dict() if not row.empty else {}


def is_enabled_for(act: pd.Series, char: pd.Series, setting: dict) -> bool:
    """Loop membership follows the scope: per_character → main and alts; per_server / unknown → main only."""
    return act["scope"] == "per_character" or bool(char["is_main"])


def eligible_activities(data: Data) -> pd.DataFrame:
    a = data.activities
    allowed = set(data.settings.get("allowed_rulesets") or [])
    return a[(a["cadence"] != "none") & a["ruleset"].isin(allowed)]


def build_plan(data: Data, auto_odyle: bool = True) -> pd.DataFrame:
    """One row per (character, activity) with weekly attempts, time, costs and rewards."""
    s = data.settings
    chars = active_characters(data)
    acts = eligible_activities(data)
    rows: list[dict] = []

    def add_row(char, act, attempts, max_att, alloc, setting, membership):
        use_extra = setting.get("use_extra_claim")
        use_extra = True if use_extra is None or pd.isna(use_extra) else bool(use_extra)
        cpa = claims_per_attempt(act, membership, use_extra)
        claims = attempts * cpa
        cap = act.get("weekly_claim_limit")
        if cap is not None and not pd.isna(cap):
            claims = min(claims, float(cap))
        forced = _num(act.get("forced_initial_claims"))
        done = _num(setting.get("milestone_claims_done"))
        if forced and not bool(act.get("repeat_after_guarantee", True)):
            claims = min(claims, max(forced - done, 0.0))
        attempts = claims / cpa if cpa else attempts
        rows.append(dict(
            character_id=int(char["id"]), character=char["name"], is_main=bool(char["is_main"]),
            role="Main" if char["is_main"] else "Alt", server=char["server"],
            activity_id=int(act["id"]), activity=act["name"], category=act["category"],
            scope=act["scope"], cadence=act["cadence"], allocation=alloc,
            attempts=attempts, max_attempts=max_att, claims_per_attempt=cpa, claims=claims,
            minutes=attempts * _num(act["duration_minutes"]),
            odyle=claims * _num(act["odyle_per_claim"]),
            kinah_cost=attempts * _num(act["kinah_cost"]),
            abyss_minutes=attempts * _num(act["duration_minutes"]) if act["consumes_abyss_time"] else 0.0,
            ap_cap_category=act["ap_cap_category"],
            status=status_label(act["ruleset"], act["source_status"]),
        ))

    def planned(setting):
        p = setting.get("planned_runs")
        return None if p is None or pd.isna(p) else float(p)

    for _, act in acts.iterrows():
        il_gate = _num(act.get("entry_item_level"))
        enabled = []
        for _, c in chars.iterrows():
            st_ = _setting_for(data, c["id"], act["id"])
            if is_enabled_for(act, c, st_) and _num(c["item_level"]) >= il_gate:
                enabled.append((c, st_))
        if not enabled:
            continue
        if act["scope"] == "per_character":
            for c, st_ in enabled:
                mem = bool(c["membership"])
                mx = weekly_max_attempts(act, mem, s)
                p = planned(st_)
                if mx is None:  # Odyle-limited: planned, or auto-filled below
                    if p is None and auto_odyle and _num(act["odyle_per_claim"]) > 0:
                        continue
                    add_row(c, act, p or 0.0, None, "planned", st_, mem)
                else:
                    add_row(c, act, min(p, mx) if p is not None else mx, mx, "character", st_, mem)
        else:
            # Server pools are never multiplied by character count.
            by_server: dict[str, list] = {}
            for c, st_ in enabled:
                by_server.setdefault(c["server"], []).append((c, st_))
            groups = list(by_server.items())
            mem = bool(s.get("account_membership", True))
            for _, members in groups:
                members.sort(key=lambda cs: (not cs[0]["is_main"], -_num(cs[0]["item_level"]), cs[0]["sort_order"]))
                pool = weekly_max_attempts(act, mem, s)
                remaining = pool if pool is not None else math.inf
                for c, st_ in members:
                    p = planned(st_)
                    take = min(p if p is not None else remaining, remaining)
                    if take == math.inf or (take <= 0 and p is None):
                        continue  # unbounded pool without planned runs, or pool exhausted
                    add_row(c, act, take, pool, "server pool", st_, mem)
                    remaining -= take

    plan = pd.DataFrame(rows)
    if auto_odyle:
        plan = _auto_fill_odyle(data, plan, chars, acts)
    plan = _clip_abyss_time(data, plan, chars)
    return _attach_rewards(data, plan)


def _clip_abyss_time(data: Data, plan: pd.DataFrame, chars: pd.DataFrame) -> pd.DataFrame:
    """Limit Abyss-time activities to each character's weekly allowance (lowest AP/minute cut first)."""
    if plan.empty:
        return plan
    s = data.settings
    ap = data.rewards["abyss_points"] if "abyss_points" in data.rewards else pd.Series(0.0, index=data.rewards.index)
    for _, c in chars.iterrows():
        allowed = ((s["abyss_membership_weekly_hours"] if c["membership"] else s["abyss_weekly_hours"])
                   + s["abyss_rift_stone_hours"]) * 60.0
        mask = (plan["character_id"] == c["id"]) & (plan["abyss_minutes"] > 0)
        over = plan.loc[mask, "abyss_minutes"].sum() - allowed
        if over <= 1e-9:
            continue
        per_min = {i: ap.get(plan.at[i, "activity_id"], 0.0) * plan.at[i, "claims_per_attempt"]
                   / max(plan.at[i, "abyss_minutes"] / max(plan.at[i, "attempts"], 1e-9), 1e-9) for i in plan.index[mask]}
        for i in sorted(per_min, key=per_min.get):
            if over <= 1e-9:
                break
            dur = plan.at[i, "abyss_minutes"] / plan.at[i, "attempts"]
            cut = min(plan.at[i, "attempts"], math.ceil(over / dur - 1e-9))
            frac = (plan.at[i, "attempts"] - cut) / plan.at[i, "attempts"]
            for col in ("attempts", "claims", "minutes", "odyle", "kinah_cost", "abyss_minutes"):
                plan.at[i, col] *= frac
            plan.at[i, "allocation"] += " (Abyss time cap)"
            over -= cut * dur
    return plan


def _auto_fill_odyle(data: Data, plan: pd.DataFrame, chars: pd.DataFrame, acts: pd.DataFrame) -> pd.DataFrame:
    """Spend each character's remaining Odyle on the best eligible Odyle activities."""
    budget = odyle_budget(data)
    values = currency_values(data, data.settings.get("objective", "balanced"))
    objective = data.settings.get("objective", "balanced")
    score_vec = values["kinah_value"] if objective == "balanced" else values[objective]
    rows = []
    for _, c in chars.iterrows():
        spent = plan.loc[plan["character_id"] == c["id"], "odyle"].sum() if not plan.empty else 0.0
        left = float(budget.loc[c["id"], "total"]) - spent if c["id"] in budget.index else 0.0
        cands = []
        for _, act in acts.iterrows():
            if act["scope"] != "per_character" or _num(act["odyle_per_claim"]) <= 0:
                continue
            if weekly_max_attempts(act, bool(c["membership"]), data.settings) is not None:
                continue
            st_ = _setting_for(data, c["id"], act["id"])
            if st_.get("planned_runs") is not None and not pd.isna(st_.get("planned_runs")):
                continue
            if not is_enabled_for(act, c, st_) or _num(c["item_level"]) < _num(act.get("entry_item_level")):
                continue
            per_claim = float((data.rewards.loc[act["id"]] * score_vec.reindex(data.rewards.columns).fillna(0)).sum())
            forced_left = max(_num(act.get("forced_initial_claims")) - _num(st_.get("milestone_claims_done")), 0.0)
            milestone_bonus = 0.0
            if forced_left and _num(act.get("guaranteed_reward_after_claims")):
                milestone_bonus = _num(act.get("guaranteed_reward_value")) / _num(act["guaranteed_reward_after_claims"])
            cands.append((forced_left > 0, per_claim / _num(act["odyle_per_claim"]), act, st_, forced_left, milestone_bonus))
        # Forced milestone claims first, then by value per Odyle.
        cands.sort(key=lambda x: (not x[0], -x[1]))
        for forced_first, _, act, st_, forced_left, _ in cands:
            mem = bool(c["membership"])
            use_extra = st_.get("use_extra_claim")
            use_extra = True if use_extra is None or pd.isna(use_extra) else bool(use_extra)
            cpa = claims_per_attempt(act, mem, use_extra)
            odyle_per_attempt = cpa * _num(act["odyle_per_claim"])
            if odyle_per_attempt <= 0 or left < odyle_per_attempt:
                continue
            n = math.floor(left / odyle_per_attempt)
            if forced_first and not bool(act["repeat_after_guarantee"]):
                n = min(n, math.ceil(forced_left / cpa))
            cap = act.get("weekly_claim_limit")
            if cap is not None and not pd.isna(cap):
                n = min(n, math.floor(float(cap) / cpa))
            if n <= 0:
                continue
            left -= n * odyle_per_attempt
            rows.append(dict(
                character_id=int(c["id"]), character=c["name"], is_main=bool(c["is_main"]),
                role="Main" if c["is_main"] else "Alt", server=c["server"],
                activity_id=int(act["id"]), activity=act["name"], category=act["category"],
                scope=act["scope"], cadence=act["cadence"], allocation="auto Odyle",
                attempts=float(n), max_attempts=None, claims_per_attempt=cpa, claims=n * cpa,
                minutes=n * _num(act["duration_minutes"]), odyle=n * odyle_per_attempt,
                kinah_cost=n * _num(act["kinah_cost"]),
                abyss_minutes=n * _num(act["duration_minutes"]) if act["consumes_abyss_time"] else 0.0,
                ap_cap_category=act["ap_cap_category"], status=status_label(act["ruleset"], act["source_status"]),
            ))
    if rows:
        plan = pd.concat([plan, pd.DataFrame(rows)], ignore_index=True) if not plan.empty else pd.DataFrame(rows)
    return plan


def _attach_rewards(data: Data, plan: pd.DataFrame) -> pd.DataFrame:
    keys = list(data.rewards.columns)
    if plan.empty:
        return pd.DataFrame(columns=["character_id", "character", "role", "activity_id", "activity", "category",
                                     "attempts", "claims", "minutes", "odyle", "hours", *keys,
                                     "kinah_value", "value_score"])
    per_claim = data.rewards.reindex(plan["activity_id"]).reset_index(drop=True)
    totals = per_claim.mul(plan["claims"].values, axis=0)
    plan = pd.concat([plan.reset_index(drop=True), totals], axis=1)
    vals = currency_values(data, "balanced")
    plan["kinah_value"] = totals.mul(vals["kinah_value"].reindex(keys).fillna(0).values, axis=1).sum(axis=1)
    plan["value_score"] = totals.mul(vals["value_score"].reindex(keys).fillna(0).values, axis=1).sum(axis=1)
    plan["hours"] = plan["minutes"] / 60.0
    return plan


def per_hour(df: pd.DataFrame, col: str) -> pd.Series:
    return (df[col] / (df["minutes"] / 60.0)).where(df["minutes"] > 0)


# ------------------------------------------------------------------ Abyss / AP

def abyss_summary(data: Data, plan: pd.DataFrame) -> pd.DataFrame:
    s = data.settings
    chars = active_characters(data)
    out = []
    for _, c in chars.iterrows():
        p = plan[plan["character_id"] == c["id"]] if not plan.empty else plan
        allowance = (s["abyss_membership_weekly_hours"] if c["membership"] else s["abyss_weekly_hours"]) + s["abyss_rift_stone_hours"]
        ap = lambda cat: float(p.loc[p["ap_cap_category"] == cat, "abyss_points"].sum()) if "abyss_points" in p else 0.0
        out.append(dict(
            character=c["name"], abyss_hours_allowed=float(allowance),
            abyss_hours_used=float(p["abyss_minutes"].sum() / 60.0) if not p.empty else 0.0,
            pve_ap=ap("pve"), pvp_ap=ap("pvp"), uncapped_ap=ap("none") + ap("excluded"),
            pve_ap_cap=float(s["pve_ap_weekly_cap"]), pvp_ap_cap=float(s["pvp_ap_weekly_cap"]),
        ))
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df["abyss_time_pct"] = (df["abyss_hours_used"] / df["abyss_hours_allowed"]).where(df["abyss_hours_allowed"] > 0)
    df["pve_cap_pct"] = (df["pve_ap"] / df["pve_ap_cap"]).where(df["pve_ap_cap"] > 0)
    df["pvp_cap_pct"] = (df["pvp_ap"] / df["pvp_ap_cap"]).where(df["pvp_ap_cap"] > 0)
    df["effective_ap"] = (
        df["pve_ap"].clip(upper=df["pve_ap_cap"].where(df["pve_ap_cap"] > 0, math.inf))
        + df["pvp_ap"].clip(upper=df["pvp_ap_cap"].where(df["pvp_ap_cap"] > 0, math.inf))
        + df["uncapped_ap"]
    )
    return df


# ------------------------------------------------------------------ dungeon calculator

def dungeon_table(data: Data, category: str | None = "Expedition", membership: bool = True) -> pd.DataFrame:
    a = data.activities if category is None else data.activities[data.activities["category"] == category]
    if a.empty:
        return pd.DataFrame()
    r = data.rewards.reindex(a["id"]).reset_index(drop=True)
    a = a.reset_index(drop=True)
    cpa = a.apply(lambda x: claims_per_attempt(x, membership, True), axis=1)
    hours = a["duration_minutes"].astype(float) / 60.0
    odyle_run = cpa * a["odyle_per_claim"].astype(float)
    kin_u = r.get("kinah_unbound", 0.0) * cpa
    kin_b = r.get("kinah_bound", 0.0) * cpa
    ap = r.get("abyss_points", 0.0) * cpa
    enh = r.get("enhancement_stones", 0.0) * cpa
    div = lambda num, den: (num / den).where(den > 0)
    return pd.DataFrame({
        "Activity": a["name"], **{k: a[c].fillna("").astype(str) for k, c in (("Dungeon", "dungeon"), ("Mode", "mode"), ("Tier", "tier"))},
        "Required GS": a["entry_item_level"], "Claims / run": cpa,
        "Total Odyle / run": odyle_run, "Total Kinah / run": kin_u + kin_b,
        "Unbound Kinah / hour": div(kin_u, hours), "Bound Kinah / hour": div(kin_b, hours),
        "AP / hour": div(ap, hours), "Claims / hour": div(cpa, hours),
        "Kinah / Odyle": div(kin_u + kin_b, odyle_run), "AP / Odyle": div(ap, odyle_run),
        "Enhancement Stones / hour": div(enh, hours),
        "Status": [status_label(x, y) for x, y in zip(a["ruleset"], a["source_status"])],
    })
