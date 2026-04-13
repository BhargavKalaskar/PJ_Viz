"""
coordinate_utils.py
-------------------
Converts game-world (x, z) coordinates to minimap pixel coordinates.

Each map has its own scale and origin values (from Player_data/README.md).
The y column in the parquet data is elevation — irrelevant for 2D mapping.

Formula:
    u = (x - origin_x) / scale
    v = (z - origin_z) / scale
    pixel_x = u * 1024
    pixel_y = (1 - v) * 1024   ← Y is flipped: image origin is top-left
"""

from __future__ import annotations

import pandas as pd

# Per-map configuration sourced from Player_data/README.md
MAP_CONFIG: dict[str, dict[str, float]] = {
    "AmbroseValley": {"scale": 900.0,  "origin_x": -370.0, "origin_z": -473.0},
    "GrandRift":     {"scale": 581.0,  "origin_x": -290.0, "origin_z": -290.0},
    "Lockdown":      {"scale": 1000.0, "origin_x": -500.0, "origin_z": -500.0},
}

IMAGE_SIZE = 1024  # all minimaps are 1024×1024 px


def world_to_pixel(x: float, z: float, map_id: str) -> tuple[float, float]:
    """Convert a single world (x, z) position to minimap pixel coordinates.

    Args:
        x: World X coordinate.
        z: World Z coordinate.
        map_id: One of 'AmbroseValley', 'GrandRift', 'Lockdown'.

    Returns:
        (pixel_x, pixel_y) in the 0–1024 range.

    Raises:
        KeyError: If map_id is not in MAP_CONFIG.
    """
    cfg = MAP_CONFIG[map_id]
    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]
    return u * IMAGE_SIZE, (1.0 - v) * IMAGE_SIZE


def add_pixel_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized: add px_x and px_y columns to a dataframe.

    Groups by map_id so each row uses the correct per-map config.
    Operates on the x and z columns; y (elevation) is ignored.

    Args:
        df: DataFrame with columns 'x', 'z', 'map_id'.

    Returns:
        The same DataFrame with new columns 'px_x' and 'px_y' appended.
    """
    df = df.copy()
    df["px_x"] = 0.0
    df["px_y"] = 0.0

    for map_id, cfg in MAP_CONFIG.items():
        mask = df["map_id"] == map_id
        if not mask.any():
            continue
        u = (df.loc[mask, "x"] - cfg["origin_x"]) / cfg["scale"]
        v = (df.loc[mask, "z"] - cfg["origin_z"]) / cfg["scale"]
        df.loc[mask, "px_x"] = u * IMAGE_SIZE
        df.loc[mask, "px_y"] = (1.0 - v) * IMAGE_SIZE

    return df
