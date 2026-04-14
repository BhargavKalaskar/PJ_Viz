"""
image_utils.py
--------------
Loads and resizes minimap images to the canonical 1024x1024 size used by the
coordinate system. Cached with st.cache_data so resizing happens once per
session, not on every figure rebuild.

Actual minimap dimensions on disk (all oversized):
  AmbroseValley: 4320x4320  (74.6 MB as RGBA array)
  GrandRift:     2160x2158  (18.6 MB as RGBA array)
  Lockdown:      9000x9000  (324 MB as RGBA array)

After resize to 1024x1024 RGBA each is ~4 MB — a ~50x reduction for Lockdown.

Robustness features:
- Case-insensitive path resolution: scans the parent directory and matches
  filenames without regard to case. Fixes Linux/Windows casing mismatches.
- Dark fallback: if the image cannot be found or loaded for any reason,
  returns a plain dark 1024x1024 RGBA array so markers and heatmaps still
  render correctly rather than crashing with an error.
"""

from __future__ import annotations

import os

import numpy as np
import streamlit as st
from PIL import Image

TARGET_SIZE = (1024, 1024)

# Dark grey background used when a minimap file cannot be loaded
_FALLBACK_COLOR = (30, 30, 35, 255)  # RGBA — matches Streamlit dark theme


def _resolve_path_case_insensitive(path: str) -> str | None:
    """Return the real path to a file using case-insensitive filename matching.

    On Linux (Streamlit Cloud) filenames are case-sensitive. This function
    scans the parent directory and returns the path whose filename matches
    case-insensitively, so a mismatch between committed casing and expected
    casing does not cause a silent failure.

    Returns None if no matching file is found.
    """
    target = os.path.basename(path)
    parent = os.path.dirname(path)
    try:
        entries = os.listdir(parent)
    except OSError:
        return None

    target_lower = target.lower()
    for entry in entries:
        if entry.lower() == target_lower:
            return os.path.join(parent, entry)

    return None


def _dark_fallback() -> np.ndarray:
    """Return a plain dark 1024x1024 RGBA array used when a minimap is missing."""
    arr = np.full((TARGET_SIZE[1], TARGET_SIZE[0], 4), _FALLBACK_COLOR, dtype=np.uint8)
    return arr


@st.cache_data(show_spinner=False, version=2)
def load_minimap(path: str) -> np.ndarray:
    """Load a minimap image, resize to 1024x1024, and return as RGBA uint8 array.

    Uses case-insensitive path resolution so the same code works on both
    Windows (case-insensitive FS) and Linux (Streamlit Cloud, case-sensitive FS).

    Falls back to a plain dark background if the file cannot be found or
    opened for any reason — markers and heatmaps still render correctly.

    Cached: the resize runs once on first call; subsequent calls return the
    cached array immediately without touching disk.

    Args:
        path: Absolute or relative path to the minimap image file.

    Returns:
        numpy array of shape (1024, 1024, 4) with dtype uint8.
        Returns a dark fallback array instead of raising if the file is missing.
    """
    # TEMP DEBUG — remove after fix confirmed
    import sys
    print(f"load_minimap called with: {path}", file=sys.stderr)
    print(f"file exists: {os.path.isfile(path)}", file=sys.stderr)

    # Step 1 — try the path as given
    resolved = path if os.path.isfile(path) else _resolve_path_case_insensitive(path)

    if resolved is None:
        # Log which file could not be found to help diagnose on Streamlit Cloud
        st.warning(
            f"Minimap not found: {os.path.basename(path)} — "
            "displaying dark background. Check file casing in Player_data/minimaps/."
        )
        return _dark_fallback()

    try:
        img = Image.open(resolved).convert("RGBA")
        if img.size != TARGET_SIZE:
            img = img.resize(TARGET_SIZE, Image.LANCZOS)
        return np.array(img)
    except Exception as exc:
        st.warning(
            f"Could not load minimap {os.path.basename(resolved)}: {exc} — "
            "displaying dark background."
        )
        return _dark_fallback()
