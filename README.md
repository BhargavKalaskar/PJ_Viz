# LILA BLACK — Player Journey Visualization Tool

A browser-based tool for Level Designers to explore 5 days of production gameplay telemetry from LILA BLACK — an extraction shooter with 3 maps, 339 players, and 796 matches.

**Live demo:** *(deploy link goes here after Streamlit Cloud deploy)*

---

## What It Does

- Plots all 8 event types (movement, combat, loot, storm deaths) on top of each map's minimap
- Heatmaps for kill density, death density, and player traffic
- Match timeline playback — watch a match unfold from first drop to last death
- Player journey tracing — follow a single player's path through a match
- Filters by map, date, match, event type, and player type

---

## Tech Stack

| Layer | Tool |
|-------|------|
| UI framework | [Streamlit](https://streamlit.io) |
| Data loading | [PyArrow](https://arrow.apache.org/docs/python/) + [Pandas](https://pandas.pydata.org) |
| Visualization | [Plotly](https://plotly.com/python/) |
| Heatmaps | [NumPy](https://numpy.org) |
| Image handling | [Pillow](https://python-pillow.org) |
| Hosting | [Streamlit Community Cloud](https://share.streamlit.io) |

---

## Run Locally

**Requirements:** Python 3.10+

```bash
# 1. Clone the repo
git clone <repo-url>
cd PJ_Viz

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app expects the `Player_data/` directory to be in the same folder as `app.py`. All parquet files and minimap images are included in the repo (~35 MB total).

---

## Project Structure

```
PJ_Viz/
├── app.py                  # Streamlit UI
├── data_loader.py          # Parquet ingestion + caching
├── coordinate_utils.py     # World → pixel coordinate conversion
├── heatmap_utils.py        # Kill / death / traffic density grids
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── ARCHITECTURE.md         # Tech decisions + data flow
├── INSIGHTS.md             # 3 data-backed findings
└── Player_data/
    ├── February_10/        # 437 parquet files
    ├── February_11/        # 293 parquet files
    ├── February_12/        # 268 parquet files
    ├── February_13/        # 166 parquet files
    ├── February_14/        # 79 parquet files (partial day)
    ├── minimaps/           # AmbroseValley, GrandRift, Lockdown PNG/JPG
    └── README.md           # Data schema documentation
```

---

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select your repo, branch `main`, main file `app.py`
4. Click Deploy — you'll get a public URL in ~2 minutes

No environment variables required. The `Player_data/` folder is bundled with the repo.

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Tech stack rationale, data flow, coordinate mapping math, tradeoffs
- **[INSIGHTS.md](INSIGHTS.md)** — 3 data-backed findings with evidence and actionable recommendations
- **[Player_data/README.md](Player_data/README.md)** — Full data schema: event types, file format, coordinate system
