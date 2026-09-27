"""Researched instanced-PvE data (web research, 2026-09-26).

Primary numbers are the Global client reward lines datamined by dbaion2.ru ("Global database, data from
the game client"); they are tagged global_lst / provisional. KR values (per claim = 40 Odyle) are kept in
the notes. GS = Item Level. Recommended GS = entry + ~200 (what parties ask for, mmo-codex) unless a
source gives a value.
"""
from __future__ import annotations

import json
import sqlite3

DB = "https://dbaion2.ru/en/dungeons/"
ENTRY = "https://game8.co/games/Aion-2/archives/613829 ; https://aion2.wiki.fextralife.com/Expeditions"
KR_JUL = "https://www.inven.co.kr/board/aion2/6444/2064"
KR_DEC = "https://www.inven.co.kr/board/aion2/6388/46532"
FALLOFF = ("Kinah falloff per server-week (KR): Exploration 100% up to 7 claims, 60% to 14, 20% to 20, 0% from 21; "
           "Conquest 100% up to 63 (pre-S3 84), then 80/60/40/20%. Leaving without claiming uses a weekly "
           "unclaimed-cube allowance (~10, shared per server).")

# dungeon, star tier, minutes (exploration, conquest)
DUNGEONS = [
    ("Krao Cave", 1, 8, 12), ("Draupnir", 1, 10, 14), ("Urugugu Canyon", 2, 10, 15),
    ("Vakron Sky Island", 2, 12, 16), ("Fire Temple", 3, 12, 18), ("Ferocious Horn Den", 3, 12, 18),
]

# (dungeon, mode) -> entry GS, recommended GS, rewards per claim (Global client line), KR note
EXPEDITION = {
    ("Krao Cave", "Exploration"): (200, 400, {"kinah_bound": 25000, "enhancement_stones": 1000},
                                   "Lv20. KR (Dec 2025): 150k Kinah, 1,000 stones per claim."),
    ("Krao Cave", "Conquest Normal"): (1000, 1200, {"kinah_unbound": 70000, "enhancement_stones": 2000, "amplify_fragments": 2},
                                       "Lv45. KR (Dec 2025): 300k Kinah, 2,000 stones per claim."),
    ("Krao Cave", "Conquest Hard"): (2400, 2600, {"kinah_unbound": 170000, "enhancement_stones": 2000, "amplify_fragments": 5},
                                     "KR (Jul 2026): 510k bound per claim."),
    ("Draupnir", "Exploration"): (None, None, {"kinah_bound": 40000, "enhancement_stones": 1300},
                                  "Lv45 unlock on Global (IGGM). KR: 300k Kinah, 1,500 stones."),
    ("Draupnir", "Conquest Normal"): (1000, 1200, {"kinah_unbound": 70000},
                                      "KR: 600k (Dec 2025); 300k bound (Jul 2026). Stones/fragments not in the client line."),
    ("Draupnir", "Conquest Hard"): (2400, 2600, {"kinah_unbound": 170000}, "KR (Jul 2026): 510k bound."),
    ("Urugugu Canyon", "Exploration"): (None, None, {"kinah_bound": 30000, "enhancement_stones": 1100},
                                        "Lv28 (Global). KR: 180k Kinah, 1,000 stones."),
    ("Urugugu Canyon", "Conquest Normal"): (1600, 1800, {"kinah_unbound": 100000, "amplify_fragments": 4},
                                            "KR: 350k; 405k bound (Jul 2026)."),
    ("Urugugu Canyon", "Conquest Hard"): (2500, 2700, {"kinah_unbound": 170000, "amplify_fragments": 5},
                                          "KR (Jul 2026): 510k bound."),
    ("Vakron Sky Island", "Exploration"): (1600, 1800, {"kinah_bound": 50000, "enhancement_stones": 1400},
                                           "KR Kinah not found."),
    ("Vakron Sky Island", "Conquest Normal"): (1600, 1800, {"kinah_unbound": 100000},
                                               "Recommended ~1,800. KR (Jul 2026): 405k bound."),
    ("Vakron Sky Island", "Conquest Hard"): (2500, 2700, {"kinah_unbound": 170000}, "KR (Jul 2026): 510k bound."),
    ("Fire Temple", "Exploration"): (None, None, {"kinah_bound": 35000, "enhancement_stones": 1200},
                                     "Lv35 (Global). KR (Dec 2025): 220k Kinah, 1,500 stones."),
    ("Fire Temple", "Conquest Normal"): (2200, 2500, {"kinah_unbound": 140000, "amplify_fragments": 5},
                                         "Recommended 2,400–2,600 (savetip). KR: 450k unbound + 2,000 stones per claim "
                                         "(Dec 2025); 510k per claim, 100% bound (Jul 2026). 400k/run not confirmed by "
                                         "any source. Pity: Enraged Kromede accessory selector after 28 claims. "
                                         "Clear ~15–20 min. " + KR_DEC + " ; https://game.savetip.co.kr/aion2-fire-temple-guide/"),
    ("Fire Temple", "Conquest Hard"): (2600, 2800, {"kinah_unbound": 170000, "amplify_fragments": 5},
                                       "KR (Jul 2026): 510k unbound + 510k bound per 80 Odyle (50/50)."),
    ("Ferocious Horn Den", "Exploration"): (None, None, {"kinah_bound": 60000, "enhancement_stones": 1500},
                                            "Entry not found."),
    ("Ferocious Horn Den", "Conquest Normal"): (2200, 2400, {"kinah_unbound": 140000},
                                                "KR: 510k per claim (Normal bound)."),
    ("Ferocious Horn Den", "Conquest Hard"): (2600, 2800, {"kinah_unbound": 170000}, "KR: 510k (Hard 50/50 bound)."),
}

TRANSCENDENCE = [
    # stage, entry GS, rewards per claim (Global client line)
    (1, 1200, {"kinah_unbound": 100000, "amplify_fragments": 7, "enhancement_stones": 2000, "silentium": 10}),
    (2, 1500, {"kinah_unbound": 120000, "amplify_fragments": 8, "enhancement_stones": 2000, "silentium": 10}),
    (3, 1800, {"kinah_unbound": 140000, "amplify_fragments": 10, "enhancement_stones": 2000, "silentium": 10}),
    (4, 2200, {"kinah_unbound": 160000, "amplify_fragments": 12, "enhancement_stones": 2000, "silentium": 10}),
]


def _set_rewards(conn: sqlite3.Connection, aid: int, rewards: dict) -> None:
    conn.execute("DELETE FROM activity_rewards WHERE activity_id = ?", (aid,))
    for k, v in rewards.items():
        if v:
            conn.execute("INSERT INTO activity_rewards (activity_id, currency_key, amount) VALUES (?, ?, ?)", (aid, k, v))


def _upsert_activity(conn: sqlite3.Connection, find_names: list[str], name: str, category: str, rewards: dict,
                     order: int, **fields) -> None:
    from aion.seed import _act

    row = None
    for n in find_names:
        row = conn.execute("SELECT id FROM activities WHERE name = ?", (n,)).fetchone()
        if row:
            break
    if row:
        vals = {"name": name, "category": category, "sort_order": order, **fields}
        conn.execute(f"UPDATE activities SET {', '.join(f'{k} = ?' for k in vals)} WHERE id = ?", (*vals.values(), row[0]))
        aid = row[0]
    else:
        act, _ = _act(name, category, **fields)
        act["sort_order"] = order
        aid = conn.execute(f"INSERT INTO activities ({', '.join(act)}) VALUES ({', '.join('?' for _ in act)})",
                           list(act.values())).lastrowid
    _set_rewards(conn, aid, rewards)


def migrate_dungeons_v1(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT value FROM settings WHERE key = 'seed_dungeons_v1'").fetchone():
        return
    order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM activities").fetchone()[0]
    common = dict(scope="per_character", cadence="opportunity", attempts_per_reset=None, odyle_per_claim=40,
                  reward_claims_per_attempt=1, membership_extra_claims=1, ruleset="global_lst",
                  source_status="provisional", forced_initial_claims=0, guaranteed_reward_after_claims=None,
                  guaranteed_reward_value=None, repeat_after_guarantee=1)
    for dungeon, stars, min_exp, min_conq in DUNGEONS:
        for mode in ("Exploration", "Conquest Normal", "Conquest Hard"):
            entry, rec, rewards, kr = EXPEDITION[(dungeon, mode)]
            old = [f"{dungeon} — {mode}"] + ([f"{dungeon} — Conquest"] if mode == "Conquest Normal" else [])
            order += 1
            extra = {"guaranteed_reward_after_claims": 28} if (dungeon, mode) == ("Fire Temple", "Conquest Normal") else {}
            _upsert_activity(
                conn, old, f"{dungeon} — {mode}", "Expedition", rewards, order,
                **{**common, **extra}, dungeon=dungeon, mode=mode, tier=f"{stars}★",
                entry_item_level=entry, recommended_item_level=rec,
                duration_minutes=min_exp if mode == "Exploration" else min_conq,
                main_default=1, alt_default=1,
                notes=(f"Global client reward line per claim (40 Odyle; 2 claims with membership). {kr} "
                       f"{'Exploration Kinah is bound. ' if mode == 'Exploration' else ''}{FALLOFF} "
                       f"Global launch: 6 dungeons, 5-player parties. Minutes estimated. {DB} ; {ENTRY} ; {KR_JUL}"))

    for stage, gs, rewards in TRANSCENDENCE:
        order += 1
        _upsert_activity(
            conn, ["Transcendence"] if stage == 1 else [], f"Transcendence — Stage {stage}", "Transcendence", rewards,
            order, **common, main_default=1, alt_default=0, entry_item_level=gs, recommended_item_level=gs + 200,
            duration_minutes=7, tier=f"Stage {stage}",
            notes=("Global: Deus Research Base and Shattered Arkanis, 4 stages; Rare Arcana can drop from stage 1 "
                   "(+ Arcana). Global client line per claim. KR: 7 charges/week (S3; 14 before), Kinah bound since "
                   "S3; falloff 100% up to 42 claims per server-week. Entry GS from KR S3 patch notes. "
                   "https://dbaion2.ru/en/dungeons/deuscenter/ ; https://www.inven.co.kr/board/aion2/6388/150348"))

    order += 1
    _upsert_activity(
        conn, ["Sanctuary raid", "Raid"], "Abyssal Forge: Ludra (raid)", "Raid",
        {"kinah_unbound": 1000000, "amplify_fragments": 9, "gear_drops": 1}, order,
        scope="per_character", cadence="weekly", attempts_per_reset=1, odyle_per_claim=80, membership_extra_claims=1,
        reward_claims_per_attempt=1, entry_item_level=2700, recommended_item_level=2900, duration_minutes=40,
        main_default=1, alt_default=0, ruleset="global_lst", source_status="provisional",
        notes=("Global launch raid, 10 players. KR: GS ≥ 2,700, 1 final-boss kill per week (recharge ticket 1M Kinah, "
               "1/server/week). 80 Odyle per injection, 160 with membership double. Global client: 1,000,000 unbound "
               "Kinah, 9 Amplify fragments, 10 Soul Codex, Ludra weapon/bracelet, Abyssal gear. "
               "https://dbaion2.ru/en/dungeons/reforgedabyss/ ; https://www.inven.co.kr/board/aion2/6388/162218"))

    renames = {"Daily Dungeon — Odium Storage": "Daily Dungeon — Odylium Repository",
               "Daily Dungeon — Kropakin's Vault": "Daily Dungeon — Crobakhi's Secret Depository"}
    for old, new in renames.items():
        conn.execute("UPDATE activities SET name = ?, enabled = 1, recommended_item_level = NULL, notes = notes || ? "
                     "WHERE name = ?", (new, " Present in the Global client (recommended level 30); LST had daily dungeons.", old))
    conn.execute(
        "UPDATE activities SET notes = ? WHERE name = 'Daily Dungeon — Daeva Bio-Research Base'",
        ("Enhancement Stones by score: 100 up to 10,000 at 10,000 points. KR launch 7/week per character (S3: 14/week "
         "per server). Instant-clear tickets 30k Kinah (14–21/server/week). Confirmed at the Global LST. "
         "https://aion2.wiki.fextralife.com/Daily_Dungeon ; https://shugo.gg/news/global-launch-scale-test",))
    conn.execute("UPDATE activities SET notes = notes || ? WHERE name = 'Nightmare'",
                 (" Solo boss, challenge levels 1–10 (higher clears include lower first-clear rewards). KR launch had "
                  "5 entries/day. GS not found. https://aion2.wiki.fextralife.com/Nightmare_Dungeons",))
    conn.execute("UPDATE activities SET notes = notes || ? WHERE name = 'Ascension Trial'",
                 (" Solo, timed, rotating list (was 7/week at KR launch). Rewards: Silentium, Ariel's Trace fragments, "
                  "Manastone/Soulstone chest, Enhancement Stones (amounts not found). "
                  "https://aion2.wiki.fextralife.com/Ascension+Trial",))

    # Odyle (KR values; Global membership only lists a higher cap "TBA" and 2 claims per cube).
    for k, v in {"odyle_regen_amount": 15.0, "odyle_regen_interval_hours": 3.0,
                 "odyle_regen_amount_no_membership": 10.0, "odyle_regen_interval_hours_no_membership": 3.0}.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
    note_shop = ("KR S3: 21 per server per week at 100,000 Kinah each (pre-S3: 4/character + 12/server). On Global the "
                 "Wind Breeze merchant is membership-only. https://www.inven.co.kr/board/aion2/6388/150348")
    note_morph = ("KR S3: 20 per server per week; per-character recipe removed (launch: 7/character, 50,000 Kinah + "
                  "25 Odyle + 5 Pure Odyle + 1 Refined Pure Odyle → 40). https://www.gameple.co.kr/news/articleView.html?idxno=214580")
    conn.execute("UPDATE odyle_sources SET purchases = 21, odyle_each = 40, kinah_cost_each = 100000, membership_required = 1, "
                 "enabled = 1, notes = ? WHERE name = 'Odyle shop (shared server)'", (note_shop,))
    conn.execute("UPDATE odyle_sources SET enabled = 0, notes = ? WHERE name = 'Odyle shop (per character)'",
                 ("Removed in KR S3 (pre-S3: 4 per character). " + note_shop,))
    conn.execute("UPDATE odyle_sources SET purchases = 20, odyle_each = 40, kinah_cost_each = 50000, enabled = 1, "
                 "notes = ? WHERE name = 'Substance Morph (shared server)'", (note_morph,))
    conn.execute("UPDATE odyle_sources SET enabled = 0, notes = ? WHERE name = 'Substance Morph (per character)'",
                 ("Removed in KR S3. " + note_morph,))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_dungeons_v1', 'true')")


def sort_dungeons_v2(conn: sqlite3.Connection) -> None:
    """One-time: list Expedition rows by star tier / dungeon / mode, Transcendence by stage."""
    if conn.execute("SELECT value FROM settings WHERE key = 'sort_dungeons_v2'").fetchone():
        return
    base = conn.execute("SELECT COALESCE(MIN(sort_order), 0) FROM activities WHERE category = 'Expedition'").fetchone()[0]
    names = [f"{d} — {m}" for d, *_ in DUNGEONS for m in ("Exploration", "Conquest Normal", "Conquest Hard")]
    names += [f"Transcendence — Stage {s}" for s, *_ in TRANSCENDENCE]
    for i, n in enumerate(names):
        conn.execute("UPDATE activities SET sort_order = ? WHERE name = ?", (base + i / 100, n))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sort_dungeons_v2', 'true')")
