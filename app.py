"""
app.py
------
LILA BLACK — Player Journey Visualization Tool
Streamlit entry point. All UI lives here; business logic lives in the utility modules.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from coordinate_utils import MAP_CONFIG, add_pixel_coords
from data_loader import DATE_FOLDERS, get_match_options, load_all_data
from heatmap_utils import get_death_heatmap, get_kill_heatmap, get_traffic_heatmap
from image_utils import load_minimap

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_ROOT = Path(__file__).parent / "Player_data"
MINIMAP_DIR = DATA_ROOT / "minimaps"

MINIMAP_FILES: dict[str, str] = {
    "AmbroseValley": str(MINIMAP_DIR / "AmbroseValley_Minimap.png"),
    "GrandRift":     str(MINIMAP_DIR / "GrandRift_Minimap.png"),
    "Lockdown":      str(MINIMAP_DIR / "Lockdown_Minimap.jpg"),
}

# Visual encoding for each event type (FR-3.2)
EVENT_STYLE: dict[str, dict] = {
    "Position":       {"color": "#4A90D9", "symbol": "circle",         "size": 4,  "label": "Position (human)"},
    "BotPosition":    {"color": "#9E9E9E", "symbol": "circle",         "size": 3,  "label": "Bot Position"},
    "Kill":           {"color": "#E53935", "symbol": "x",              "size": 10, "label": "Kill"},
    "Killed":         {"color": "#FF7043", "symbol": "triangle-down",  "size": 9,  "label": "Killed"},
    "BotKill":        {"color": "#B71C1C", "symbol": "x-open",         "size": 9,  "label": "Bot Kill"},
    "BotKilled":      {"color": "#EF9A9A", "symbol": "triangle-down-open", "size": 8, "label": "Bot Killed"},
    "KilledByStorm":  {"color": "#9C27B0", "symbol": "diamond",        "size": 10, "label": "Killed by Storm"},
    "Loot":           {"color": "#FFD600", "symbol": "star",           "size": 9,  "label": "Loot"},
}

ALL_EVENTS = list(EVENT_STYLE.keys())
IMAGE_SIZE = 1024

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="LILA BLACK — Player Journey Viz",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load data (cached)
# ---------------------------------------------------------------------------

df_all = load_all_data(str(DATA_ROOT))

# ---------------------------------------------------------------------------
# Sidebar — Filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🎮 LILA BLACK")
    st.caption("Player Journey Visualization")
    st.divider()

    # --- Map filter ---
    map_options = list(MAP_CONFIG.keys())
    selected_map = st.selectbox("Map", map_options, index=0)

    # --- Date filter ---
    date_labels = ["All dates"] + list(DATE_FOLDERS.values())
    selected_dates = st.multiselect(
        "Date",
        options=list(DATE_FOLDERS.values()),
        default=list(DATE_FOLDERS.values()),
        placeholder="Select dates…",
    )
    if not selected_dates:
        selected_dates = list(DATE_FOLDERS.values())

    # --- Player type filter ---
    player_type = st.radio(
        "Player type",
        ["Humans + Bots", "Humans only", "Bots only"],
        index=0,
        horizontal=True,
    )

    st.divider()

    # --- Match filter ---
    df_map_date = df_all[
        (df_all["map_id"] == selected_map) & (df_all["date"].isin(selected_dates))
    ]
    if player_type == "Humans only":
        df_map_date = df_map_date[~df_map_date["is_bot"]]
    elif player_type == "Bots only":
        df_map_date = df_map_date[df_map_date["is_bot"]]

    match_options_map = get_match_options(df_map_date)
    match_display_labels = ["All matches"] + list(match_options_map.keys())
    selected_match_label = st.selectbox("Match", match_display_labels, index=0)
    selected_match_id = (
        match_options_map[selected_match_label]
        if selected_match_label != "All matches"
        else None
    )

    st.divider()

    # --- Event type filter ---
    st.markdown("**Event types**")
    selected_events: list[str] = []
    cols = st.columns(2)
    for i, event in enumerate(ALL_EVENTS):
        style = EVENT_STYLE[event]
        checked = cols[i % 2].checkbox(
            style["label"],
            value=True,
            key=f"evt_{event}",
        )
        if checked:
            selected_events.append(event)

    st.divider()

    # --- Heatmap mode ---
    st.markdown("**Heatmap overlay**")
    heatmap_mode = st.radio(
        "Type",
        ["Off", "Traffic", "Kill", "Death"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
    )
    heatmap_opacity = 0.6
    if heatmap_mode != "Off":
        heatmap_opacity = st.slider("Opacity", 0.2, 0.9, 0.6, 0.05)

    st.divider()

    # --- Specific player filter (only when a match is selected) ---
    selected_player_id: str | None = None
    if selected_match_id:
        match_df = df_map_date[df_map_date["match_id"] == selected_match_id]
        human_players = sorted(
            match_df[~match_df["is_bot"]]["user_id"].astype(str).unique().tolist()
        )
        player_options = ["All players"] + [p[:8] + "…" for p in human_players]
        player_id_map = {p[:8] + "…": p for p in human_players}

        selected_player_label = st.selectbox(
            "Follow player",
            player_options,
            index=0,
        )
        if selected_player_label != "All players":
            selected_player_id = player_id_map.get(selected_player_label)

    # --- Reset button ---
    if st.button("↺ Reset filters", width='stretch'):
        st.rerun()

    st.divider()

    # --- Legend ---
    st.markdown("**Legend**")
    for event, style in EVENT_STYLE.items():
        color = style["color"]
        label = style["label"]
        st.markdown(
            f'<span style="color:{color}; font-size:16px;">●</span> {label}',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Filter dataframe
# ---------------------------------------------------------------------------

df_filtered = df_map_date.copy()
if selected_match_id:
    df_filtered = df_filtered[df_filtered["match_id"] == selected_match_id]
if selected_events:
    df_filtered = df_filtered[df_filtered["event"].isin(selected_events)]

# Add pixel coordinates
df_filtered = add_pixel_coords(df_filtered)

# ---------------------------------------------------------------------------
# Build Plotly figure
# ---------------------------------------------------------------------------

@st.cache_data(max_entries=10, show_spinner=False)
def build_figure(
    df: pd.DataFrame,
    selected_map: str,
    heatmap_mode: str,
    heatmap_opacity: float,
    selected_events: tuple,
    selected_player_id: str | None,
) -> go.Figure:
    """Build the Plotly map figure.

    All state that affects the output is an explicit parameter so that
    st.cache_data keys correctly on every dependency. Identical calls
    (same filtered df + same UI state) return the cached figure instantly.
    """
    fig = go.Figure()

    # --- Base layer: minimap image (pre-resized to 1024x1024, cached) ---
    try:
        img_array = load_minimap(MINIMAP_FILES[selected_map])
        fig.add_trace(go.Image(z=img_array, name="minimap"))
    except Exception:
        st.warning(f"Could not load minimap for {selected_map}.")

    # --- Heatmap overlay ---
    if heatmap_mode != "Off" and not df.empty:
        if heatmap_mode == "Kill":
            grid = get_kill_heatmap(df)
        elif heatmap_mode == "Death":
            grid = get_death_heatmap(df)
        else:
            grid = get_traffic_heatmap(df)

        if grid.max() > 0:
            # Mask zero cells so they show as transparent
            grid_masked = np.where(grid == 0, np.nan, grid)
            fig.add_trace(
                go.Heatmap(
                    z=grid_masked,
                    x=np.linspace(0, IMAGE_SIZE, grid.shape[1]),
                    y=np.linspace(0, IMAGE_SIZE, grid.shape[0]),
                    colorscale="Hot",
                    opacity=heatmap_opacity,
                    showscale=False,
                    hoverinfo="skip",
                    name=f"{heatmap_mode} heatmap",
                )
            )

    # --- Player journey trace (when a specific player is selected) ---
    if selected_player_id and not df.empty:
        journey = (
            df[df["user_id"].astype(str) == selected_player_id]
            .sort_values("ts")
        )
        if not journey.empty:
            # Movement path line
            move = journey[journey["event"].isin({"Position", "BotPosition"})]
            if not move.empty:
                fig.add_trace(
                    go.Scatter(
                        x=move["px_x"],
                        y=move["px_y"],
                        mode="lines",
                        line=dict(color="#4A90D9", width=2),
                        opacity=0.7,
                        name="Movement path",
                        hoverinfo="skip",
                    )
                )

            # Start marker (green circle)
            start = journey.iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[start["px_x"]],
                    y=[start["px_y"]],
                    mode="markers",
                    marker=dict(color="#00E676", size=14, symbol="circle",
                                line=dict(color="white", width=2)),
                    name="Journey start",
                    hovertemplate="Start<extra></extra>",
                )
            )

            # End marker (red X)
            end = journey.iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=[end["px_x"]],
                    y=[end["px_y"]],
                    mode="markers",
                    marker=dict(color="#FF1744", size=14, symbol="x",
                                line=dict(color="white", width=2)),
                    name="Journey end",
                    hovertemplate="End<extra></extra>",
                )
            )

            # Key events along path (kills, loots, deaths)
            key_events = journey[journey["event"].isin(
                {"Kill", "BotKill", "Killed", "BotKilled", "KilledByStorm", "Loot"}
            )]
            if not key_events.empty:
                for _, row in key_events.iterrows():
                    style = EVENT_STYLE.get(row["event"], {})
                    fig.add_trace(
                        go.Scatter(
                            x=[row["px_x"]],
                            y=[row["px_y"]],
                            mode="markers",
                            marker=dict(
                                color=style.get("color", "white"),
                                size=style.get("size", 8) + 2,
                                symbol=style.get("symbol", "circle"),
                                line=dict(color="white", width=1),
                            ),
                            name=style.get("label", row["event"]),
                            hovertemplate=f"{row['event']}<extra></extra>",
                            showlegend=False,
                        )
                    )

    # --- Event markers (scatter layer) ---
    if not df.empty and heatmap_mode == "Off":
        for event_type in selected_events:
            subset = df[df["event"] == event_type]
            if subset.empty:
                continue
            style = EVENT_STYLE[event_type]
            fig.add_trace(
                go.Scatter(
                    x=subset["px_x"],
                    y=subset["px_y"],
                    mode="markers",
                    marker=dict(
                        color=style["color"],
                        size=style["size"],
                        symbol=style["symbol"],
                        opacity=0.7,
                        line=dict(color="rgba(0,0,0,0.3)", width=0.5),
                    ),
                    name=style["label"],
                    hovertemplate=(
                        f"<b>{style['label']}</b><br>"
                        "x: %{customdata[0]:.1f}<br>"
                        "z: %{customdata[1]:.1f}<br>"
                        "<extra></extra>"
                    ),
                    customdata=subset[["x", "z"]].values,
                )
            )

    # --- Layout ---
    fig.update_layout(
        xaxis=dict(
            range=[0, IMAGE_SIZE],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="y",
        ),
        yaxis=dict(
            range=[IMAGE_SIZE, 0],  # flip y so image top = data top
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="black",
        plot_bgcolor="black",
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)",
            font=dict(color="white", size=11),
            x=1.01,
            y=1,
            xanchor="left",
        ),
        height=700,
        dragmode="pan",
    )

    return fig


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

# Stats row
total_events = len(df_filtered)
unique_players = df_filtered[~df_filtered["is_bot"]]["user_id"].nunique()
unique_matches = df_filtered["match_id"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Map", selected_map)
c2.metric("Events shown", f"{total_events:,}")
c3.metric("Human players", unique_players)
c4.metric("Matches", unique_matches)

# ---------------------------------------------------------------------------
# Timeline — rendered ABOVE the map so the slider is interactive immediately
# (Streamlit renders top-to-bottom; placing the slider before the heavy figure
# means it becomes live before the Plotly chart finishes rendering.)
# ---------------------------------------------------------------------------

timeline_cutoff: int | None = None

if selected_match_id:
    match_ts = df_filtered["ts"].dropna()
    if not match_ts.empty:
        ts_min = int(match_ts.min())
        ts_max = int(match_ts.max())
        # Guard against single-event matches with no duration
        if ts_max <= ts_min:
            ts_max = ts_min + 1

        duration_s = ts_max - ts_min

        # Apply any pending play-advance BEFORE the slider is instantiated.
        # Streamlit raises StreamlitAPIException if you write to a widget's
        # session_state key after it has been rendered in the same run.
        # Fix: store the next value under "timeline_next", then move it into
        # "timeline_slider" here — before the widget exists this run.
        if "timeline_next" in st.session_state:
            st.session_state["timeline_slider"] = st.session_state.pop("timeline_next")

        st.markdown("### Match Timeline")
        # st.container() gives the slider its own DOM node, separating it from
        # the Plotly canvas below so scroll events on the slider are not
        # captured by Plotly's scroll-zoom handler.
        with st.container():
            tl_col, play_col = st.columns([6, 1])

            with tl_col:
                # Slider range is 0..duration_s (relative seconds from match
                # start) so tick labels show small numbers, not raw timestamps.
                # ts is in seconds; ts_min + timeline_val = absolute cutoff.
                timeline_val = st.slider(
                    "Elapsed time",
                    min_value=0,
                    max_value=duration_s,
                    value=0,
                    step=30,
                    label_visibility="collapsed",
                    key="timeline_slider",
                )
                elapsed_s = timeline_val  # already seconds from match start
                st.caption(f"⏱ {elapsed_s // 60}m {elapsed_s % 60:02d}s into match")

            with play_col:
                if "playing" not in st.session_state:
                    st.session_state["playing"] = False
                play_label = "⏸" if st.session_state["playing"] else "▶"
                if st.button(play_label, width='stretch'):
                    st.session_state["playing"] = not st.session_state["playing"]

        # Auto-advance when playing.
        # Write to "timeline_next" (not "timeline_slider") — never touch a
        # widget key after it has been instantiated in the current run.
        if st.session_state.get("playing"):
            new_val = timeline_val + 30   # advance 30 seconds per tick
            if new_val >= duration_s:
                st.session_state["playing"] = False
            else:
                time.sleep(0.15)
                st.session_state["timeline_next"] = new_val
                st.rerun()

        # Show only events up to the current slider position.
        # Far left (0s): first moment only. Far right (duration_s): full match.
        df_filtered = df_filtered[df_filtered["ts"] <= ts_min + timeline_val]

# Map viewport — rendered after the slider so frontend thread is not blocked
fig = build_figure(
    df_filtered,
    selected_map,
    heatmap_mode,
    heatmap_opacity,
    tuple(selected_events),   # list → tuple so st.cache_data can hash it
    selected_player_id,
)
st.plotly_chart(
    fig,
    width='stretch',
    config={
        "staticPlot": False,
        "scrollZoom": True,
        "displayModeBar": True,
        "modeBarButtonsToKeep": ["zoom2d", "pan2d", "resetScale2d"],
    },
)

# Footer
st.caption(
    "Data: LILA BLACK production telemetry, Feb 10–14 2026 · "
    "Built with Streamlit + Plotly · "
    f"Showing {total_events:,} of {len(df_all):,} total events"
)
