# ARCHITECTURE.md — Player Journey Visualization Tool

## Why This Architecture

The tool needs to solve three specific problems:
1. Load 1,243 parquet files fast enough that the app is usable
2. Convert game-world coordinates to pixel positions accurately for all 3 maps
3. Serve a live, shareable URL with no setup required on the recipient's end

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
│  PROCESSING LAYER  (Python, runs on Streamlit)  │
│  data_loader.py      →  reads + caches all data │
│  coordinate_utils.py →  world (x,z) → pixel     │
│  heatmap_utils.py    →  2D density grids        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  FRONTEND LAYER  (Streamlit UI in browser)      │
│  app.py  →  sidebar filters                     │
│          →  Plotly figure (image + markers)     │
│          →  timeline slider + play              │
└─────────────────────────────────────────────────┘
                       │
            Streamlit Community Cloud
            (free hosting, public URL)
```

---

## Data Flow — Step by Step

**Step 1 — Startup cache**  
`data_loader.load_all_data()` runs once and is decorated with `@st.cache_data`. It scans all 5 daily folders using `pyarrow.dataset.dataset()`, which reads parquet files in a single batch operation rather than a Python loop. All 1,243 files are concatenated into one DataFrame (~89,000 rows). Subsequent filter changes never re-read disk.

**Step 2 — Event decoding**  
The `event` column is stored as raw bytes in parquet (`b'Position'`). It is decoded to a UTF-8 string during load. This is done once at load time, not at query time.

**Step 3 — Bot classification**  
Each row is tagged `is_bot = True/False` by checking whether `user_id` matches the UUID regex pattern. Human UUIDs are 36-character hyphenated hex strings. Bot IDs are short numeric strings (e.g. `"1440"`).

**Step 4 — Filter application**  
When the user changes a sidebar control, Streamlit re-runs `app.py`. The cached DataFrame is sliced in-memory using pandas boolean indexing — map, date, match, event type, player type filters are applied in sequence.

**Step 5 — Coordinate conversion**  
`coordinate_utils.add_pixel_coords()` runs on the filtered subset (not the full dataset), adding `px_x` and `px_y` columns. It groups by `map_id` and applies the correct per-map formula vectorially.

**Step 6 — Visualization**  
`app.py:build_figure()` constructs a Plotly `go.Figure` with:
- `go.Image` as the base layer (minimap loaded via Pillow → numpy array)
- `go.Scatter` traces for event markers (one trace per event type)
- `go.Heatmap` overlay when heatmap mode is active

**Step 7 — Render**  
`st.plotly_chart()` sends the figure to the browser. Plotly renders entirely client-side via WebGL.

---

## Coordinate Mapping — Explained

The game world uses a 3D coordinate system. Only `x` (east-west) and `z` (north-south) are used for 2D mapping. `y` is elevation and is ignored entirely.

The minimap images are 1024×1024 pixels. The challenge: mapping a world position like `(-301, -355)` to a pixel like `(78, 890)`.

**Formula:**
```
u = (x - origin_x) / scale       # normalize to 0–1
v = (z - origin_z) / scale       # normalize to 0–1

pixel_x = u × 1024
pixel_y = (1 - v) × 1024         ← Y is flipped
```

**Why the Y flip?** Image coordinates start at the top-left (y increases downward). Game-world Z increases going "up" (northward). Without the flip, the map would be rendered upside-down.

**Per-map configuration** (from Player_data/README.md):

| Map | Scale | Origin X | Origin Z |
|-----|-------|----------|----------|
| AmbroseValley | 900 | −370 | −473 |
| GrandRift | 581 | −290 | −290 |
| Lockdown | 1000 | −500 | −500 |

This config lives in `coordinate_utils.MAP_CONFIG` — the single source of truth. It is used by both `world_to_pixel()` (single-point conversion) and `add_pixel_coords()` (vectorized batch conversion).

---

## Tech Stack Decisions

### Python + Streamlit vs React
Streamlit was chosen for speed of execution. With 1–2 days to build, a React app would spend half that time on boilerplate (bundler config, state management, API layer). Streamlit gives sidebar filters, sliders, file serving, and a live URL from Python alone. The tradeoff is less control over UI polish — but a working tool beats a beautiful skeleton.

### PyArrow Dataset vs pandas `read_parquet` loop
`pyarrow.dataset.dataset()` scans a collection of files as a single dataset object, enabling vectorized reads with column pushdown filtering. A Python `for` loop calling `pq.read_table()` on each file adds ~1,243 round-trips of overhead. In practice this is ~3× faster on this dataset.

### Plotly vs D3 or Matplotlib
Plotly was the only library that handles both requirements with one API: placing scatter markers on top of an image as a base layer, and rendering density heatmaps with opacity. Matplotlib lacks the interactivity. D3 requires writing JavaScript. Plotly does both in Python and integrates directly with `st.plotly_chart`.

### Load-all vs Lazy Loading
All data is loaded on startup and cached. The filtered result is always a pandas slice of the same in-memory DataFrame — no disk I/O after the initial load. The tradeoff is a slower first load (~10–15s) but near-instant filter responses. Given the use case (a Level Designer actively exploring the data), fast filter response was prioritized over fast startup.

### Streamlit Community Cloud vs Railway/Heroku
Streamlit Community Cloud is free forever for one public app and deploys directly from a GitHub repo. It requires zero infrastructure knowledge. Railway and Render have free tiers but impose build complexity and sleep timeouts. For this assignment, zero-friction deployment was the right call.

---

## Assumptions Made

- `February_14` is a partial day (per README). It is included but not weighted differently.
- Files with no `.parquet` extension are valid parquet files — the format is identified by magic bytes, not extension.
- The `y` column (elevation) is intentionally excluded from all 2D visualizations.
- `ts` values represent elapsed milliseconds within a match, not wall-clock timestamps.
- Any file that raises an exception during load is silently skipped (corrupted files are treated as missing data, not errors).

---

## Tradeoffs Summary

| Decision | Chosen | Gave Up |
|----------|--------|---------|
| Streamlit vs React | Faster build, instant deploy | UI polish + fine layout control |
| Load-all on startup | Fast filter response | Slower cold start (~15s) |
| Plotly vs D3 | Simple code, works in Streamlit | Custom rendering flexibility |
| Single master DataFrame | Easy filtering logic | Higher peak memory usage |
| Streamlit Cloud vs Railway | Zero config, always free | More compute, custom domains |
| PyArrow dataset vs loop | 3× faster file loading | Slightly more complex code |
