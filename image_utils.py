import os
import numpy as np
import streamlit as st
from PIL import Image

TARGET_SIZE = (1024, 1024)

@st.cache_data(show_spinner=False)
def load_minimap(map_name: str) -> np.ndarray:
    possible_paths = [
        f'Player_data/minimaps/{map_name}_Minimap.png',
        f'Player_data/minimaps/{map_name}_Minimap.jpg',
        f'/mount/src/pj_viz/Player_data/minimaps/{map_name}_Minimap.png',
        f'/mount/src/pj_viz/Player_data/minimaps/{map_name}_Minimap.jpg',
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            img = Image.open(path).convert('RGBA')
            img = img.resize(TARGET_SIZE, Image.LANCZOS)
            return np.array(img)
    dark = np.full((1024, 1024, 4), (30, 30, 35, 255), dtype=np.uint8)
    return dark
