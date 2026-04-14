# LILA BLACK — Player Journey Visualization Tool

A browser-based tool for Level Designers to explore 5 days of production gameplay telemetry from LILA BLACK — an extraction shooter with 3 maps, 339 players, and 796 matches.

**Live Tool:** https://3du9geedssvn6dwe9xjhvk.streamlit.app/

**Walkthrough Video:** https://drive.google.com/file/d/1SxL34bhgcd24-HICZnI9HPtguLOw0WrR/view?usp=sharing

> ⚠️ **Please lower your volume before watching** — the microphone was very sensitive during recording and the audio is loud.

---

## What Problem Does This Solve?

Level Designers at Lila Games have raw telemetry data but no way to see what's actually happening on their maps. They can't tell if players are using the zones they designed, whether the storm is fair, or where fights are actually breaking out vs where they intended them to happen.

This tool turns 89,104 raw gameplay events into a visual, interactive map that a Level Designer can open in their browser and actually use — no setup, no code, no data science knowledge required.

---

## Features

- **Event markers** — All 8 event types plotted on the minimap with distinct colors and shapes
- **Human vs bot distinction** — Visually separate human player behavior from bot AI patterns
- **Heatmaps** — Kill density, death density, and player traffic overlays across all 3 maps
- **Match timeline** — Watch any match unfold event by event with a playback slider
- **Smart filters** — Filter by map, date, match, event type, and player type instantly
- **Zoom and pan** — Drill into specific map zones to investigate individual events
- **Interactive legend** — Color and shape guide always visible on the map

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| UI framework | Streamlit | Fast to build, instant deployment, no frontend code needed |
| Data loading | PyArrow + Pandas | Native parquet support, fast batch reading of 1,243 files |
| Visualization | Plotly (Scattergl) | WebGL rendering for fast marker display, heatmap support |
| Heatmaps | NumPy | numpy.histogram2d for density grid computation |
| Image handling | Pillow | Minimap resizing and RGBA conversion |
| Hosting | Streamlit Community Cloud | Free, instant public URL, auto-deploys from GitHub |

---

## Run Locally

**Requirements:** Python 3.10+

```bash
# 1. Clone the repo
git clone https://github.com/BhargavKalaskar/PJ_Viz.git
cd PJ_Viz

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app expects the `Player_data/` directory in the same folder as `app.py`. All parquet files and minimap images are included in the repo (~35 MB total).
No environment variables required.

---

## Project Structure

```
PJ_Viz/
├── app.py                  # Streamlit UI — all UI logic
├── data_loader.py          # Parquet ingestion, event decoding, bot classification
├── coordinate_utils.py     # World (x,z) → minimap pixel conversion
├── heatmap_utils.py        # Kill / death / traffic density grids
├── image_utils.py          # Minimap loading and resizing
├── requirements.txt        # Pinned Python dependencies
├── README.md               # This file
├── ARCHITECTURE.md         # Tech decisions, data flow, coordinate math, tradeoffs
├── INSIGHTS.md             # 3 data-backed findings with evidence
├── index.html              # Landing page
└── Player_data/
    ├── February_10/        # 437 parquet files
    ├── February_11/        # 293 parquet files
    ├── February_12/        # 268 parquet files
    ├── February_13/        # 166 parquet files
    ├── February_14/        # 79 parquet files (partial day)
    ├── minimaps/           # AmbroseValley, GrandRift, Lockdown images
    └── README.md           # Original data schema documentation
```

---

## Data

| Metric | Value |
|---|---|
| Date range | February 10–14, 2026 |
| Total events | 89,104 |
| Unique players | 339 |
| Unique matches | 796 |
| Maps | AmbroseValley, GrandRift, Lockdown |
| File format | Apache Parquet (.nakama-0 extension) |

---

## Key Technical Decisions

**Minimap coordinate mapping** — Game world coordinates (x, z) are converted to pixel positions using per-map scale and origin values from the data README. The Y axis is elevation and is ignored for 2D mapping. Full explanation in ARCHITECTURE.md.

**Image resizing** — Minimap images were documented as 1024×1024 but actual dimensions were AmbroseValley 4320×4320 and Lockdown 9000×9000. All images are resized to 1024×1024 at load time via `image_utils.py`. Without this fix the Plotly figure JSON exceeded 169MB causing browser crashes.

**WebGL rendering** — All scatter markers use `go.Scattergl` instead of `go.Scatter` for GPU-accelerated rendering. This reduced interaction latency significantly on large datasets.

**Single cached load** — All 1,243 parquet files are loaded once on startup via `@st.cache_data` and stored as pre-split per-map DataFrames. Subsequent filter operations run against the already-loaded data.

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Tech stack rationale, data flow, coordinate mapping math, tradeoffs table
- **[INSIGHTS.md](INSIGHTS.md)** — 3 data-backed findings with evidence and actionable recommendations
- **[Player_data/README.md](Player_data/README.md)** — Original data schema: event types, file format, coordinate system
