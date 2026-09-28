"""Default data. Every value is a planning reference and is editable in the app.

Placeholder reward numbers are tagged source_status='unknown' so they are never
mistaken for confirmed Global values.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

DEFAULT_SETTINGS: dict = {
    "account_membership": True,
    "allowed_rulesets": ["global", "global_lst", "kr_tw_reference", "user_override"],
    "weekly_available_hours": 35.0,
    "minimum_main_hours": 12.0,
    "include_alts": True,
    "objective": "balanced",
    "daily_play_hours": 14.0,
    "break_hours_per_day": 1.0,
    "start_date": dt.date.today().isoformat(),
    "allow_block_split": True,
    "reset_day": "Wednesday",
    "reset_time": "05:00",
    "kinah_value_mode": "Unbound + bound",
    "include_bound_kinah": True,
    "use_shop_odyle": False,
    "use_morph_odyle": False,
    "odyle_regen_amount": 15.0,
    "odyle_regen_interval_hours": 3.0,
    "odyle_regen_amount_no_membership": 15.0,
    "odyle_regen_interval_hours_no_membership": 3.0,
    "odyle_cap": 840.0,  # most Odyle stored, with membership (secondary source, Asian build)
    "odyle_cap_no_membership": 560.0,
    "season_weeks": 12.0,
    "abyss_weekly_hours": 7.0,
    "abyss_membership_weekly_hours": 14.0,
    "abyss_rift_stone_hours": 0.0,
    "pve_ap_weekly_cap": 60000.0,
    "pvp_ap_weekly_cap": 60000.0,
    "seasonal_ap_cap": 0.0,
    "ap_cap_model": "Separate PvE / PvP weekly caps (provisional — Global LST differed from KR/TW)",
    "enhancement_recovery_pct": 100.0,
    "kinah_recovery_pct": 0.0,
    "leveling_gear_strategy": "Weapon > survival-required armor upgrades",
}

RULESETS = [
    ("global", "Confirmed Global", "green", "Verified on the Global live client."),
    ("global_lst", "Global LST / pre-launch", "blue", "Observed in the Global Launch Scale Test or pre-launch Global data."),
    ("kr_tw_reference", "KR/TW reference", "orange", "Value from KR/TW; may differ on Global."),
    ("user_override", "User override", "violet", "Your own planning value."),
]

CURRENCIES = [
    # key, name, category, tradable, bound, shared, kinah value, weight
    ("kinah_unbound", "Kinah — Unbound", "kinah", 1, 0, 0, 1.0, 0.001),
    ("kinah_bound", "Kinah — Bound", "kinah", 0, 1, 0, 1.0, 0.0005),
    ("abyss_points", "Abyss Points (AP)", "ap", 0, 1, 0, None, 0.01),
    ("odyle_energy", "Odyle Energy", "currency", 0, 1, 0, None, 0.5),
    ("enhancement_stones", "Enhancement Stones", "material", 0, 1, 0, 500.0, 1.0),
    ("potential_stones", "Potential Stones", "material", 0, 1, 0, None, 1.0),
    ("abyss_potential_stones", "Abyss Potential Stones", "material", 0, 1, 0, None, 1.0),
    ("amplify_fragments", "Amplify Stone Fragments", "material", 0, 1, 0, None, 1.0),
    ("soul_crystals", "Soul Crystals", "material", 0, 1, 0, None, 1.0),
    ("stigma_shards", "Stigma Shards", "material", 0, 1, 0, None, 0.5),
    ("manastones", "Manastone/Soulstone Chest", "material", 1, 0, 0, None, 1.0),
    ("nightmare_currency", "Phantasmal Fragments", "currency", 0, 1, 0, None, 0.2),
    ("trial_currency", "Trial Currency / Proof / Subjugation Mark", "currency", 0, 1, 0, None, 0.2),
    ("silver_medals", "Silver Medals", "currency", 0, 1, 0, None, 1.0),
    ("hidden_cube_keys", "Hidden Cube Keys", "currency", 0, 1, 1, None, 3.0),
    ("arcana_rewards", "Arcana-related rewards", "progress", 0, 1, 0, None, 2.0),
    ("daevanion_materials", "Daevanion-related materials", "progress", 0, 1, 0, None, 2.0),
    ("gear_drops", "Gear Drops", "gear", 0, 1, 0, None, 10.0),
    ("pity_progress", "Pity / Guaranteed Reward Progress", "progress", 0, 1, 0, None, 0.0),
    ("rank_points", "Rank Points", "progress", 0, 1, 0, None, 0.01),
    ("gear_score", "Gear Score (GS)", "progress", 0, 1, 0, None, 1.0),
    ("daevanion_points", "Daevanion Points", "progress", 0, 1, 0, None, 5.0),
    ("skill_points", "Skill Points", "progress", 0, 1, 0, None, 5.0),
    ("experience", "Experience", "progress", 0, 1, 0, None, 0.0),
    ("soul_codex", "Soul Codex", "material", 0, 1, 0, None, 1.0),
    ("artwork_scraps", "Artwork scraps", "material", 0, 1, 0, None, 0.5),
    ("seed_of_detection", "Seed of Detection", "material", 0, 1, 0, None, 0.5),
    ("odyle_material", "Odyle", "material", 0, 1, 0, None, 0.2),
    ("fine_odyle", "Fine Odyle", "material", 0, 1, 0, None, 0.5),
    ("pure_odyle", "Pure Odyle", "material", 0, 1, 0, None, 1.0),
    ("radiant_odyle", "Radiant Odyle", "material", 0, 1, 0, None, 3.0),
    ("refining_stone", "Refining Stone", "material", 0, 1, 0, None, 0.2),
    ("expert_refining_stone", "Expert's Refining Stone", "material", 0, 1, 0, None, 0.5),
    ("artisan_refining_stone", "Artisan's Refining Stone", "material", 0, 1, 0, None, 2.0),
    ("artisan_ultimate_refining_stone", "Artisan's Ultimate Refining Stone", "material", 0, 1, 0, None, 5.0),
    ("gear_unique", "Unique gear", "gear", 0, 1, 0, None, 10.0),
    ("gear_epic", "Epic gear", "gear", 0, 1, 0, None, 5.0),
    ("gear_rare", "Rare gear", "gear", 0, 1, 0, None, 2.0),
    ("gear_common", "Common gear", "gear", 0, 1, 0, None, 0.5),
    ("gear_common_rare", "Common/Rare gear", "gear", 0, 1, 0, None, 1.0),
    ("balaur_essence", "Balaur's Essence", "material", 0, 1, 0, None, 1.0),
    ("thick_balaur", "Thick Balaur material", "material", 0, 1, 0, None, 1.0),
    ("manastone_soulstone", "Manastone / Soulstone", "material", 0, 1, 0, None, 0.5),
    ("wrathful_keys", "Wrathful keys (Mind / Will / Ego)", "material", 0, 1, 0, None, 3.0),
    ("scrolls_common", "Common scrolls", "material", 0, 1, 0, None, 0.2),
]

LEVELING_TEMPLATES = [
    # role, block_type, label, start, end, hours, required, critical, priority, checklist, options
    ("main", "early", "1→22", 1, 22, 2.0, 1, 1, 1,
     "Main Story Quest\nNearby Empyrean Traces / Feathers when efficient\nSealed Dungeons on the route\n"
     "Strongholds on the route\nRelevant nearby side/regional quests\nOrange / Daevanion progression quests when appropriate\n"
     "Reach the Krao Cave MSQ/Expedition breakpoint\nAvoid unnecessary resource spending during the rush",
     {"collect_feathers": True, "sealed_dungeons": True, "strongholds": True, "side_quests": "selective", "spend_odyle": False}),
    ("main", "mid", "22→45", 22, 45, 2.0, 1, 1, 5,
     "Rush MSQ to 45\nNightmare unlocks via the MSQ chain (no separate unlock block)",
     {}),
    ("main", "cleanup", "Cleanup", 45, 45, 7.0, 0, 0, 9,
     "Remaining accessible Empyrean Traces / Feathers\nSealed Dungeons\nStrongholds\nSide/regional quests\n"
     "Permanent Daevanion/skill-point progression\nAccessible enemy-faction/Rift exploration\nOther one-time progression",
     {}),
    ("alt", "early", "1→22", 1, 22, 1.5, 1, 1, 2,
     "Follow MSQ\nRoute-critical Sealed Dungeons\nReach Krao Cave\nDo not repeat shared Feather progression done on Main\n"
     "Do not claim low-value Odyle cubes during leveling",
     {"collect_feathers": False, "sealed_dungeons": True, "strongholds": False, "side_quests": "minimal", "spend_odyle": False}),
    ("alt", "mid", "22→45", 22, 45, 1.5, 1, 1, 6,
     "Rush to 45\nActivate character-specific accumulating systems (Odyle, Nightmare charges) ASAP",
     {}),
    ("alt", "cleanup", "Cleanup", 45, 45, 5.0, 0, 0, 10,
     "Character-specific permanent progression\nSkip server-shared progression already completed",
     {}),
]

ROSTER = [
    # name, class, is_main, item_level
    ("Gladiator", "Gladiator", 1, 1800),
    ("Chanter", "Chanter", 0, 1200),
    ("Cleric", "Cleric", 0, 1200),
    ("Assassin", "Assassin", 0, 1200),
]

GEAR_SLOTS = [
    ("Weapon", 10), ("Guard / off-hand", 5), ("Belt", 7),
    ("Revelation Amulet / Pendant", 8), ("Armor", 6), ("Accessories", 5),
]

PH = "Placeholder reward values — replace with Global data."


def _act(name, category, rewards=None, **kw):
    base = dict(
        name=name, category=category, enabled=1, main_default=1, alt_default=0,
        scope="unknown", cadence="weekly", attempts_per_reset=None,
        membership_bonus_attempts=0, charges_per_day=None, charge_cap=None,
        reward_claims_per_attempt=1, membership_extra_claims=0, weekly_claim_limit=None,
        duration_minutes=10, odyle_per_claim=0, kinah_cost=0, ap_cost=0, ticket_cost=0,
        entry_item_level=None, recommended_item_level=None, consumes_abyss_time=0,
        ap_cap_category="none", forced_initial_claims=0, guaranteed_reward_after_claims=None,
        guaranteed_reward_value=None, repeat_after_guarantee=1, ruleset="kr_tw_reference",
        source_status="provisional", notes="", dungeon=None, mode=None, tier=None,
    )
    base.update(kw)
    return base, rewards or {}


def _activities():
    acts = [
        _act("Daily Duties", "Daily & Weekly", {"hidden_cube_keys": 0.2, "kinah_bound": 2000},
             scope="per_server", cadence="daily", attempts_per_reset=5, duration_minutes=3,
             notes="Primary target: Hidden Cube Key. 5/day planning reference."),
        _act("Supply Requests — Daily", "Supply Requests", {"kinah_bound": 5000, "enhancement_stones": 2},
             cadence="daily", attempts_per_reset=3, duration_minutes=4, alt_default=1,
             notes="Scope configurable until final Global behavior is verified."),
        _act("Supply Requests — Weekly", "Supply Requests", {"kinah_bound": 15000, "enhancement_stones": 5},
             cadence="weekly", attempts_per_reset=3, duration_minutes=6, alt_default=1),
        _act("Supply Requests — Season", "Supply Requests", {"kinah_bound": 20000, "enhancement_stones": 10},
             cadence="seasonal", attempts_per_reset=10, duration_minutes=8, alt_default=1),
        _act("Dimensional Invasion", "Dimensional Invasion", {"kinah_bound": 8000, "enhancement_stones": 3},
             cadence="regenerating", charges_per_day=1, charge_cap=7, duration_minutes=10,
             notes="1 charge/day, cap 7 reference. Track contribution score in notes."),
        _act("Raid", "Raid", {"amplify_fragments": 5, "daevanion_materials": 3, "enhancement_stones": 10, "gear_drops": 0.2},
             attempts_per_reset=3, duration_minutes=30, notes="3/week reference; scope/rewards provisional."),
        _act("Daily Dungeon — Daeva Bio-Research Base", "Daily Dungeon", {"enhancement_stones": 15},
             scope="per_server", attempts_per_reset=14, duration_minutes=8, ruleset="global_lst",
             notes="Global LST: 14 entries/week/server. KR/TW daily dungeons not assumed."),
        _act("Shugo Festival", "Shugo Festival", {"kinah_bound": 3000, "enhancement_stones": 2},
             scope="per_server", attempts_per_reset=7, membership_bonus_attempts=7, duration_minutes=5,
             notes="KR/TW: 7/week, 14 with membership. Not Global-confirmed."),
        _act("Transcendence", "Transcendence", {"arcana_rewards": 2, "enhancement_stones": 10},
             scope="per_character", cadence="opportunity", odyle_per_claim=40, membership_extra_claims=1,
             duration_minutes=15, notes="Main-focused Odyle sink. " + PH, source_status="unknown"),
        _act("Nightmare", "Nightmare", {"nightmare_currency": 10, "kinah_bound": 5000, "enhancement_stones": 2},
             scope="per_character", cadence="regenerating", charges_per_day=2, charge_cap=14,
             duration_minutes=6, alt_default=1, notes="2 charges/day, cap 14 reference."),
        _act("Ascension Trial", "Ascension Trial", {"manastones": 3, "stigma_shards": 5, "trial_currency": 20},
             scope="per_character", attempts_per_reset=3, duration_minutes=15, alt_default=1,
             notes="3/week reference. Level-50 Trial systems excluded from the 45 launch loop."),
        _act("Command Missions — Normal", "Command Missions", {"abyss_points": 500, "hidden_cube_keys": 0.25, "soul_crystals": 2},
             scope="per_server", attempts_per_reset=12, duration_minutes=5,
             notes="12 scrolls/week/server reference. Provisional Global scope."),
    ]
    for t in range(1, 5):
        acts.append(_act(f"Abyss Command — Type {t}", "Abyss Commands", {"abyss_points": 1000, "soul_crystals": 1},
                         scope="per_server", attempts_per_reset=5, duration_minutes=8,
                         notes="4 types × 5/week = 20/week/server reference."))
    acts += [
        _act("Open Abyss (per hour)", "Abyss",
             {"abyss_points": 3000, "kinah_unbound": 10000, "potential_stones": 5, "silver_medals": 3, "rank_points": 50},
             scope="per_character", attempts_per_reset=7, membership_bonus_attempts=7, duration_minutes=60,
             consumes_abyss_time=1, ap_cap_category="pve",
             notes="One attempt = one hour of Abyss time. " + PH, source_status="unknown"),
        _act("Abyss Corridor", "Abyss", {"abyss_points": 4000, "kinah_unbound": 5000, "abyss_potential_stones": 2},
             scope="per_character", cadence="opportunity", attempts_per_reset=3, duration_minutes=20,
             consumes_abyss_time=1, ap_cap_category="excluded",
             notes="Opportunity activity: attempts = availability events/week. " + PH, source_status="unknown"),
        _act("Arena 5v5 — rewarded matches", "Instanced PvP", {"abyss_points": 300, "silver_medals": 2},
             scope="per_character", attempts_per_reset=10, duration_minutes=10, ap_cap_category="pvp",
             notes="Separate from Abyss time. Gear not equalized (ruleset)."),
        _act("Battlefield 10v10 — win rewards", "Instanced PvP", {"abyss_points": 800, "silver_medals": 5},
             scope="per_character", attempts_per_reset=3, duration_minutes=30, ap_cap_category="pvp",
             notes="3 weekly win rewards. Duration should include expected losses."),
        _act("Battlefield 10v10 — participation rewards", "Instanced PvP", {"abyss_points": 300, "silver_medals": 2},
             scope="per_character", attempts_per_reset=3, duration_minutes=15, ap_cap_category="pvp",
             notes="3 weekly participation rewards. Gear equalized (ruleset)."),
    ]
    dungeons = [
        # dungeon, run minutes, entry IL, rec IL, kinah bound exp/conq, unbound exp/conq, enh, amplify
        ("Krao Cave", 8, 0, 600, (20000, 30000), (3000, 6000), (4, 6), (0, 1)),
        ("Fire Temple", 10, 900, 1300, (30000, 45000), (5000, 9000), (6, 9), (1, 2)),
        ("Draupnir", 12, 1300, 1700, (40000, 60000), (7000, 12000), (8, 12), (2, 3)),
        ("Vakron Sky Island", 15, 1700, 2100, (55000, 80000), (9000, 16000), (10, 15), (3, 4)),
    ]
    for tier, (dg, mins, il, rec, kb, ku, enh, amp) in enumerate(dungeons, start=1):
        for i, mode in enumerate(("Exploration", "Conquest")):
            milestone = {}
            if mode == "Exploration" and dg in ("Draupnir", "Vakron Sky Island"):
                milestone = dict(forced_initial_claims=10, guaranteed_reward_after_claims=10,
                                 guaranteed_reward_value=60 if dg == "Draupnir" else 90, repeat_after_guarantee=0)
            acts.append(_act(
                f"{dg} — {mode}", "Expedition",
                {"kinah_bound": kb[i], "kinah_unbound": ku[i], "enhancement_stones": enh[i],
                 "amplify_fragments": amp[i], "pity_progress": 1 if mode == "Exploration" else 0},
                dungeon=dg, mode=mode, tier=f"T{tier}", scope="per_character", cadence="opportunity",
                odyle_per_claim=40, membership_extra_claims=1, alt_default=1,
                duration_minutes=mins + (2 if mode == "Conquest" else 0),
                entry_item_level=il + (200 if mode == "Conquest" else 0),
                recommended_item_level=rec + (200 if mode == "Conquest" else 0),
                source_status="unknown", ruleset="user_override",
                notes=("Guaranteed progression reward after initial claims. " if milestone else "") + PH,
                **milestone,
            ))
    return acts


ODYLE_SOURCES = [
    ("Odyle shop (per character)", "shop", "per_character", 4, 40),
    ("Odyle shop (shared server)", "shop", "per_server", 16, 40),
    ("Substance Morph (per character)", "morph", "per_character", 4, 40),
    ("Substance Morph (shared server)", "morph", "per_server", 16, 40),
]

SOURCES = [
    ("global_lst", "Global Launch Scale Test observations", "", "provisional",
     "September LST capped at level 37; 1→45 times are estimates."),
    ("kr_tw_reference", "NCSoft KR/TW patch notes", "", "provisional", "Mechanics introduced/changed in KR/TW."),
    ("user_override", "Community guides", "", "provisional", "Use only when official values are unavailable."),
]


def add_character_defaults(conn: sqlite3.Connection, character_id: int, is_main: bool) -> None:
    """Create leveling blocks and gear slots for a new character."""
    role = "main" if is_main else "alt"
    order_base = conn.execute("SELECT COALESCE(MAX(schedule_order), 0) FROM leveling_blocks").fetchone()[0]
    rows = conn.execute(
        "SELECT block_type, label, start_level, end_level, hours, required, critical FROM leveling_templates "
        "WHERE role = ? ORDER BY priority", (role,)
    ).fetchall()
    for i, (bt, label, s, e, h, req, crit) in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO leveling_blocks (character_id, block_type, label, start_level, end_level, hours, required, critical, schedule_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (character_id, bt, label, s, e, h, req, crit, order_base + i),
        )
    for slot, prio in GEAR_SLOTS:
        conn.execute(
            "INSERT INTO gear_slots (character_id, profile, slot, priority_score) VALUES (?, 'pve', ?, ?)",
            (character_id, slot, prio if is_main else prio / 2),
        )
    assign_sessions(conn, only_missing=True)


BLOCK_RANK = {"early": 0, "mid": 1, "cleanup": 2}
# Fixed leveling blocks: levels are derived from the block type.
BLOCK_LEVELS = {"early": ("1→22", 1, 22), "mid": ("22→45", 22, 45), "cleanup": ("Cleanup", 45, 45)}


def normalize_blocks(conn: sqlite3.Connection) -> None:
    # Only the 1→22 block has optional route toggles; 22→45 (MSQ rush, Nightmare unlock) is mandatory.
    conn.execute("UPDATE leveling_templates SET options = '{}' WHERE block_type <> 'early'")
    for bt, (label, s, e) in BLOCK_LEVELS.items():
        for table in ("leveling_templates", "leveling_blocks"):
            conn.execute(f"UPDATE {table} SET label = ?, start_level = ?, end_level = ? WHERE block_type = ?",
                         (label, s, e, bt))


def _daily_hours(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT value FROM settings WHERE key = 'daily_play_hours'").fetchone()
    return float(json.loads(row[0])) if row else float(DEFAULT_SETTINGS["daily_play_hours"])


def assign_sessions(conn: sqlite3.Connection, only_missing: bool = False) -> None:
    """Fill sessions from the daily play-hour budget (blocks are never split).

    With only_missing, blocks without a session join the earliest session already used
    by the same block type (e.g. a new alt's 1→22 goes with the other 1→22 blocks).
    """
    from aion.sessions import block_hours, ensure_sessions

    live = block_hours(conn)
    rows = [(r[0], r[1], live.get(r[0], {}).get("hours", 0.0), r[3]) for r in conn.execute(
        "SELECT id, block_type, hours, session FROM leveling_blocks ORDER BY schedule_order, id").fetchall()]
    if only_missing and any(r[3] is not None for r in rows):
        first = {}
        for _, bt, _, sess in rows:
            if sess is not None:
                first[bt] = min(first.get(bt, sess), sess)
        last = max((r[3] for r in rows if r[3] is not None), default=1)
        for bid, bt, _, sess in rows:
            if sess is None:
                conn.execute("UPDATE leveling_blocks SET session = ? WHERE id = ?", (first.get(bt, last), bid))
        return
    cap = _daily_hours(conn)
    permanent = {r[0] for r in conn.execute("SELECT number FROM sessions WHERE permanent = 1")}

    def next_free(n: int) -> int:
        while n in permanent:  # leveling goes into one-off sessions only
            n += 1
        return n

    session, used = next_free(1), 0.0
    for bid, _, hours, _ in rows:
        hours = float(hours or 0)
        if used > 0 and used + hours > cap:
            session, used = next_free(session + 1), 0.0
        used += hours
        conn.execute("UPDATE leveling_blocks SET session = ? WHERE id = ?", (session, bid))
    ensure_sessions(conn)


def suggested_block_order(conn: sqlite3.Connection) -> None:
    """Main first within each tier: all 1→22, then all 22→45, then all cleanups."""
    rows = conn.execute(
        "SELECT b.id, b.block_type, c.is_main, c.sort_order, c.id FROM leveling_blocks b "
        "JOIN characters c ON c.id = b.character_id"
    ).fetchall()
    rows.sort(key=lambda r: (BLOCK_RANK.get(r[1], 3), -int(r[2] or 0), r[3] or 0, r[4]))
    for i, r in enumerate(rows, start=1):
        conn.execute("UPDATE leveling_blocks SET schedule_order = ? WHERE id = ?", (i, r[0]))


def seed(conn: sqlite3.Connection) -> None:
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
    for i, c in enumerate(CURRENCIES):
        conn.execute(
            "INSERT OR IGNORE INTO currencies (key, name, category, tradable, bound, shared, estimated_kinah_value, weight, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (*c, i),
        )
    for role, bt, label, s, e, h, req, crit, prio, checklist, opts in LEVELING_TEMPLATES:
        conn.execute(
            "INSERT OR IGNORE INTO leveling_templates (role, block_type, label, start_level, end_level, hours, required, critical, priority, checklist, options) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (role, bt, label, s, e, h, req, crit, prio, checklist, json.dumps(opts)),
        )
    for i, (name, cls, is_main, il) in enumerate(ROSTER):
        cur = conn.execute(
            "INSERT INTO characters (name, class, is_main, membership, level, item_level, sort_order, notes) VALUES (?, ?, ?, 1, 1, ?, ?, ?)",
            (name, cls, is_main, il, i, "GS is a post-45 planning target."),
        )
        add_character_defaults(conn, cur.lastrowid, bool(is_main))
    suggested_block_order(conn)
    for i, (act, rewards) in enumerate(_activities()):
        act["sort_order"] = i
        cols = ", ".join(act)
        cur = conn.execute(f"INSERT INTO activities ({cols}) VALUES ({', '.join('?' for _ in act)})", list(act.values()))
        for key, amount in rewards.items():
            if amount:
                conn.execute("INSERT INTO activity_rewards (activity_id, currency_key, amount) VALUES (?, ?, ?)",
                             (cur.lastrowid, key, amount))
    for name, st, scope, n, each in ODYLE_SOURCES:
        conn.execute(
            "INSERT INTO odyle_sources (name, source_type, scope, purchases, odyle_each, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (name, st, scope, n, each, "KR/TW reference — enable with the sidebar toggle."),
        )
    for rs, name, url, status, notes in SOURCES:
        conn.execute(
            "INSERT INTO sources (ruleset, source_name, source_url, status, notes, verified_date) VALUES (?, ?, ?, ?, ?, ?)",
            (rs, name, url, status, notes, dt.date.today().isoformat()),
        )


def normalize_scopes(conn: sqlite3.Connection) -> None:
    """Only per_character / per_server / unknown exist: the account is bound to one server."""
    for table in ("activities", "progression_items", "odyle_sources"):
        conn.execute(f"UPDATE {table} SET scope = 'per_server' WHERE scope IN ('per_account', 'shared_server_pool')")
    for table in ("activities", "progression_items"):
        conn.execute(f"UPDATE {table} SET scope = 'unknown' "
                     "WHERE scope IS NULL OR scope NOT IN ('per_character', 'per_server')")


def ensure_defaults(conn: sqlite3.Connection) -> None:
    # New currencies reach existing databases too.
    n = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM currencies").fetchone()[0]
    for i, c in enumerate(CURRENCIES):
        conn.execute(
            "INSERT OR IGNORE INTO currencies (key, name, category, tradable, bound, shared, estimated_kinah_value, weight, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (*c, n + i + 1),
        )
    from aion.research_data import migrate_gs_v2, seed_progression

    seed_progression(conn)
    migrate_gs_v2(conn)
    # Shugo Festival and Dimensional Invasion have their own content pages.
    for name in ("Shugo Festival", "Dimensional Invasion"):
        conn.execute("UPDATE activities SET category = ? WHERE name = ? AND category = 'Daily & Weekly'", (name, name))
    from aion.research_content import migrate_content_v1
    from aion.research_dungeons import migrate_dungeons_v1, sort_dungeons_v2

    migrate_content_v1(conn)
    migrate_dungeons_v1(conn)
    sort_dungeons_v2(conn)
    for key, label, color, desc in RULESETS:
        conn.execute("INSERT OR IGNORE INTO rulesets (key, label, color, description) VALUES (?, ?, ?, ?)",
                     (key, label, color, desc))
    normalize_blocks(conn)
    assign_sessions(conn, only_missing=True)
    normalize_scopes(conn)
    from aion.sessions import ensure_sessions

    ensure_sessions(conn)
