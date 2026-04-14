# INSIGHTS.md — Data-Backed Findings

**Dataset:** LILA BLACK production telemetry, February 10–14 2026  
**Scope:** 89,104 events · 339 unique players · 796 matches · 3 maps  
**Tool:** LILA BLACK Player Journey Visualization Tool  

---

## Insight 1 — Storm Deaths Are Heavily East-Biased on AmbroseValley

### What Caught My Eye
When I toggled on the KilledByStorm layer on AmbroseValley and filtered to human-only events, almost all the purple markers were clustered on the right (East) side of the map. The West side was nearly empty of storm deaths. That asymmetry was immediately visible without any calculation.

### The Evidence
Storm deaths split by map quadrant (AmbroseValley, all 5 days):

| Quadrant | Storm Deaths | Share |
|---|---|---|
| East/North | 8 | 47% |
| East/South | 4 | 24% |
| West/South | 3 | 18% |
| West/North | 2 | 12% |

71% of all KilledByStorm events (12 of 17) occur on the East side. Mean storm death position: x=+19.7, z=−30.5 — East of map center at x=−9.2. Players on the West side die to the storm at less than half the rate of East-side players.

### Why A Level Designer Should Care
The storm is supposed to be a neutral environmental hazard that applies pressure equally across the map. If 71% of storm deaths are happening on one side, it means either the storm path consistently closes from the East — giving East-side landers less time and fewer viable exit routes — or East-side extraction points are inadequate. Players who land East are being systematically punished by map design, not by their own decisions.

### Actionable Recommendations
1. Audit the storm's movement direction and speed relative to East-side extraction points
2. Add or relocate an extraction point on the East side of AmbroseValley
3. Slow the storm's advance on the East flank by 10–15%
4. If the asymmetry is intentional, update in-game level briefings to signal the risk to players landing East

**Metrics affected:** KilledByStorm East/West ratio. Current: 71/29. Target: closer to 50/50.

---

## Insight 2 — Human PvP Is Nearly Absent: The Game Is Playing Like Pure PvE

### What Caught My Eye
I filtered to Kill events only (human killed human) expecting to see combat hotspots across the map. The map was almost completely empty. Switching to BotKill events lit up the entire map. Something was clearly wrong with the ratio.

### The Evidence
Kill event breakdown across all maps and all 5 days:

| Event | Count | % of all kills |
|---|---|---|
| BotKill — human killed a bot | 2,415 | 76.9% |
| BotKilled — bot killed a human | 700 | 22.3% |
| Kill — human killed a human | 3 | 0.1% |
| Killed — human killed by human | 3 | 0.1% |
| KilledByStorm | 39 | 1.2% |

Total human vs human kills across 796 matches over 5 days: **3.**
That is a 805:1 bot kill to human kill ratio.
Current human PvP rate: 0.004 kills per match.

### Why A Level Designer Should Care
LILA BLACK is designed as an extraction shooter — a PvPvE genre where human vs human combat is a core tension. At 3 PvP kills across 796 matches, the game is functionally playing as a PvE experience. This could mean two things: the player population is still in early testing with mostly bot-filled lobbies, or the extraction objective is so dominant that players are avoiding conflict entirely. Either way, map design may be contributing — if players can extract without ever crossing paths, the maps aren't creating the forced encounters the genre depends on.

### Actionable Recommendations
1. Audit extraction point placement — are players able to extract from isolated corners without crossing the main play area?
2. Consider reducing bot density per match to force human players into proximity
3. Add chokepoints between high-loot zones and extraction points to create unavoidable human encounters
4. Set a health KPI: target ≥2 human vs human kills per match as a baseline for meaningful PvP tension

**Metrics affected:** Kill event count per match. Current: 0.004. Target: 2+.

---

## Insight 3 — Loot Gravity Is Pulling Every Player Into One Zone, Making Matches Predictable

### What Caught My Eye
When I switched to the traffic heatmap on AmbroseValley the heat was almost entirely concentrated in one area — the central-north zone. Switching to the loot layer confirmed it — one zone had significantly more loot pickups than anywhere else on the map. The peripheral areas were practically empty.

### The Evidence
Top loot zones on AmbroseValley (human players only, all 5 days):

| Zone | Loot Events | Player Traffic | PvP Kills |
|---|---|---|---|
| Central-North | 1,599 | 5,669 | 2 |
| SW-Center | 1,467 | 4,528 | 0 |
| W-Center | 1,394 | 6,080 | 0 |
| E-Center | 1,486 | 4,799 | 0 |
| W-Corner | 655 | 2,511 | 0 |

The central-north zone accounts for 20% of all loot pickups on AmbroseValley. It is also the only zone where human vs human kills occurred — both of the 2 recorded PvP kills on this map happened here. Dead zones exist: Northwest-far (1 event total) and East-South (3 events total) are essentially unvisited across 5 days of matches.

### Why A Level Designer Should Care
When loot is concentrated in one zone, player routing becomes predictable and repetitive. Every match plays out the same way — players converge on the central-north, the few PvP encounters that happen all happen in the same spot, and large portions of the map go completely unvisited. This reduces map variety, shortens the effective play area, and wastes the design investment in peripheral zones. The dead zones in the Northwest and East-South represent real estate the Level Designer built but nobody is using.

### Actionable Recommendations
1. Redistribute 20–30% of loot from the central-north zone to the two near-dead zones to pull players into underused areas
2. Introduce a secondary high-value loot zone on the opposite side of the map to create a second gravitational pull and more varied player routing
3. Add environmental incentives (cover, verticality, unique assets) to dead zones to make them worth visiting even without loot
4. Target: no single zone should account for more than 12% of total loot events

**Metrics affected:** Loot distribution entropy across zones. Player traffic spread. Dead zone visit rate. Current dead zone visit rate: <0.1% of total events.

---

## Data Notes

**Kill event coordinates** record where the eliminated entity died, not where the attacker was standing. A BotKill marker appearing without nearby human Position dots is expected — the human player may have been firing from several meters away. Combat range analysis would require cross-referencing kill events with the nearest preceding Position event of the same player.

**Position events** are sampled periodically, not continuously. Players move between samples without generating position records. This means movement paths are approximations, not exact traces.

**February 14 is a partial day** — data collection was still ongoing. Insights 1-3 are consistent across all 5 days including the partial day, suggesting the patterns are structural rather than date-specific.
