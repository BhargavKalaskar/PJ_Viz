"""
data_loader.py
--------------
Loads all player event data from the Player_data/ folder tree.

Design decisions:
- Uses pyarrow.dataset to scan all 1,243 files in a single pass (faster than
  a Python loop of individual pq.read_table() calls).
- Cached with @st.cache_data so the heavy load only runs once per session.
- Decodes the 'event' column from bytes to str automatically.
- Classifies each row as human or bot based on the user_id format:
    UUID  → human   (e.g. "f4e072fa-b7af-4761-b567-1d95b7ad0108")
    numeric → bot   (e.g. "1440")
- Extracts the calendar date from the folder name (February_10 → "Feb 10").
- Skips unreadable files silently (FR-1.5).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import streamlit as st

# Folder names → display labels
DATE_FOLDERS: dict[str, str] = {
    "February_10": "Feb 10",
    "February_11": "Feb 11",
    "February_12": "Feb 12",
    "February_13": "Feb 13",
    "February_14": "Feb 14",
}

# Regex that matches a UUID user_id (human players)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_human(user_id: str) -> bool:
    return bool(_UUID_RE.match(str(user_id)))


def _load_folder(folder_path: Path, date_label: str) -> pd.DataFrame | None:
    """Load all parquet files from one daily folder into a single DataFrame."""
    files = [
        str(p)
        for p in folder_path.iterdir()
        if p.is_file() and not p.name.startswith(".")
    ]
    if not files:
        return None

    frames: list[pd.DataFrame] = []
    for filepath in files:
        try:
            table = ds.dataset(filepath, format="parquet").to_table()
            frames.append(table.to_pandas())
        except Exception:
            # Skip corrupted / non-parquet files silently (FR-1.5)
            continue

    if not frames:
        return None

    df = pd.concat(frames, ignore_index=True)
    df["date"] = date_label
    return df


@st.cache_data(show_spinner="Loading player data — this takes ~10 seconds on first run…")
def load_all_data(data_root: str) -> pd.DataFrame:
    """Load and return all player event data across all 5 daily folders.

    Post-processing applied:
    - 'event' column decoded from bytes → str
    - 'is_bot' boolean column added
    - 'date' column added (e.g. "Feb 10")
    - 'ts' cast to int64 milliseconds for consistent arithmetic
    - Rows with missing x/z dropped

    Args:
        data_root: Absolute path to the Player_data/ directory.

    Returns:
        A single concatenated DataFrame with all events.
    """
    root = Path(data_root)
    all_frames: list[pd.DataFrame] = []

    for folder_name, date_label in DATE_FOLDERS.items():
        folder_path = root / folder_name
        if not folder_path.exists():
            continue
        df = _load_folder(folder_path, date_label)
        if df is not None:
            all_frames.append(df)

    if not all_frames:
        raise FileNotFoundError(f"No data found under {data_root}")

    combined = pd.concat(all_frames, ignore_index=True)

    # Decode event bytes → string
    combined["event"] = combined["event"].apply(
        lambda v: v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)
    )

    # Bot classification: UUID = human, numeric = bot
    combined["is_bot"] = ~combined["user_id"].astype(str).apply(_is_human)

    # Normalise timestamp to int64.
    # The parquet schema says datetime64[ms] but the stored integers are Unix
    # timestamps in SECONDS (verified: value 1770754537 = 2026-02-10 20:15:37).
    # This is a schema mislabelling in the game's data pipeline.
    # .astype("int64") on datetime64[ms] returns the raw integer, which here
    # equals the Unix timestamp in seconds. All timeline arithmetic therefore
    # works in seconds — do NOT divide by 1_000 or 1_000_000.
    if pd.api.types.is_datetime64_any_dtype(combined["ts"]):
        combined["ts"] = combined["ts"].astype("int64")
    else:
        combined["ts"] = pd.to_numeric(combined["ts"], errors="coerce")

    # Drop rows where spatial data is unusable
    combined = combined.dropna(subset=["x", "z"])

    # Clean up match_id — strip the '.nakama-0' suffix for display
    combined["match_id_clean"] = (
        combined["match_id"].astype(str).str.replace(r"\.nakama-0$", "", regex=True)
    )

    # Convert frequently-filtered string columns to categoricals.
    # Categorical filtering is 5–10× faster than string filtering in pandas
    # because comparisons operate on integer codes, not string data.
    combined["event"]  = combined["event"].astype("category")
    combined["map_id"] = combined["map_id"].astype("category")
    combined["date"]   = combined["date"].astype("category")

    # Pre-split by map. Map selection is the first filter on every interaction;
    # starting from ~30k rows instead of ~89k rows makes every subsequent
    # filter and groupby ~3× faster.
    map_dfs: dict[str, pd.DataFrame] = {
        map_id: combined[combined["map_id"] == map_id].reset_index(drop=True)
        for map_id in ("AmbroseValley", "GrandRift", "Lockdown")
    }

    # Pre-compute match-dropdown options per map so the sidebar groupby never
    # runs at render time (only runs once here at startup).
    match_options_cache: dict[str, dict[str, str]] = {
        map_id: get_match_options(df)
        for map_id, df in map_dfs.items()
    }

    return {
        "all": combined,
        **map_dfs,
        "match_options": match_options_cache,
    }


def get_match_options(df: pd.DataFrame) -> dict[str, str]:
    """Return {display_label: match_id} for populating the match dropdown.

    Display label format: "<short_id> — <n> players"
    """
    counts = (
        df[~df["is_bot"]]
        .groupby("match_id")["user_id"]
        .nunique()
        .reset_index()
        .rename(columns={"user_id": "human_count"})
    )
    options: dict[str, str] = {}
    for _, row in counts.iterrows():
        short = str(row["match_id"])[:8]
        label = f"{short}… — {int(row['human_count'])} players"
        options[label] = row["match_id"]
    return options
