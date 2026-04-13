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
"""

from __future__ import annotations

import numpy as np
import streamlit as st
from PIL import Image

TARGET_SIZE = (1024, 1024)


@st.cache_data(show_spinner=False)
def load_minimap(path: str) -> np.ndarray:
    """Load a minimap image, resize to 1024x1024, and return as RGBA uint8 array.

    Cached: the resize runs once on first call; subsequent calls return the
    cached array immediately without touching disk.

    Args:
        path: Absolute or relative path to the minimap image file.

    Returns:
        numpy array of shape (1024, 1024, 4) with dtype uint8.

    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    img = Image.open(path).convert("RGBA")
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.LANCZOS)
    return np.array(img)
