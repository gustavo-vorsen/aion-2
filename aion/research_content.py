"""Researched recurring-content data (web research, 2026-09-26).

The Global LST (Sept 2026) capped level 37 and had Abyss/PvP/Rifts/shop/membership off, so almost
no Global endgame numbers exist yet: values are KR/TW references unless tagged global_lst.
Where KR changed values over time, launch-era (level-45) values are used and later changes are noted.
"""
from __future__ import annotations

import json
import sqlite3

GB = "https://aion2.plaync.com (official KR guidebook)"
INVEN_LOOP = "https://www.inven.co.kr/webzine/news/?news=311736&site=aion2"

CONTENT_CURRENCIES = [
    # key, name, category, tradable, bound, shared, kinah value, weight
    ("twilight_cloudstones", "Twilight Cloudstones", "material", 0, 1, 0, None, 0.2),
    ("silentium", "Silentium", "material", 0, 1, 0, None, 0.5),
    ("ariel_shards", "Ariel fragments", "material", 0, 1, 0, None, 1.0),
    ("breakthrough_shards", "Breakthrough shards", "material", 0, 1, 0, None, 1.0),
    ("pet_soul_boxes", "Pet soul boxes", "material", 0, 1, 0, None, 0.5),
    ("gold_medals", "Gold Medals", "currency", 0, 1, 0, None, 2.0),
    ("platinum_medals", "Platinum Medals", "currency", 0, 1, 0, None, 5.0),
    ("centuryroot_tokens", "Centuryroot Tokens (festival shop)", "currency", 0, 1, 0, None, 0.5),
]

# activity name -> (fields to set, rewards per claim (replaces all; None = keep), notes)
CONTENT_UPDATES = {
    "Shugo Festival": (
        dict(scope="per_server", cadence="daily", attempts_per_reset=3, membership_bonus_attempts=0,
             duration_minutes=5, ruleset="global_lst", source_status="provisional"),
        {"abyss_points": 200, "centuryroot_tokens": 1},
        "Global: 3 keys/day free (secondary source, unverified); Global membership lists no extra keys. KR: 7/week "
        "free, 14 with membership, per server (S3). 160–240 AP per key at KR launch (doubled Dec 2025 and Apr 2026); "
        "AP not capped. Needs ≥100 contribution. https://www.iggm.com/news/aion-2-launch-scale-test-draws-73000-players-"
        "how-does-global-version-differ-from-korea-taiwan ; https://aion2.wiki.fextralife.com/Shugo_Festival"),
    "Dimensional Invasion": (
        dict(scope="per_server", cadence="regenerating", charges_per_day=1, charge_cap=7, duration_minutes=12,
             ruleset="kr_tw_reference", source_status="provisional"),
        {},
        "Every hour at :30. Reward claims +1/day cap 7 (community, May 2026) vs 2/day max 14/week (official guidebook, "
        "Apr 2026). ≥100 contribution gives 3 reward picks: AP (not capped), enhancement stones, festival currency "
        "(amounts not found). Minutes estimated. " + GB),
    "Daily Duties": (
        dict(scope="per_server", cadence="daily", attempts_per_reset=5, duration_minutes=3,
             ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 500},
        "5/day, reset 05:00; per server since Apr 2026 (per character before). 500 AP each; reward slots 100/50/33%: "
        "Kinah, enhancement stones, Odyle, Hidden Cube Key (no fixed amount), gear, Bio-Research tickets. " + INVEN_LOOP),
    "Supply Requests — Daily": (
        dict(scope="unknown_global", cadence="daily", attempts_per_reset=1, duration_minutes=5,
             ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 15000},
        "Emergency/daily tab: 10–20k AP per day in total (modelled as 1 claim/day). Item turn-ins; AP not capped. " + INVEN_LOOP),
    "Supply Requests — Weekly": (
        dict(scope="unknown_global", cadence="weekly", attempts_per_reset=1, duration_minutes=10,
             ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 40000},
        "Weekly tab: 30–50k AP. Up to ~200k AP/week across tabs, realistically 50–100k. " + INVEN_LOOP),
    "Supply Requests — Season": (
        dict(ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 750},
        "Season craft/boss requests, e.g. 5 Silentium → 750 AP, 8 → 1,260 AP. " + INVEN_LOOP),
    "Command Missions — Normal": (
        dict(scope="per_server", attempts_per_reset=12, duration_minutes=7, ruleset="kr_tw_reference",
             source_status="provisional"),
        {"abyss_points": 500},
        "12/week bought with Kinah (per server since S3). 500 AP each + random Ariel fragments, Odyle, Kinah, "
        "enhancement stones. Minutes estimated. " + INVEN_LOOP),
    "Nightmare": (
        dict(scope="per_character", cadence="regenerating", charges_per_day=2, charge_cap=14,
             ruleset="kr_tw_reference", source_status="provisional"),
        {},
        "2/day cap 14, per character. Dream Shards for the Nightmare shop (15 Daevanion crystals per character). "
        "Instant-clear tickets 30k Kinah. Reward amounts not found. " + GB),
    "Ascension Trial": (
        dict(scope="per_character", attempts_per_reset=3, ruleset="kr_tw_reference", source_status="provisional"),
        None,
        "3/week per character. Stigma shards among rewards (amounts not found). https://talentbuilds.com/aion2/checklist"),
    "Transcendence": (
        dict(scope="per_character", ruleset="kr_tw_reference", source_status="provisional"),
        None,
        "2 entries/day at KR launch (cap 14). Rewards: Arcana, Theostones, Amplify fragments. Kinah falloff 100% up to "
        "56 clears per server-week, then 80/60/40/20%. " + GB),
    "Raid": (
        dict(name="Sanctuary raid", attempts_per_reset=3, entry_item_level=2700, odyle_per_claim=40,
             membership_extra_claims=1, ruleset="kr_tw_reference", source_status="provisional"),
        None,
        "Sanctuary: 2–4 entries/week at launch, 1–2 reward cubes, GS ≥ 2,700; membership = 2 Odyle injections per "
        "cube. Bound Kinah among rewards. https://gamers4.life/aion-2/database/en/checklist/"),
    "Daily Dungeon — Daeva Bio-Research Base": (
        dict(scope="per_character", attempts_per_reset=7, ruleset="kr_tw_reference", source_status="provisional"),
        {"enhancement_stones": 10000},
        "KR launch: 7/week per character (S3: 14/week per server). Up to 10,000 enhancement stones per run. " + GB),
    "Open Abyss (per hour)": (
        dict(ruleset="kr_tw_reference", source_status="unknown", entry_item_level=1000),
        {"silver_medals": 54 / 14, "gold_medals": 20 / 14, "platinum_medals": 3 / 14},
        "7 h/week, 14 with membership; +1 h per Rift Stone. Global may have no time limit for free players "
        "(unverified). Unlock lvl 45, GS ~1,000. AP per hour not found. Weekly medals (rank 1–9): 54 silver, 20 gold, "
        "3 platinum, spread per hour here. https://kodex.yavuz.app/en/systems/abyss/"),
    "Abyss Corridor": (
        dict(cadence="opportunity", attempts_per_reset=10, duration_minutes=5, consumes_abyss_time=0,
             ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 7500},
        "After an Artifact siege (Wed/Sat 22:00), only the owning faction. Launch: ~5 min per run, 5–10k AP (up to "
        "~30k); up to ~100k/week if your side holds all corridors. https://vortexgaming.io/en/postdetail/596156"),
    "Arena 5v5 — rewarded matches": (
        dict(name="Arena — win rewards", attempts_per_reset=30, duration_minutes=10, ruleset="kr_tw_reference",
             source_status="provisional"),
        {"abyss_points": 1000},
        "1v1 and 5v5. S3: win rewards capped at 30/week. TW: 30 wins × 1,000 AP. Minutes include losses (estimate). "
        "https://kodex.yavuz.app/en/pvp/"),
    "Battlefield 10v10 — win rewards": (
        dict(attempts_per_reset=3, duration_minutes=25, ruleset="kr_tw_reference", source_status="provisional"),
        {"abyss_points": 1000, "silver_medals": 1, "gold_medals": 1},
        "10v10, 10 min + 5 overtime. Rewards for up to 3 wins/week (AP + 3 silver + 3 gold medals per week). Open "
        "11–14h and 20–22h. " + GB),
    "Battlefield 10v10 — participation rewards": (
        dict(enabled=0, ruleset="kr_tw_reference", source_status="unknown"),
        None, "Current participation reward not found (disabled)."),
}

# name, category, rewards, fields
NEW_CONTENT = [
    ("Arena — participation rewards", "Instanced PvP", {"abyss_points": 500},
     dict(scope="per_character", attempts_per_reset=10, duration_minutes=10, ap_cap_category="pvp", alt_default=0,
          notes="TW: 10 participations × 500 AP per week. https://kodex.yavuz.app/en/pvp/")),
    ("Season weekly missions", "Daily & Weekly", {"abyss_points": 12520},
     dict(scope="per_character", attempts_per_reset=1, duration_minutes=60,
          notes="Full weekly completion up to 12,520 AP (casual ~5,650); Oath coins + season shop; the 8,000-point "
                "tier gives Odyle and resurrection stones. " + INVEN_LOOP)),
    ("Daily Dungeon — Odium Storage", "Daily Dungeon", {"pet_soul_boxes": 35},
     dict(scope="per_character", attempts_per_reset=7, duration_minutes=8, enabled=0,
          notes="KR: 30–40 pet soul boxes per run. Not confirmed for Global launch (disabled). " + GB)),
    ("Daily Dungeon — Kropakin's Vault", "Daily Dungeon", {},
     dict(scope="per_character", attempts_per_reset=7, duration_minutes=8, enabled=0,
          notes="KR: bound Kinah (amount not found). Not confirmed for Global launch (disabled). " + GB)),
    ("Awakening Battle", "Awakening Battle", {"silentium": 100, "ariel_shards": 40},
     dict(scope="per_character", attempts_per_reset=3, duration_minutes=10, alt_default=1,
          notes="Solo, 3/week per character (was 7), Combat Power ≥ 1,000. Extreme difficulty example: 100 Silentium, "
                "40 Ariel shards, 20 engraving boxes (+ Stigma shards). Minutes estimated. "
                "https://vortexgaming.io/en/postdetail/650135")),
    ("Subjugation (weekly)", "Subjugation", {"enhancement_stones": 20000, "ariel_shards": 30, "breakthrough_shards": 24},
     dict(scope="per_character", attempts_per_reset=3, duration_minutes=20,
          notes="4 players, 3/week. Hard: 20,000 enhancement stones, 30 Ariel shards, 24 Breakthrough shards. Removed "
                "in KR S3 but likely present at a level-45 Global launch. https://vortexgaming.io/en/postdetail/650135")),
    ("Guardian Lord Nahma", "Field Bosses", {"kinah_unbound": 1000000},
     dict(scope="per_character", attempts_per_reset=2, duration_minutes=20,
          notes="Fri/Sun 22:00 (lower; Enraged Nahma in middle). Kinah per kill capped at 1M (value = cap). Loot to "
                "everyone with contribution within 100 m. https://aion2hub.com/tools/world-bosses")),
    ("Executors (Argo / Kaira / Tamasa)", "Field Bosses", {"kinah_unbound": 200000},
     dict(scope="per_character", attempts_per_reset=2, duration_minutes=20,
          notes="Wed/Sat 22:30 (lower; Dramos/Ducal/Marakha middle). Kinah per kill capped at 200k (value = cap). "
                "https://aion2hub.com/tools/world-bosses")),
    ("Watcher Kaira", "Field Bosses", {"kinah_unbound": 200000},
     dict(scope="per_character", cadence="opportunity", attempts_per_reset=7, duration_minutes=15,
          notes="Every 4 h from 01:00 (attempts = how many you plan per week). Kinah per kill capped at 200k. "
                "https://aion2hub.com/tools/world-bosses")),
    ("Artifact siege", "Abyss", {},
     dict(scope="per_character", attempts_per_reset=2, duration_minutes=45, ap_cap_category="pve",
          notes="Wed/Sat 22:00. AP by contribution for the faction that kills the core (amount not found). " + GB)),
    ("Abyss Rift Zone", "Abyss", {},
     dict(scope="per_character", attempts_per_reset=2, duration_minutes=45, entry_item_level=3000, enabled=0,
          notes="Tue/Thu 22:00, 300 per faction, lvl 45 + GS 3,000. Added after KR launch (disabled; check Global). "
                "https://aion2hub.com/updates/aion-2-update-2026-07-15")),
]


def _set_rewards(conn: sqlite3.Connection, aid: int, rewards: dict) -> None:
    conn.execute("DELETE FROM activity_rewards WHERE activity_id = ?", (aid,))
    for k, v in rewards.items():
        if v:
            conn.execute("INSERT INTO activity_rewards (activity_id, currency_key, amount) VALUES (?, ?, ?)", (aid, k, v))


def migrate_content_v1(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT value FROM settings WHERE key = 'seed_content_v1'").fetchone():
        return
    from aion.seed import _act

    for c in CONTENT_CURRENCIES:
        n = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM currencies").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO currencies (key, name, category, tradable, bound, shared, estimated_kinah_value, "
            "weight, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (*c, n + 1))
    conn.execute("UPDATE currencies SET name = 'Nightmare Currency (Dream Shards)' WHERE key = 'nightmare_currency'")

    for name, (fields, rewards, notes) in CONTENT_UPDATES.items():
        row = conn.execute("SELECT id FROM activities WHERE name = ?", (name,)).fetchone()
        if not row:
            continue
        vals = {**fields, "notes": notes}
        conn.execute(f"UPDATE activities SET {', '.join(f'{k} = ?' for k in vals)} WHERE id = ?", (*vals.values(), row[0]))
        if rewards is not None:
            _set_rewards(conn, row[0], rewards)

    # Abyss Command Scrolls: the 4 grades have identical rewards → one row, 20/week.
    ids = [r[0] for r in conn.execute("SELECT id FROM activities WHERE name LIKE 'Abyss Command — Type %' ORDER BY id")]
    if ids:
        conn.execute(
            "UPDATE activities SET name = 'Abyss Command Scroll', attempts_per_reset = 20, duration_minutes = 7, "
            "ruleset = 'kr_tw_reference', source_status = 'provisional', notes = ? WHERE id = ?",
            ("4 grades × 5/week = 20; difficulty and rewards identical, buy the cheapest. 500 AP + 100 Twilight "
             "Cloudstones each (~10,000 AP/week). Minutes estimated. https://vortexgaming.io/en/postdetail/650135", ids[0]))
        _set_rewards(conn, ids[0], {"abyss_points": 500, "twilight_cloudstones": 100})
        for i in ids[1:]:
            conn.execute("DELETE FROM activities WHERE id = ?", (i,))

    order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM activities").fetchone()[0]
    for name, category, rewards, fields in NEW_CONTENT:
        if conn.execute("SELECT 1 FROM activities WHERE name = ?", (name,)).fetchone():
            continue
        act, _ = _act(name, category, **{"ruleset": "kr_tw_reference", "source_status": "provisional", **fields})
        order += 1
        act["sort_order"] = order
        cur = conn.execute(f"INSERT INTO activities ({', '.join(act)}) VALUES ({', '.join('?' for _ in act)})",
                           list(act.values()))
        _set_rewards(conn, cur.lastrowid, rewards)

    for k, v in {"pve_ap_weekly_cap": 200000.0, "pvp_ap_weekly_cap": 200000.0,
                 "ap_cap_model": "200k/week PvE (monster kills) + 200k/week PvP; Supply/Shugo/Invasion AP uncapped (KR)"}.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_content_v1', 'true')")
