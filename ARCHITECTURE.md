# ARCHITECTURE.md — Player Journey Visualization Tool

## Visual References

> These diagrams were created during the product planning phase before a single line of code was written.

| Diagram | Description |
|---|---|
| [System Architecture Overview](Docs/system_architecture_overview.svg) | Three layer structure — data, processing, frontend |
| [Data Flow Pipeline](Docs/data_flow_pipeline.svg) | Step by step from parquet file to map marker on screen |
| [Level Designer User Flow](Docs/level_designer_user_flow.svg) | How the tool is actually used — three investigation modes |

---

## Why This Architecture

Three problems to solve:

1. Load 1,243 parquet files fast enough that the app is usable
2. Convert game-world coordinates to pixel positions accurately for all 3 maps
3. Serve a live shareable URL with no setup required on the recipient's end

The architecture is intentionally simple — three layers, five files, one deploy target.

---

## System Overview

```
┌─────────────────────────────────────────────────┐
│  DATA LAYER                                     │
│  Player_data/February_*/  →  1,243 .nakama-0    │
│  Player_data/minimaps/    →  3 PNG/JPG images   │
│  coordinate_utils.py      →  map scale + origin │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  PROCESSING LAYER  (Python, Streamlit Cloud)    │
│  data_loader.py      →  reads + caches all data │
│  coordinate_utils.py →  world (x,z) → pixel     │
│  heatmap_utils.py    →  2D density grids        │
│  image_utils.py      →  minimap resize + cache  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  FRONTEND LAYER  (Streamlit UI in browser)      │
│  app.py  →  sidebar filters                     │
│          →  Plotly Scattergl (WebGL markers)    │
│          →  timeline slider + play button       │
│          →  heatmap overlay + legend            │
└─────────────────────────────────────────────────┘
                       │
            Streamlit Community Cloud
            https://3du9geedssvn6dwe9xjhvk.streamlit.app
```

---

## Data Flow — Step by Step

**Step 1 — Startup cache**
`data_loader.load_all_data()` runs once decorated with `@st.cache_data`. Scans all 5 daily folders using `pyarrow.dataset.dataset()` — a single batch operation, not a Python loop. All 1,243 files load into one DataFrame (~89,000 rows). Data is pre-split into per-map DataFrames for faster subsequent filtering.

**Step 2 — Event decoding**
The `event` column is stored as raw bytes in parquet (`b'Position'`). Decoded to UTF-8 string at load time once — not at query time.

**Step 3 — Bot classification**
Each row tagged `is_bot = True/False` by checking whether `user_id` is a UUID (human) or short numeric string (bot). Human UUIDs are 36-character hyphenated hex strings. Bot IDs are numeric (e.g. `"1440"`).

**Step 4 — Minimap loading**
`image_utils.load_minimap()` loads each minimap via Pillow, resizes to exactly 1024×1024 (see Assumptions), converts to RGBA numpy array, and caches the result. Resize runs once per session — never per render.

**Step 5 — Filter application**
When user changes a sidebar control, Streamlit re-runs `app.py`. The cached per-map DataFrame is sliced in-memory using pandas boolean indexing — date, match, event type, player type filters applied in sequence on the already-small map subset.

**Step 6 — Coordinate conversion**
`coordinate_utils.add_pixel_coords()` runs on the filtered subset only, adding `px_x` and `px_y` columns vectorially per map group.

**Step 7 — Figure construction**
`build_figure()` constructs a Plotly figure with:
- `go.Image` as the base layer (minimap numpy array)
- `go.Scattergl` traces per event type (WebGL GPU-accelerated rendering)
- `go.Heatmap` overlay when heatmap mode is active

Decorated with `@st.cache_data(max_entries=10)` — identical filter states return instantly from cache.

**Step 8 — Browser render**
`st.plotly_chart()` sends the figure JSON (~10MB) to the browser. Plotly.js renders entirely client-side via WebGL.

---

## Coordinate Mapping — The Tricky Part

The game world uses a 3D coordinate system. Only `x` (east-west) and `z` (north-south) are used for 2D mapping. `y` is elevation — ignored entirely.

Minimap images are 1024×1024 pixels. The challenge: mapping a world position like `(-301, -355)` to a pixel like `(78, 890)`.

**Formula:**
```
u = (x - origin_x) / scale       # normalize to 0–1 range
v = (z - origin_z) / scale       # normalize to 0–1 range

pixel_x = u × 1024
pixel_y = (1 - v) × 1024         ← Y axis is flipped
```

**Why the Y flip?** Image coordinates start at top-left — y increases downward. Game-world Z increases northward (upward). Without the flip the entire map renders upside-down.

**Verified against README example:**
World `(-301.45, -355.55)` → pixel `(78, 890)` ✓ Exact match confirmed in smoke test.

**Per-map configuration:**

| Map | Scale | Origin X | Origin Z |
|---|---|---|---|
| AmbroseValley | 900 | −370 | −473 |
| GrandRift | 581 | −290 | −290 |
| Lockdown | 1000 | −500 | −500 |

Single source of truth lives in `coordinate_utils.MAP_CONFIG`.

---

## Assumptions Made

**Minimap dimensions** — README states all minimaps are 1024×1024. Actual dimensions discovered during build: AmbroseValley was 4320×4320, Lockdown was 9000×9000. All images resized to 1024×1024 at load time via `image_utils.py`. Without this fix the Plotly figure JSON exceeded 169MB causing browser Out of Memory crashes. Peak memory went from 897MB → 38MB after the fix.

**Timestamp units** — The `ts` column is stored as `datetime64[ms]` in parquet but underlying values represent Unix seconds not milliseconds. A `// 1_000_000` division in the original loader collapsed both `ts_min` and `ts_max` to the same value (1770), making timeline duration = 0 and the slider non-functional. Fixed by storing as `int64` seconds directly.

**Kill event coordinates** — BotKill and Kill event coordinates record where the eliminated entity died, not where the attacker was standing. A BotKill marker appearing without nearby human Position dots is expected — the human player may have been firing from range. This is a data design decision in the telemetry system, not a mapping error.

**February 14 partial day** — Included as-is, not weighted differently. All three insights are consistent across all 5 days including the partial day.

**Bot classification** — UUID `user_id` = human, numeric `user_id` = bot. Verified against README and confirmed by event type correlation.

**Corrupted files** — Any file raising an exception during load is silently skipped. Treated as missing data, not errors.

---

## Major Tradeoffs

| Decision | Chosen | Gave Up | Why |
|---|---|---|---|
| Streamlit vs React | Streamlit | UI polish, layout control | 5 day build — Streamlit ships in hours not days |
| Load-all vs lazy load | Load-all on startup | Slower cold start | Fast filter response matters more for exploratory sessions |
| Plotly Scattergl vs D3 | Plotly Scattergl | Custom rendering flexibility | WebGL built-in, heatmap support, native Streamlit integration |
| PyArrow dataset vs loop | PyArrow batch | Slightly more complex code | 3× faster file loading across 1,243 files |
| Per-map pre-split | Pre-split DataFrame | More memory | First filter is always map — eliminates 68% of rows before any user filter |
| Scattergl vs Scatter | Scattergl | Some marker symbol options | GPU rendering — 10-50× faster for large point counts |
| Scroll zoom re-enabled | Zoom on | Potential slider conflict | Level Designers need zoom to investigate specific map zones |
| Streamlit Cloud vs Railway | Streamlit Cloud | More compute, custom domain | Zero config, always free, auto-deploys from GitHub |

---

## Performance Notes

**The memory crash we solved:** Initial Plotly figure JSON was 169MB because minimap images were 4–9× larger than documented in the README. Peak memory hit 897MB before any scatter points were added. After resizing to 1024×1024 at load time: figure JSON dropped to ~10MB, peak memory to 38MB — a 96% reduction.

**Render latency:** Python-side filtering runs in 5–10ms. Remaining latency is Plotly figure serialization (~10MB JSON) and browser-side WebGL rendering. This is a client-side cost that cannot be eliminated without changing the rendering approach entirely. Acceptable for a data exploration tool used in deliberate analytical sessions, not real-time interaction.

**Scattergl rendering artifacts:** Triangle marker symbols in Scattergl's WebGL renderer produce edge artifacts (white dust particles) at certain opacity levels. Fixed by removing the white outline from triangle traces specifically — circles and squares retain the white outline for visibility against varied map backgrounds.

---

## Supporting Documentation

- [Functional Requirements](Docs/Functional%20requirements.docx) — full FR list with priority stack
- [User Journey](Docs/User%20flows_journey%20maps.docx) — Level Designer investigation modes and decision points
