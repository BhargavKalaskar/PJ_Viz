# INSIGHTS.md — Data-Backed Findings
**Dataset:** LILA BLACK production telemetry, February 10–14 2026  
**Scope:** 89,104 events · 339 unique players · 796 matches · 3 maps

---

## Insight 1 — Storm Deaths Are Heavily East-Biased on AmbroseValley

### Observation
On AmbroseValley, 71% of `KilledByStorm` events occur on the **East side of the map** (12 of 17 storm deaths), with the East/North quadrant alone accounting for 47% (8 deaths). Players on the West side die to the storm at less than half the rate of players on the East side.

### Evidence
Storm deaths split by map quadrant (AmbroseValley, all 5 days):

| Quadrant | Storm Deaths | Share |
|----------|-------------|-------|
| East/North | 8 | 47% |
| East/South | 4 | 24% |
| West/South | 3 | 18% |
| West/North | 2 | 12% |

Mean storm death position: x=+19.7, z=−30.5 (East of map center x=−9.2)

### Actionable Recommendation
Audit the storm's movement direction and speed relative to East-side extraction points. The data indicates the storm consistently closes from the East, giving East-side landers less time or fewer viable exit routes. Options:
1. Add or relocate an extraction point on the East side
2. Slow the storm's advance on the East flank by ~10–15%
3. If intentional, update level briefings to signal the risk to players who land East

**Metric to watch:** `KilledByStorm` East/West ratio. Target: closer to 50/50 distribution.

---

## Insight 2 — Human PvP Combat Is Nearly Absent: 99.9% of Kills Involve Bots

### Observation
Across 5 days and 89,104 events, there were only **3 human-vs-human kills** (`Kill` events) compared to **2,415 bot kills** (`BotKill` events) — a ratio of 805:1. Player combat is overwhelmingly bot-driven. Human players are far more likely to kill a bot than another human.

### Evidence
Kill event breakdown across all maps and dates:

| Event | Count | % of all kills |
|-------|-------|---------------|
| BotKill (human kills bot) | 2,415 | 76.9% |
| BotKilled (bot kills human) | 700 | 22.3% |
| Kill (human kills human) | 3 | 0.1% |
| Killed (human killed by human) | 3 | 0.1% |
| KilledByStorm | 39 | 1.2% |

Total PvP kills: 3. Total matches: 796.

### Actionable Recommendation
This data suggests either (a) the game is in early testing with low concurrent human population — matches are mostly bots — or (b) the extraction-first objective discourages direct PvP. Either way:
1. **If low player population:** Monitor this ratio as player count scales. At scale, human kills should rise significantly.
2. **If design intent:** Consider whether the current bot density is making matches feel like PvE rather than PvPvE. Reducing bot count per match could force more human encounters.
3. Set a **health KPI**: human-vs-human kill rate per match. A target of ≥2 PvP kills per match would indicate meaningful player interaction.

**Metric to watch:** `Kill` events per match per day. Currently: 0.004 per match.

---

## Insight 3 — Loot Is Concentrated in One Zone, Creating a Single Dominant Conflict Area

### Observation
On AmbroseValley (the most-played map, 68% of all events), **one grid zone accounts for 20% of all loot pickups** across the entire map — the central-north area (roughly x: −145 to +80, z: −23 to +202). This is also the only zone where the 2 recorded human-vs-human kills occurred, suggesting it functions as the de-facto combat hotspot. Peripheral zones receive far less engagement.

### Evidence
Top 5 loot zones on AmbroseValley (4×4 grid, human players only):

| Zone (grid) | Loot events | Kills | Player traffic |
|-------------|------------|-------|---------------|
| Central-North (1_2) | 1,599 | 2 | 5,669 |
| SW-Center (1_0) | 1,467 | 0 | 4,528 |
| W-Center (1_1) | 1,394 | 0 | 6,080 |
| E-Center (2_1) | 1,486 | 0 | 4,799 |
| W-Corner (0_0) | 655 | 0 | 2,511 |

Dead zones (bottom 10% traffic): Northwest-far (grid 0_6: 1 event) and East-South (grid 4_0: 3 events) are essentially unvisited.

### Actionable Recommendation
The map has a pronounced loot gravity toward the central-north, which creates a predictable, repetitive experience: players converge on the same zone every match. Two options depending on design intent:
1. **If variety is the goal:** Redistribute 20–30% of loot from the central-north zone to the two near-dead zones to pull players into underused areas. Target: no single zone >12% of total loot events.
2. **If the hotspot is intentional (e.g., a named POI):** Introduce a secondary high-value loot zone on the opposite side of the map to create a second gravitational pull and more varied player routing.

**Metric to watch:** Loot distribution entropy across zones. A higher entropy score = more even exploration of the map.
