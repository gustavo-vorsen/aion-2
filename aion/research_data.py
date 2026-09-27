"""Researched progression data (web research, 2026-09-26).

Almost nothing system-specific was published for the Global client (the Sept 2026 LST capped
level 37 and disabled Rifts/Abyss/PvP), so most values are KR/TW references at the cap-45 stage.
Every row carries its source URL in `notes`. Unknown values are left 0 and say "not found".
"""
from __future__ import annotations

import sqlite3

# New reward types used by progression systems.
PROGRESSION_CURRENCIES = [
    # key, name, category, tradable, bound, shared, kinah value, weight
    ("noble_belt_scrolls", "Noble Belt Enhance Scrolls", "progress", 0, 1, 0, None, 5.0),
    ("amulet_scrolls", "Revelation Amulet Enhance Scrolls", "progress", 0, 1, 0, None, 5.0),
    ("wing_featherdown", "Sealed Wing Featherdown", "material", 0, 1, 0, None, 0.5),
    ("pantheon_scraps", "Pantheon statue scraps", "material", 0, 1, 0, None, 0.5),
    ("titles", "Titles", "progress", 0, 1, 0, None, 2.0),
    ("action_power", "Action Power (permanent)", "progress", 0, 1, 0, None, 0.1),
]

KR = "kr_tw_reference"
URL_GS = "https://www.inven.co.kr/board/aion2/6444/279"
URL_DAEV = "https://aion2.wiki.fextralife.com/Daevanion_Boards ; https://gamerstogether.cz/en/aion-2-daevanion/"
URL_SEALED = "https://game8.co/games/Aion-2/archives/617999 ; https://aion2hub.com/leveling/elyos-levels-10-25"
URL_HOLD = "https://www.gametoc.co.kr/news/articleView.html?idxno=104144 ; https://game8.co/games/Aion-2/archives/617436"
URL_QUEST = "https://game8.co/games/Aion-2/archives/623928"
URL_TRACE = "https://game8.co/games/Aion-2/archives/617446"
URL_GENUS = "https://sagye.kr/tips/pets ; https://www.gametoc.co.kr/news/articleView.html?idxno=105439"
URL_RIFT = "https://www.inven.co.kr/board/aion2/6444/305 ; https://www.gavara.org/forums/topic/aion-2-rift-rewards-guide-better-runs-with-u4n-strategies"

# system, faction, name, region, level_req, count, minutes_each, scope, status, notes, rewards (per completion)
PROGRESSION = [
    # ---- Skills
    ("skills", "own", "Skill points from leveling (1→45)", "", 45, 1, 0, "per_character", "provisional",
     "About 230–258 skill points by 45 depending on class (enough for ~11–12 skills at Lv10). Skill Lv8 = 13 pts, "
     "Lv10 = 21 pts; Lv8/12/16 unlock specialization slots. Skill levels do NOT add Item Level (GS); they add Combat "
     "Power. Levels above 10 come from Daevanion nodes, gear and Arcana. https://mmo-codex.com/articles/aion-2-sorcerer-guide/",
     {"skill_points": 244}),
    ("skills", "own", "Stigma slots (unlock at level 23)", "", 23, 4, 0, "per_character", "provisional",
     "4 Stigma slots. Levelled only with Stigma Shards (Abyss/PvP shops, Ascension Trial, Shugo Festa). CP per stigma "
     "level: 1→5 ≈0.9K, 5→10 ≈2K, 10→15 ≈3.5K, 15→20 ≈6K. https://vortexgaming.io/en/postdetail/717212",
     {}),
    # ---- Daevanion (boards are the GS sinks; point sources are the other tabs + these rows)
    ("daevanion", "own", "Nezekan board", "", 12, 1, 0, "per_character", "provisional",
     "Full board: +1 level to 11 skills, HP +1,000, Attack Bonus +180, Defense Bonus +1,400. Point total not found. "
     "Node costs: stat 1, passive 2, active 3, unique 4. +1 Item Level per point spent. " + URL_DAEV, {}),
    ("daevanion", "own", "Zikel board", "", 20, 1, 0, "per_character", "provisional",
     "59 points (TW). +1 Item Level per point spent. " + URL_DAEV, {"gear_score": 59}),
    ("daevanion", "own", "Vaizel board", "", 30, 1, 0, "per_character", "provisional",
     "70 points (TW). +1 Item Level per point spent. " + URL_DAEV, {"gear_score": 70}),
    ("daevanion", "own", "Triniel board", "", 40, 1, 0, "per_character", "provisional",
     "Point total not found. " + URL_DAEV, {}),
    ("daevanion", "own", "Ariel board (PvE)", "", 45, 1, 0, "per_character", "provisional",
     "128 points (TW). Ariel crystals from duty/mission quests and Nightmare. " + URL_DAEV, {"gear_score": 128}),
    ("daevanion", "own", "Azphel board (PvP)", "", 45, 1, 0, "per_character", "provisional",
     "128 points (TW). Azphel crystals from Abyss shop, Proving Ground, Ereshkigal Monolith. " + URL_DAEV, {"gear_score": 128}),
    ("daevanion", "own", "Level-up Daevanion points", "", 45, 1, 0, "per_character", "unknown",
     "Level-up rewards give Daevanion points (amount not found). Almost 400 points total are available by 45 "
     "(global guide) including quests/sealed dungeons. https://mmo-codex.com/articles/aion-2-leveling-guide/", {}),
    ("daevanion", "own", "Shugo Festa shop crystals", "", 45, 1, 0, "per_character", "provisional",
     "15 per character on TW (7 on KR). " + URL_DAEV, {"daevanion_points": 15}),
    ("daevanion", "own", "Nightmare shop crystals", "", 45, 1, 0, "per_character", "provisional",
     "15 per character. " + URL_DAEV, {"daevanion_points": 15}),
    ("daevanion", "own", "Substance Morph crystal", "", 45, 1, 0, "per_character", "provisional",
     "1 crystal = 100 fragments + 50 Odyle (repeatable; count = how many you plan). " + URL_DAEV, {"daevanion_points": 1}),
    # ---- Side quests
    ("side_quests", "own", "Regional quests (Verteron / Altgard)", "Verteron / Altgard", 10, 73, 5, "per_character", "provisional",
     "73 per faction map (game8). Rewards per quest: EXP 0.01–2%, 10k–100k bound Kinah (avg used: 50k), usually 2–3 "
     "Daevanion crystals (avg used: 2.5). Minutes per quest is an estimate. " + URL_QUEST,
     {"kinah_bound": 50000, "daevanion_points": 2.5}),
    ("side_quests", "own", "Regional quests (Abyss)", "Abyss", 45, 0, 5, "per_character", "unknown",
     "Count not found. " + URL_QUEST, {}),
    ("side_quests", "enemy", "Rift quests (enemy territory)", "Enemy map via Rift", 45, 7, 5, "per_character", "provisional",
     "7 Rift quests per entrance (7mmo). Reward Daevanion and Abyss Points (amounts not found). Rifts open every 3–4 h "
     "for 1 h on KR; disabled in the Global LST. " + URL_RIFT, {}),
    # ---- Strongholds
    ("strongholds", "own", "Strongholds (garrisons)", "Verteron / Altgard", 10, 15, 10, "per_character", "provisional",
     "14–15 per faction map (sources disagree). One-time chest: 15,000 Kinah + 2 Noble Belt Enhance Scrolls (only "
     "source of belt scrolls) + some titles. Daevanion: 2 per gamerstogether, none per game8/aion2hub (not counted). "
     "Minutes is an estimate; Stronghold Express Vouchers auto-clear a region. " + URL_HOLD,
     {"kinah_bound": 15000, "noble_belt_scrolls": 2}),
    ("strongholds", "enemy", "Enemy strongholds (via Rift)", "Enemy map via Rift", 45, 15, 10, "per_character", "provisional",
     "Needed to get enough belt scrolls for a Unique Noble Belt. Same chest assumed. " + URL_HOLD,
     {"kinah_bound": 15000, "noble_belt_scrolls": 2}),
    # ---- Sealed (hidden) dungeons
    ("hidden_dungeons", "own", "Sealed dungeons", "Verteron / Altgard", 15, 61, 10, "per_character", "provisional",
     "61 per faction map (game8; aion2hub lists 55 by tier). First clear: 15k Kinah, 2 Daevanion crystals, 2 Wisdom "
     "Stones (skill points), 1.2–1.25k Enhancement Stones, 2 Sealed Wing Featherdown, 2 Pantheon statue scraps. "
     "'Ruins of the Ancient City of Ru' gives 20/20 wing materials. ≤10 min each. " + URL_SEALED,
     {"kinah_bound": 15000, "daevanion_points": 2, "skill_points": 2, "enhancement_stones": 1225,
      "wing_featherdown": 2, "pantheon_scraps": 2}),
    ("hidden_dungeons", "enemy", "Enemy sealed dungeons (via Rift)", "Enemy map via Rift", 45, 61, 10, "per_character", "provisional",
     "500 Abyss Points each and 'a significant amount of Daevanion' (amount not found). " + URL_RIFT,
     {"abyss_points": 500}),
    # ---- Empyrean traces / Monolith
    ("feathers", "own", "Monolith Verteron / Altgard (30 levels)", "Verteron / Altgard", 10, 1, 0, "per_server", "provisional",
     "560 traces to Lv30; since KR 2025-12-03 each feather gives 4 traces. Shared per server since KR 2025-12-17 "
     "(expected on Global). Cumulative: 112 Wisdom Stones, Action Power +320, 30 Revelation Amulet scrolls (only "
     "source), 11 Hidden Cube keys, 20 Soul Codex resets, stats, 2 outfits, titles at Lv10/20/30. Extra traces → 50 "
     "Enhancement Stones each (max 1,680/server). Hours not found. " + URL_TRACE,
     {"skill_points": 112, "action_power": 320, "amulet_scrolls": 30, "hidden_cube_keys": 11, "titles": 3}),
    ("feathers", "own", "Monolith Ereshkigal (Abyss)", "Abyss", 45, 1, 0, "per_server", "unknown",
     "PvP stats and Azphel crystals; 20 levels (title at 20). Details not found. " + URL_TRACE, {"titles": 1}),
    ("feathers", "enemy", "Enemy Empyrean traces (via Rift)", "Enemy map via Rift", 45, 1, 0, "per_server", "unknown",
     "Traces are faction-specific; enemy traces can be collected during Rifts. Reward track not found. " + URL_TRACE, {}),
    # ---- Genus Insight
    ("genus", "own", "Genus: Intellect (Cogni)", "", 1, 41, 0, "per_server", "provisional",
     "41 pets. Kill a monster type to collect Pet Souls; each pet to understanding Lv5 needs 500 souls (sagye) or "
     "1,010 (gameple). Pets/souls shared per server. Stats: HP, Crit, Power, Knowledge, dmg vs genus. " + URL_GENUS, {}),
    ("genus", "own", "Genus: Wild (Fera)", "", 1, 65, 0, "per_server", "provisional", "65 pets. " + URL_GENUS, {}),
    ("genus", "own", "Genus: Natura", "", 1, 48, 0, "per_server", "provisional", "48 pets. " + URL_GENUS, {}),
    ("genus", "own", "Genus: Transformation (Varian)", "", 1, 46, 0, "per_server", "provisional", "46 pets. " + URL_GENUS, {}),
    ("genus", "own", "Genus Insight Lv10 (all genera)", "", 1, 1, 0, "per_server", "provisional",
     "Insight levels to 10 with Insight Crystals (daily duties, passes). 9 rerollable effect slots (3 and 9 = attack). "
     "Titles for all genera at Lv10 and for all 200 pets. " + URL_GENUS, {"titles": 2}),
    # ---- Titles
    ("titles", "own", "Unique titles", "", 1, 12, 0, "per_character", "provisional",
     "12 Unique titles (Monolith Lv30, Ereshkigal 20, all genera Lv10, 200 pets, 25 wings, 700 appearances, 300 PvP "
     "kills, sealed-dungeon sets, 6 episode chapters, +15 Unique gear). Owned stats always apply; equip 1 offensive, 1 "
     "defensive, 1 utility. Community owned-effect sum: PvE Atk +36, Acc +90, Def +130, dmg red. 3.5%, dmg amp 5%, "
     "HP +470. https://game8.co/games/Aion-2/archives/613096", {"titles": 1}),
    # ---- Wardrobe
    ("wardrobe", "own", "Appearance collection", "", 1, 700, 0, "per_server", "provisional",
     "Each appearance gives a small permanent stat (0.2% → 0.1% when made server-shared). 700 appearances → title "
     "(combat speed +5%, cooldown −5%). https://game.savetip.co.kr/aion-2-appearance-collection-guide-title/", {}),
    # ---- Wings
    ("wings", "own", "Wings collection", "", 10, 25, 0, "per_character", "provisional",
     "30+ wings (title counts 25). Equipped stats (e.g. Def Bonus 200, HP 300), owned Flight Power, +1..+10 enhance. "
     "Sources: quest 'The Power in the Lake', morph 70 Featherdown + 10 Pure Odyle, Hidden Cubes, lvl-45 shops. "
     "Account sharing unconfirmed. https://game8.co/games/Aion-2/archives/614970", {"titles": 0.04}),
    # ---- Revelation Amulet / Noble Belt
    ("amulet_belt", "own", "Revelation Amulet (per grade)", "", 10, 1, 0, "per_character", "provisional",
     "10 enhance levels per grade then promote. Only Monolith scrolls upgrade it. Large Item Level gains (amount not "
     "found). https://www.gameple.co.kr/news/articleView.html?idxno=214553", {}),
    ("amulet_belt", "own", "Noble Belt (per grade)", "", 10, 1, 0, "per_character", "provisional",
     "10 enhance levels per grade then promote. Only Stronghold scrolls upgrade it (enemy strongholds needed for "
     "Unique). Item Level amount not found. https://www.gameple.co.kr/news/articleView.html?idxno=214553", {}),
    # ---- Pantheon
    ("pantheon", "own", "Pantheon statues & paintings", "", 10, 1, 0, "per_character", "unknown",
     "Personal hall; statues/paintings give permanent stats. Statue scraps from sealed dungeons; also Nightmare, field "
     "bosses, crafting. Amounts not found. https://www.rsnxt.com/News/aion-2-the-pantheon-system-your-guide-to-statues-art-and-power.html", {}),
    # ---- Arcana
    ("arcana", "own", "Arcana slots (5)", "", 45, 5, 0, "per_character", "provisional",
     "5 slots, cards up to +5, from Transcendence (repeatable farm). Biggest Item Level jump: grey 20, green 40, blue "
     "60, gold 80 per card (value here = all 5 slots gold). On Global, Rare Arcana can drop from Transcendence 1. "
     "https://7mmo.com/threads/the-aion-2-bible-the-tryhard-guide-from-level-1-to-ludra.5351/", {"gear_score": 80}),
]


def seed_progression(conn: sqlite3.Connection) -> None:
    """Insert researched progression rows once (tracked in settings)."""
    done = conn.execute("SELECT value FROM settings WHERE key = 'seed_progression_v1'").fetchone()
    for i, c in enumerate(PROGRESSION_CURRENCIES):
        n = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM currencies").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO currencies (key, name, category, tradable, bound, shared, estimated_kinah_value, weight, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (*c, n + 1))
    conn.execute("UPDATE currencies SET name = 'Item Level (GS)' WHERE key = 'gear_score'")
    conn.execute("UPDATE currencies SET name = 'Skill Points / Wisdom Stones' WHERE key = 'skill_points'")
    conn.execute("UPDATE currencies SET name = 'Daevanion Points / Crystals' WHERE key = 'daevanion_points'")
    if done:
        return
    for i, (system, faction, name, region, lvl, count, mins, scope, status, notes, rewards) in enumerate(PROGRESSION):
        cur = conn.execute(
            "INSERT INTO progression_items (system, faction, name, region, level_req, count, minutes_each, scope, ruleset, "
            "source_status, sort_order, notes, main_default, alt_default) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (system, faction, name, region, lvl, count, mins, scope, KR, status, i, notes, 0 if scope == "per_server" else 1))
        for k, v in rewards.items():
            conn.execute("INSERT INTO progression_rewards (item_id, currency_key, amount) VALUES (?, ?, ?)", (cur.lastrowid, k, v))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_progression_v1', 'true')")


BOARD_CAPACITY = {"Zikel board": 59, "Vaizel board": 70, "Ariel board (PvE)": 128, "Azphel board (PvP)": 128}
GS_PER_UNIT = {"gear_score": 1.0, "daevanion_points": 1.0}  # others unknown / Combat Power only → 0


def migrate_gs_v2(conn: sqlite3.Connection) -> None:
    """GS conversion: boards keep capacity (not GS) so Daevanion points aren't counted twice."""
    if conn.execute("SELECT value FROM settings WHERE key = 'seed_gs_v2'").fetchone():
        return
    for k, v in GS_PER_UNIT.items():
        conn.execute("UPDATE currencies SET gs_per_unit = ? WHERE key = ?", (v, k))
    for name, cap in BOARD_CAPACITY.items():
        conn.execute("UPDATE progression_items SET capacity = ? WHERE system = 'daevanion' AND name = ?", (cap, name))
    conn.execute(
        "DELETE FROM progression_rewards WHERE currency_key = 'gear_score' AND item_id IN "
        "(SELECT id FROM progression_items WHERE system = 'daevanion' AND name LIKE '%board%')")
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_gs_v2', 'true')")
