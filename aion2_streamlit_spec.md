# AION 2 Global — Streamlit Progression & Weekly Loop Planner Specification

> **Purpose:** implementation specification for a Streamlit app that plans leveling and recurring AION 2 activities by character, estimates time/currency/resource returns, and visualizes weekly efficiency (Kinah/hour, AP/hour, rewards/week, time/character/week, Odyle efficiency, etc.).
>
> **Data policy:** keep every gameplay value editable. Global launch values can differ from KR/TW and pre-launch tests. Store `ruleset`, `source_status`, and `notes` for every activity/reward where practical.

---

## 1. Core App Concept

The app must let the user:

1. Create any number of characters.
2. Mark each character as **Main** or **Alt** with a toggle.
3. Choose class, faction, server, membership status, current level/item level, and optional notes.
4. Define leveling durations as editable parameters.
5. Reorder leveling blocks and automatically split the plan into calendar/play days based on a configurable daily time budget.
6. Configure recurring activities and their scope: **per character**, **per server**, **per account**, or **shared/unknown**.
7. Configure activity duration, attempts, reset cadence, resource cost, and all rewards.
8. Calculate weekly time, Kinah, AP, currencies, materials, Odyle usage, and efficiency ratios.
9. Compare Main vs Alts and individual characters.
10. Display charts for weekly income, time, reward mix, efficiency, and resource allocation.
11. Preserve uncertainty: Global-unconfirmed values should be visually tagged rather than silently treated as facts.

---

# 2. Navigation / Pages

Recommended Streamlit pages/tabs:

1. **Dashboard**
2. **Characters**
3. **Leveling — Main**
4. **Leveling — Alt**
5. **Leveling Schedule**
6. **Main Loop**
7. **Alt Loop**
8. **Expeditions / Odyle**
9. **Nightmare**
10. **Ascension Trial**
11. **Abyss**
12. **Abyss Commands**
13. **PvP / Battlefields**
14. **Daily & Weekly Content**
15. **Economy / Shops**
16. **Rewards & Currencies**
17. **Analytics**
18. **Settings / Ruleset**

---

# 3. Character Model

Each character should be stored as a record.

```yaml
character:
  id: uuid
  name: string
  class: [Gladiator, Chanter, Cleric, Assassin, Ranger, Sorcerer, Spiritmaster, Templar]
  faction: [Asmodian, Elyos]
  server: string
  is_main: bool
  membership: bool
  level: int
  item_level: int
  combat_power: int | null
  active: bool
  notes: string
```

Default initial roster for this planner:

```yaml
- Gladiator: Main
- Chanter: Alt
- Cleric: Alt
- Assassin: Alt
```

Do **not** hard-code four characters. The UI must support adding/removing characters.

---

# 4. Scope Model — Critical

Every recurring limit/reward must have a scope field:

```python
scope = [
    "per_character",
    "per_server",
    "per_account",
    "shared_server_pool",
    "unknown_global"
]
```

This prevents the app from multiplying a server-wide reward by every alt.

Additional reset fields:

```yaml
cadence: [none, daily, weekly, seasonal, regenerating, event, opportunity]
reset_day: Wednesday
reset_time: "05:00"
max_attempts: number | null
max_reward_claims: number | null
accumulation_cap: number | null
```

---

# 5. Leveling — Main Page

The Main leveling page must expose every block as editable parameters.

## Default planning assumptions

These are **user planning values**, not guaranteed Global completion times.

```yaml
main_leveling:
  level_1_to_22_23_hours: 2.0
  level_22_23_to_45_hours: 2.0
  post_45_cleanup_hours: 7.0
```

The user should be able to rename the breakpoint (22 or 23) and change the hours.

### Main 1 → 22/23 block

Default route checklist:

- Main Story Quest.
- Nearby Empyrean Traces / Feathers when efficient.
- Sealed Dungeons on the route.
- Strongholds on the route.
- Relevant nearby side/regional quests.
- Orange / Daevanion progression quests when appropriate.
- Reach the Krao Cave MSQ/Expedition breakpoint.
- Avoid unnecessary resource spending during the rush.

Editable fields:

```yaml
start_level: 1
end_level: 23
estimated_hours: 2.0
required: true
priority: 1
collect_feathers: true
sealed_dungeons: true
strongholds: true
side_quests: selective
spend_odyle: false
```

### Main 22/23 → 45 block

```yaml
start_level: 23
end_level: 45
estimated_hours: 2.0
required: true
priority: 5
rush_msq: true
nightmare_unlock_via_msq: true
```

Nightmare should **not** have a separate fake “unlock time” block if the final Global MSQ unlocks it as part of the story chain.

### Main cleanup

Default: **7 hours**, editable.

Includes permanent/non-recurring completion work such as:

- Remaining accessible Empyrean Traces / Feathers.
- Sealed Dungeons.
- Strongholds.
- Side/regional quests.
- Permanent Daevanion/skill-point progression.
- Accessible enemy-faction/Rift exploration when applicable.
- Other one-time progression required by the selected ruleset.

Cleanup must **not** be counted in the recurring weekly loop.

---

# 6. Leveling — Alt Page

Each Alt has independent time parameters.

Default planning values:

```yaml
alt_leveling:
  level_1_to_22_23_hours: 1.5
  level_22_23_to_45_hours: 1.5
  cleanup_hours: 5.0
```

Why cleanup is lower by default: shared/synchronized permanent progression may not need to be repeated. Keep this editable because final Global behavior can change.

### Alt 1 → 22/23

Target: pass the early Krao/Expedition/Odyle breakpoint efficiently.

Default behavior:

- Follow MSQ.
- Do route-critical Sealed Dungeons.
- Do enough progression to reach Krao Cave.
- Do not deliberately repeat shared Feather progression already completed on Main.
- Do not automatically claim low-value Odyle cubes during leveling.

### Alt 22/23 → 45

Target: rush level 45 and activate all relevant character-specific accumulating systems as early as possible.

### Alt cleanup

Default: **5 hours per Alt**.

Do permanent character-specific progression but skip genuinely server-shared progression already completed.

---

# 7. Leveling Schedule Page

This page is central to the app.

The user must be able to drag/reorder or assign priorities to blocks such as:

```text
Main 1→23
Alt 1 1→23
Alt 2 1→23
Alt 3 1→23
Main 23→45
Alt 1 23→45
Alt 2 23→45
Alt 3 23→45
Main Cleanup
Alt 1 Cleanup
Alt 2 Cleanup
Alt 3 Cleanup
```

Configurable parameters:

```yaml
daily_play_hours: 14
start_date: date
block_order: list
allow_block_split_across_days: bool
break_hours_per_day: float
```

Output:

- Day / Session number.
- Character.
- Block.
- Start level.
- End level.
- Estimated duration.
- Cumulative duration.
- Remaining daily budget.
- Critical/non-critical flag.

The UI should call these **Leveling Sessions**, not hard-code “Day 1 / Day 2 / Day 3”. The scheduler can then derive Day 1, Day 2, etc. from the chosen time budget.

### Default launch priority

The first priority is getting all characters through their critical leveling milestones. Cleanup is lower priority and may spill into later sessions.

---

# 8. Generic Activity Schema

Use one normalized activity model so charts can aggregate everything.

```yaml
activity:
  id: string
  name: string
  category: string
  enabled: bool
  main_default: bool
  alt_default: bool
  scope: per_character | per_server | per_account | shared_server_pool | unknown_global
  cadence: daily | weekly | regenerating | event | opportunity | none
  attempts_per_reset: float | null
  reward_claims_per_attempt: float
  duration_minutes_per_attempt: float
  entry_costs:
    odyle: float
    kinah: float
    ap: float
    ticket: float
  rewards:
    kinah_unbound: float
    kinah_bound: float
    abyss_points: float
    enhancement_stones: float
    potential_stones: float
    soul_crystals: float
    stigma_shards: float
    arcana: float
    nightmare_currency: float
    trial_currency: float
    medals: float
    custom: {}
  ruleset: global | global_lst | kr_tw_reference | user_override
  source_status: confirmed | provisional | unknown
  notes: string
```

All numeric fields must be editable from Streamlit.

---

# 9. Main Character Recurring Loop

The Main loop should contain **only recurring/reset/recharging activities**. Do not mix one-time progression systems such as Collections, Wardrobe, Arcana configuration, gear upgrades, achievements, titles, or permanent quest cleanup into this page.

## Main default activity list

### Daily Duties

```yaml
scope: per_server
cadence: daily
attempts: 5
```

Primary planning target: **Hidden Cube Key** when applicable. Reward values must be configurable.

### Supply Requests

Keep Daily/Weekly/Season variants as separate configurable activities if the Global client exposes them separately.

Scope should remain configurable until final Global behavior is verified.

### Expedition / Conquest

Uses Odyle Energy for reward cube claims.

Track separately by dungeon and mode:

- Krao Cave — Exploration
- Krao Cave — Conquest
- Fire Temple — Exploration
- Fire Temple — Conquest
- Draupnir — Exploration
- Draupnir — Conquest
- Vakron Sky Island — Exploration
- Vakron Sky Island — Conquest
- Any additional Global launch dungeon

For each dungeon store:

```yaml
entry_item_level
recommended_item_level
run_minutes
odyle_per_claim
membership_extra_claim_available
kinah_bound_per_claim
kinah_unbound_per_claim
enhancement_stones
amplify_fragments
gear_pool_value
pity_or_guaranteed_reward_progress
```

Important planning behavior:

- Exploration can be strategically worthwhile for **guaranteed progression rewards**, especially during initial gearing.
- Do not implement a universal “never open Exploration cubes” rule.
- Conquest is generally the repeat-farm/economy mode, but the app should calculate rather than assume which is optimal.

### Transcendence

Main-focused by default.

Track:

- Odyle cost.
- Run duration.
- Reward claims.
- Arcana-related rewards.
- Enhancement resources.
- Any Global-specific currency/material.

Do not count “Arcana” itself as a recurring activity; it is a reward/progression destination.

### Nightmare

Character-specific recurring content.

Editable parameters:

```yaml
charges_generated_per_day: 2
charge_cap: 14
run_minutes: user_input
rewards_per_run:
  nightmare_currency: user_input
  kinah: user_input
  materials: user_input
```

The values above are planning/reference defaults and must be tagged by ruleset.

### Ascension Trial

Character-specific.

Planning default:

```yaml
attempts_per_week: 3
scope: per_character
```

Track run time and rewards such as Manastones/Stigma/enhancement-related materials according to the selected Global data.

### Command Missions — Normal

Planning reference:

```yaml
weekly_scrolls: 12
scope: per_server
```

Rewards to expose:

- AP.
- Hidden Cube Keys where applicable.
- Soul Crystals.
- Other mission-specific rewards.

Keep scope tagged **provisional Global** until final-client confirmation.

### Abyss Command Scrolls

Add to Main loop.

Planning reference:

```yaml
types: 4
weekly_per_type: 5
total_weekly: 20
scope: per_server
```

Combined with normal Command Scrolls, the current planning reference is **32 Command Missions/week/server**, but keep both systems separate in data and UI.

### Dimensional Invasion

Editable reference parameters:

```yaml
charges_per_day: 1
charge_cap: 7
```

Track duration, contribution score, reward values, and weekly output.

### Raid

Planning reference:

```yaml
attempts_per_week: 3
```

Scope and final Global rewards should remain editable/provisional until confirmed.

Track:

- Amplify resources.
- Daevanion-related rewards.
- Enhancement materials.
- Gear.
- Custom currencies.

### Daily Dungeon

Global LST reference available before launch:

- Daeva Bio-Research Base.
- 14 entries/week/server reference.
- Primary reward: Enhancement Stones.

Do not assume KR/TW Daily Dungeons such as Kropakin's Secret Vault are available at Global launch unless the final ruleset confirms them.

### Shugo Festival

Keep as an optional/provisional Main activity.

Reference rule from KR/TW:

```yaml
weekly_rewards_without_membership: 7
weekly_rewards_with_membership: 14
scope: per_server
```

Do not treat this as Global-confirmed until final client confirmation.

---

# 10. Alt Recurring Loop

Default Alt loop:

1. **Supply Requests** — if/when character-specific reward makes them worthwhile.
2. **Conquest / Expedition using that character's Odyle** — primary economy function.
3. **Nightmare** — character-specific charges.
4. **Ascension Trial** — character-specific weekly attempts.

Potential additions should be controlled by toggles based on final scope:

- Instanced PvP rewards if confirmed per character.
- Any per-character Command system if Global differs from current planning assumption.

Default exclusions from Alt loop:

- Server-wide Daily Duties.
- Server-wide Command Scroll purchases.
- Server-wide Abyss Command pool.
- Shugo if server-wide.
- Main-only strategic Transcendence allocation unless user enables it.

---

# 11. Odyle Energy Model

Odyle is one of the most important resources and should have its own calculator.

## Natural regeneration

Planning reference with Membership:

```yaml
odyle_regen_amount: 15
odyle_regen_interval_hours: 3
odyle_per_day: 120
odyle_per_week: 840
scope: per_character
```

All values editable.

## Cube claims

Typical planning reference:

```yaml
normal_cube_claim_cost: 40
membership_additional_claims: 1
```

Interpretation: Membership can allow an additional selection/claim at the cube, but **the second claim consumes its own Odyle**. It is not a free duplicate reward.

Thus an 80-Odyle double claim can consume two 40-Odyle reward selections in one dungeon clear.

## Purchasable Odyle — KR/TW reference to keep as optional rule

Current reference discussed:

```yaml
shop_per_character:
  purchases: 4
  odyle_each: 40
  total_per_character: 160
shop_shared_server:
  purchases: 16
  odyle_each: 40
  total_server: 640
```

For four characters:

```text
4 chars × 160 = 640
shared server pool = 640
shop total = 1,280 Odyle/week
```

## Substance Morph / Crafting Odyle

The current KR/TW reference has an equivalent set of character/server-limited Odyle recipes, potentially adding another amount comparable to the shop pool.

For four characters under that reference:

```text
Shop:       +1,280/week
Morph:      +1,280/week
Potential additional total: +2,560/week
```

**Important:** these purchase/morph limits are not to be hard-coded as confirmed Global launch rules. Add a ruleset toggle and allow the user to enable/disable them.

## Odyle analytics

Charts/calculations:

- Odyle generated/week/character.
- Odyle bought/week.
- Odyle crafted/week.
- Odyle spent by content.
- Odyle remaining.
- Reward per 40 Odyle.
- Kinah per Odyle.
- AP per Odyle.
- Total reward value per Odyle.

---

# 12. Abyss Page

Treat the Abyss as a separate progression/economy subsystem.

## Open Abyss

Track separately:

```yaml
weekly_time_allowance_hours
membership_time_allowance_hours
extra_time_from_rift_stones
pve_ap_weekly_cap
pvp_ap_weekly_cap
global_ap_cap_model
seasonal_ap_cap
```

Reference previously discussed:

- KR/TW/community: 7h/week base, 14h/week with Membership.
- Rift Stones can extend time.
- Global LST information indicated a different AP-cap model than older KR/TW values; therefore all AP caps must be ruleset-specific/editable.

Do **not** equate:

- weekly Abyss time;
- weekly AP cap;
- Corridor rewards;
- Battlefield rewards.

They are separate constraints.

## Abyss rewards

Track:

- Abyss Points.
- Potential Stones / Abyss Potential Stones.
- Gear drops.
- Medals.
- Rank Points if applicable.
- Boss/objective rewards.
- Tradable drops.
- Custom materials.

Abyss progression includes PvP/Abyss gear. The app should allow a character to have separate **PvE Gear** and **PvP/Abyss Gear** profiles with different item level/CP fields.

```yaml
gear_profiles:
  pve:
    item_level: int
    combat_power: int
  pvp:
    item_level: int
    displayed_combat_power: int
    pvp_power_metric: optional
```

Displayed Combat Power can change when switching equipped gear; PvP-specific bonuses should not be assumed to map one-to-one into the PvE-oriented CP number.

---

# 13. Abyss Corridor

Do **not** model Corridor as simply “3 entries/week” unless final Global data proves that.

Model it as an Abyss opportunity/event activity:

```yaml
name: Abyss Corridor
category: Abyss
cadence: opportunity
scope: per_character
consumes_abyss_time: configurable
run_minutes: user_input
rewards:
  abyss_points: user_input
  kinah: user_input
  other: user_input
availability_events_per_week: user_input
```

Concept:

- Connected to Abyss/Artifact state.
- Primarily PvE mob clearing for efficient AP/rewards.
- Not the same thing as open-world PvP.
- Keep Corridor AP treatment separately configurable because patch rules can exclude it from ordinary PvE AP-cap categories.

Analytics:

- AP/hour.
- Kinah/hour.
- AP per Corridor.
- Weekly Corridor time.
- Contribution to AP cap.

---

# 14. PvP / Battlefields

Instanced PvP must be separate from Open Abyss.

## 5v5

Model as its own activity:

```yaml
name: Arena 5v5
category: Instanced PvP
scope: per_character   # provisional until Global final verification
weekly_reward_attempts: user_input
match_minutes: user_input
rewards:
  abyss_points: user_input
  currency: user_input
  win_rewards: user_input
  participation_rewards: user_input
consumes_abyss_time: false
gear_equalized: false_or_ruleset
```

## 10v10

```yaml
name: Battlefield 10v10
category: Instanced PvP
scope: per_character   # provisional until Global final verification
weekly_win_rewards: 3  # reference, editable
weekly_participation_rewards: 3  # reference, editable
match_minutes: user_input
rewards:
  abyss_points: user_input
  currency: user_input
consumes_abyss_time: false
gear_equalized: true_or_ruleset
```

The UI must distinguish:

- attempts/matches;
- rewarded matches;
- win rewards;
- participation rewards;
- weekly cap;
- per-character vs server-wide scope.

---

# 15. Economy / Dungeon Calculator

Every dungeon should be editable as a row in a DataFrame-style editor.

Recommended columns:

```text
Dungeon
Mode
Tier
Required Item Level
Recommended Item Level
Minutes per Run
Odyle per Claim
Claims per Run
Membership Max Claims
Kinah Unbound / Claim
Kinah Bound / Claim
AP / Claim
Enhancement Stones / Claim
Potential Stones / Claim
Amplify Fragments / Claim
Soul Crystals / Claim
Other Currency / Claim
Pity Progress / Claim
Weekly Limit
Scope
Ruleset
Confirmed?
```

Derived fields:

```text
Total Odyle / Run
Total Kinah / Run
Unbound Kinah / Hour
Bound Kinah / Hour
AP / Hour
Reward Claims / Hour
Kinah / Odyle
AP / Odyle
Enhancement Stones / Hour
Weekly Kinah
Weekly AP
Weekly Time
```

---

# 16. Initial Gearing Logic

Do not hard-code one universal upgrade order, but provide a recommendation/priority configuration.

During leveling, default strategy:

```text
Weapon > survival-required armor upgrades
```

Reason: offensive improvement shortens MSQ/dungeon time. Enhancement Stones invested into replaceable equipment may be recoverable on extraction depending on Global rules, while Kinah spent may not be fully recoverable. Keep recovery percentages configurable.

At/after level 45, track long-lived progression separately:

- Weapon.
- Guard/off-hand if applicable.
- Belt.
- Revelation Amulet/Pendant.
- Armor.
- Accessories.

The app should allow the user to assign an upgrade priority score and material budget to each slot.

---

# 17. Exploration vs Conquest Strategy

Do not encode “Conquest always, Exploration never.”

The planner needs two value concepts:

1. **Repeat value** — ordinary reward per Odyle/time.
2. **Milestone value** — guaranteed reward/pity/progression from completing a required number of Exploration claims.

Examples discussed for initial progression:

- Draupnir Exploration may be worth doing for a guaranteed progression piece.
- Vakron Exploration may be worth doing for its guaranteed reward before transitioning to repeated Vakron Conquest.

The optimizer should therefore support:

```yaml
forced_initial_claims: int
guaranteed_reward_after_claims: int
guaranteed_reward_estimated_value: float
repeat_after_guarantee: bool
```

---

# 18. Rewards / Currency Registry

Use a dynamic registry rather than fixed chart columns.

Minimum currencies/resources:

```text
Kinah — Unbound
Kinah — Bound
Abyss Points (AP)
Odyle Energy
Enhancement Stones
Potential Stones
Abyss Potential Stones
Amplify Stone Fragments
Soul Crystals
Stigma Shards
Nightmare Currency
Trial Currency / Proof / Subjugation Mark
Silver Medals
Hidden Cube Keys
Arcana-related rewards
Daevanion-related materials
Gear Drops
Pity / Guaranteed Reward Progress
Rank Points
Custom Currency 1..N
```

For every reward type support:

```yaml
tradable: bool
bound: bool
shared: bool
estimated_kinah_value: optional float
weight_for_composite_score: optional float
```

This allows charts to show raw reward units **or** a user-defined normalized “value score.”

---

# 19. Analytics / Charts

Required charts:

## Weekly Time

- Total hours/week.
- Hours by character.
- Hours Main vs Alts.
- Hours by activity category.
- Hours by activity.

## Kinah

- Unbound Kinah/week.
- Bound Kinah/week.
- Kinah/hour by activity.
- Kinah/hour by character.
- Kinah/Odyle.
- Cumulative weekly Kinah.

## AP

- AP/week.
- AP/hour.
- AP by Open Abyss vs Corridor vs Commands vs Battlefields.
- AP cap utilization percentage.

## Odyle

- Generated vs spent.
- Natural vs shop vs morph vs other sources.
- Spend allocation by dungeon.
- Remaining Odyle/week.
- Reward/Odyle efficiency.

## Materials

Selectable reward chart:

```python
reward_metric = st.selectbox(
    "Reward metric",
    reward_registry
)
```

Then show:

- reward/week;
- reward/hour;
- reward/attempt;
- reward/Odyle;
- reward by character.

## Main vs Alt

- Weekly time.
- Weekly unbound Kinah contribution.
- AP contribution.
- Odyle generated/spent.
- Material contribution.

## Efficiency Frontier

Optional advanced chart:

- X = time/week.
- Y = selected reward/week.
- Bubble size = Odyle cost.
- One point per activity.

---

# 20. Weekly Planner / Optimizer

Inputs:

```yaml
weekly_available_hours: float
minimum_main_hours: float
include_alts: bool
objective:
  - maximize_unbound_kinah
  - maximize_ap
  - maximize_combat_progression
  - maximize_custom_value_score
  - balanced
```

Constraints:

- Scope limits.
- Weekly/daily caps.
- Character eligibility.
- Item-level gates.
- Odyle available.
- Abyss time available.
- Membership.
- Required milestone claims.

Output ordered list:

```text
Priority | Character | Activity | Runs | Time | Cost | Rewards | Efficiency
```

Do not make optimization assumptions invisible. Show the objective and constraints used.

---

# 21. Main vs Alt Default Assignment Matrix

| Activity | Main | Alt | Default Scope | Notes |
|---|---:|---:|---|---|
| Daily Duties | Yes | No | Server | 5/day planning reference |
| Supply Requests | Yes | Yes | Configurable | Verify final Global scope |
| Expedition/Conquest | Yes | Yes | Character resource | Each character has Odyle economy |
| Transcendence | Yes | Optional | Character resource | Main prioritizes progression |
| Nightmare | Yes | Yes | Character | Character-specific charges |
| Ascension Trial | Yes | Yes | Character | 3/week reference |
| Normal Command Scrolls | Yes | No | Server provisional | 12/week reference |
| Abyss Commands | Yes | No | Server provisional | 4 types × 5/week = 20 |
| Dimensional Invasion | Yes | Optional | Configurable | 1/day, cap 7 reference |
| Raid | Yes | Optional | Configurable | 3/week reference |
| Daily Dungeon | Yes | No by default | Server | Global LST: Bio-Research Base |
| Shugo Festival | Yes | No by default | Server provisional | Membership reference 14/week |
| Open Abyss | Yes | Optional | Character | Time + AP caps separate |
| Abyss Corridor | Yes | Optional | Character/opportunity | AP-efficient PvE opportunity |
| Arena 5v5 | Yes | Optional | Character provisional | Separate from Abyss time |
| Battlefield 10v10 | Yes | Optional | Character provisional | Separate weekly rewards |

All assignments must be user-editable.

---

# 22. Current Four-Character Planning Example

Default roster:

```yaml
Gladiator:
  role: main
  level_1_to_23_hours: 2.0
  level_23_to_45_hours: 2.0
  cleanup_hours: 7.0

Chanter:
  role: alt
  level_1_to_23_hours: 1.5
  level_23_to_45_hours: 1.5
  cleanup_hours: 5.0

Cleric:
  role: alt
  level_1_to_23_hours: 1.5
  level_23_to_45_hours: 1.5
  cleanup_hours: 5.0

Assassin:
  role: alt
  level_1_to_23_hours: 1.5
  level_23_to_45_hours: 1.5
  cleanup_hours: 5.0
```

Suggested initial block order:

```text
1. Gladiator 1→23
2. Chanter 1→23
3. Cleric 1→23
4. Assassin 1→23
5. Gladiator 23→45
6. Chanter 23→45
7. Cleric 23→45
8. Assassin 23→45
9. Gladiator Cleanup
10. Chanter Cleanup
11. Cleric Cleanup
12. Assassin Cleanup
```

The order must be draggable/editable. The app calculates sessions/days from the time budget instead of assuming fixed days.

---

# 23. Streamlit UI Recommendations

## Characters

Use `st.data_editor` for the roster plus an edit form.

Fields:

```text
Name | Class | Main? | Membership? | Level | Item Level | Active
```

## Activity Editor

Use `st.data_editor` with filters:

- Character.
- Main/Alt.
- Category.
- Cadence.
- Scope.
- Confirmed/Provisional.

## Parameter Sidebar

Global sidebar controls:

```text
Ruleset
Membership
Weekly Available Hours
Daily Leveling Hours
Reset Day
Kinah Value Mode
Include Bound Kinah?
Include Alts?
Use Shop Odyle?
Use Morph Odyle?
```

## Status colors

Use semantic status indicators:

```text
Confirmed Global
Global LST / pre-launch
KR/TW reference
User override
Unknown
```

Do not silently convert a KR/TW number into a Global-confirmed number.

---

# 24. Suggested Python Data Structures

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Reward:
    name: str
    amount: float
    bound: bool = False
    tradable: bool = False
    estimated_kinah_value: Optional[float] = None

@dataclass
class Activity:
    name: str
    category: str
    scope: str
    cadence: str
    duration_minutes: float
    attempts_per_reset: Optional[float] = None
    odyle_cost: float = 0
    kinah_cost: float = 0
    rewards: list[Reward] = field(default_factory=list)
    ruleset: str = "user_override"
    confirmed: bool = False

@dataclass
class Character:
    name: str
    character_class: str
    is_main: bool
    membership: bool
    level: int = 1
    item_level: int = 0
```

For persistence, SQLite is preferable to a collection of ad-hoc session-state dictionaries once the app grows.

---

# 25. Suggested Database Tables

```text
characters
leveling_blocks
activities
activity_limits
activity_rewards
character_activity_settings
currency_registry
odyle_sources
gear_profiles
weekly_runs
rulesets
sources
user_settings
```

### `sources`

```text
id
activity_id
ruleset
source_name
source_url
verified_date
status
notes
```

This is important because AION 2 Global is launching with rules that do not always match current KR/TW.

---

# 26. Calculations

## Weekly time

```python
weekly_minutes = attempts * duration_minutes
```

For daily activities:

```python
weekly_attempts = attempts_per_day * 7
```

For per-character activities:

```python
total = sum(activity(character) for character in active_characters)
```

For per-server activities:

```python
total = activity_once_per_server
```

Never multiply server-wide limits by character count.

## Reward/hour

```python
reward_per_hour = reward_per_run / (duration_minutes / 60)
```

## Kinah/hour

Track bound and unbound separately:

```python
unbound_kinah_per_hour
bound_kinah_per_hour
combined_kinah_per_hour  # optional display only
```

## Reward/Odyle

```python
reward_per_odyle = reward_per_claim / odyle_cost
```

## Weekly character contribution

```python
character_weekly_value = sum(
    activity_reward * completed_attempts
    for activity in character.activities
)
```

---

# 27. Important Gameplay Rules to Encode as Configurable Logic

1. **Odyle is a scarce reward-claim resource**, not simply an entry ticket.
2. Membership may allow an additional cube selection, but the extra selection costs additional Odyle.
3. Exploration and Conquest can have different reward profiles even for the same dungeon.
4. Initial Exploration claims can be worthwhile because of guaranteed rewards/pity.
5. Per-character and per-server caps must never be conflated.
6. Abyss weekly time and weekly AP caps are different systems.
7. Abyss Corridor is separate from ordinary open-world Abyss farming for analytics.
8. Instanced 5v5/10v10 PvP is separate from Abyss time.
9. One-time cleanup/progression must not inflate weekly loop time.
10. Shared/synchronized progression should not automatically be repeated on every alt.
11. Bound Kinah and unbound Kinah must be separate metrics.
12. Global, Global LST, and KR/TW reference values must be tagged separately.

---

# 28. Data Still Requiring Final Global Verification

Keep these editable and visibly provisional until the launch client confirms them:

- Exact Global Odyle shop weekly limits.
- Exact Global Substance Morph Odyle limits.
- Exact Global Open Abyss weekly time allowance and Rift Stone extension values.
- Exact Global AP cap structure.
- Exact Global Corridor availability/reset/reward treatment.
- Exact Global 5v5 reward limits and scope.
- Exact Global 10v10 reward limits and scope.
- Final Global Shugo Festival scope/weekly keys.
- Final Global Raid weekly scope/count.
- Final Global Supply Request scope.
- Final Global Command Scroll and Abyss Command scope if the launch UI differs from the current server-wide reference.
- Final Global dungeon reward quantities.
- Exact Kinah/AP/material values for every dungeon tier.
- Final Global item-level gates.

The application should be designed so updating these values requires editing data, **not rewriting business logic**.

---

# 29. Source / Ruleset Notes

Useful current references for the data layer include:

- AION 2 Global-specific databases/guides that distinguish Global-client data from KR/TW data.
- NCSoft official patch notes for mechanics introduced or changed in KR/TW.
- Global Launch Scale Test observations for pre-launch Global behavior.
- Community guides only when the exact value is not available officially; mark these `provisional`.

Examples discussed while defining this planner:

- Global level cap at launch: 45; September LST capped testing at 37, so exact Global 1→45 time remains a planning estimate.
- Expedition reward claims use Odyle; current systems increasingly separate run/entry limits from reward-claim resource limits.
- Current KR/TW Trial content has weekly per-difficulty rewards, but later level-50 Trial systems must not be accidentally added to the Global level-45 launch loop.

---

# 30. MVP Build Order

### Phase 1 — Core

1. Character CRUD + Main toggle.
2. Leveling Main page.
3. Leveling Alt page.
4. Drag/order leveling blocks.
5. Daily/session scheduler.
6. Activity registry.
7. Main/Alt loop assignment.
8. Weekly time calculations.

### Phase 2 — Economy

9. Dungeon/Odyle editor.
10. Kinah calculations.
11. AP calculations.
12. Reward registry.
13. Odyle budget.
14. Main vs Alt contribution.

### Phase 3 — Analytics

15. Weekly charts.
16. Reward/hour charts.
17. Reward/Odyle charts.
18. AP-cap utilization.
19. Abyss-time utilization.
20. Character comparison.

### Phase 4 — Optimization

21. Weekly time-budget optimizer.
22. Objective selector.
23. Automatic recommended run allocation.
24. Milestone/guaranteed-reward logic.
25. Ruleset/source manager.

---

# 31. Key Design Principle

**Everything that can change at Global launch must be a parameter, not a constant.**

The app's job is not to assert that a particular dungeon always gives exactly X Kinah or that a weekly limit is always per character. Its job is to let the user maintain the current ruleset and immediately recalculate:

- what to do;
- on which character;
- how many times;
- how long it takes;
- how much Odyle it costs;
- how much Kinah/AP/material it returns;
- the return per hour;
- the return per Odyle;
- total weekly workload;
- Main vs Alt contribution.

That structure will survive Global balance changes without requiring the Streamlit application to be redesigned.
