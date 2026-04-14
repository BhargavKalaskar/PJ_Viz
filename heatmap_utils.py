"""
heatmap_utils.py
----------------
Builds 2D density grids from filtered player event data.

Each heatmap type answers a different Level Designer question:
  Kill heatmap    → "Where is combat actually happening?"
  Death heatmap   → "Where are players dying — including storm deaths?"
  Traffic heatmap → "Where do players spend their time on this map?"

The density grid is a 2D numpy array (bins × bins) produced by
numpy.histogram2d, then rendered as a Plotly go.Heatmap overlay on
top of the minimap image.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

# Event type groupings
KILL_EVENTS   = {"Kill", "BotKill"}
DEATH_EVENTS  = {"Killed", "BotKilled", "KilledByStorm"}
MOVE_EVENTS   = {"Position", "BotPosition"}

IMAGE_SIZE = 1024  # minimap pixel dimensions
DEFAULT_BINS = 128  # grid resolution — higher = finer detail, slower render


def build_density_grid(
    px_x: pd.Series,
    px_y: pd.Series,
    bins: int = DEFAULT_BINS,
) -> np.ndarray:
    """Build a 2D density array from minimap pixel coordinates.

    Args:
        px_x: Series of pixel X coordinates (0–1024).
        px_y: Series of pixel Y coordinates (0–1024).
        bins: Grid resolution. Higher = finer, slower.

    Returns:
        2D numpy array of shape (bins, bins). Values are event counts per cell.
        Returns a zero array if the input is empty.
    """
    if px_x.empty or px_y.empty:
        return np.zeros((bins, bins))

    grid, _, _ = np.histogram2d(
        px_x.clip(0, IMAGE_SIZE),
        px_y.clip(0, IMAGE_SIZE),
        bins=bins,
        range=[[0, IMAGE_SIZE], [0, IMAGE_SIZE]],
    )
    # Transpose so grid[row, col] maps naturally to (y, x) in image space
    return grid.T


@st.cache_data(max_entries=20, show_spinner=False)
def get_kill_heatmap(df: pd.DataFrame, bins: int = DEFAULT_BINS) -> np.ndarray:
    """Density grid for Kill + BotKill events.

    Args:
        df: Filtered DataFrame with px_x, px_y, event columns.
        bins: Grid resolution.

    Returns:
        2D density array.
    """
    subset = df[df["event"].isin(KILL_EVENTS)]
    return build_density_grid(subset["px_x"], subset["px_y"], bins)


@st.cache_data(max_entries=20, show_spinner=False)
def get_death_heatmap(df: pd.DataFrame, bins: int = DEFAULT_BINS) -> np.ndarray:
    """Density grid for Killed + BotKilled + KilledByStorm events.

    Args:
        df: Filtered DataFrame with px_x, px_y, event columns.
        bins: Grid resolution.

    Returns:
        2D density array.
    """
    subset = df[df["event"].isin(DEATH_EVENTS)]
    return build_density_grid(subset["px_x"], subset["px_y"], bins)


@st.cache_data(max_entries=20, show_spinner=False)
def get_traffic_heatmap(df: pd.DataFrame, bins: int = DEFAULT_BINS) -> np.ndarray:
    """Density grid for Position + BotPosition events (player movement).

    Args:
        df: Filtered DataFrame with px_x, px_y, event columns.
        bins: Grid resolution.

    Returns:
        2D density array.
    """
    subset = df[df["event"].isin(MOVE_EVENTS)]
    return build_density_grid(subset["px_x"], subset["px_y"], bins)
