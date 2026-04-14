"""
app.py
------
LILA BLACK — Player Journey Visualization Tool
Streamlit entry point. All UI lives here; business logic lives in the utility modules.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import os
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = Path(BASE_DIR) / "Player_data"

MINIMAP_FILES: dict[str, str] = {
    "AmbroseValley": "AmbroseValley",
    "GrandRift":     "GrandRift",
    "Lockdown":      "Lockdown",
}

# Visual encoding for each event type (FR-3.2)
# opacity key: per-event override; absent = use the sidebar marker_opacity slider.
# BotPosition uses white so it needs a fixed lower opacity to stay distinguishable.
EVENT_STYLE: dict[str, dict] = {
    # Color = WHAT happened. Shape = WHO was involved.
    "Position":      {"color": "#00BFFF", "symbol": "circle",        "size": 6,  "label": "Position (Human)", "tooltip": "Human player position"},
    "BotPosition":   {"color": "#888888", "symbol": "circle",        "size": 5,  "label": "Bot Position",     "tooltip": "Bot position"},
    "Kill":          {"color": "#FF0000", "symbol": "circle",        "size": 14, "label": "Kill",             "tooltip": "Human eliminated another human"},
    "Killed":        {"color": "#FF6600", "symbol": "triangle-down", "size": 15, "label": "Killed",           "tooltip": "Human was eliminated by another human"},
    "BotKill":       {"color": "#CC0000", "symbol": "triangle-up",   "size": 13, "label": "Bot Kill",         "tooltip": "Human eliminated a bot"},
    "BotKilled":     {"color": "#FF9999", "symbol": "square",        "size": 11, "label": "Bot Killed",       "tooltip": "Human was eliminated by a bot"},
    "KilledByStorm": {"color": "#CC00FF", "symbol": "triangle-up",   "size": 16, "label": "Killed by Storm",  "tooltip": "Player died to the storm"},
    "Loot":          {"color": "#FFE000", "symbol": "circle",        "size": 12, "label": "Loot",             "tooltip": "Player picked up an item"},
}

ALL_EVENTS = list(EVENT_STYLE.keys())

# Human-readable names shown in the Plotly figure legend (bottom-right corner)
_TRACE_NAMES: dict[str, str] = {
    "Kill":          "Kill — Human eliminated human",
    "Killed":        "Killed — Eliminated by human",
    "BotKill":       "Bot Kill — Human eliminated bot",
    "BotKilled":     "Bot Killed — Eliminated by bot",
    "KilledByStorm": "Killed by Storm — Died to storm",
    "Loot":          "Loot — Item picked up",
    "Position":      "Position (Human) — Player was here",
    "BotPosition":   "Bot Position — Bot was here",
}
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

data = load_all_data(str(DATA_ROOT))

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
    # Start from the pre-filtered per-map DataFrame (~3× fewer rows than full dataset).
    df_map = data[selected_map]
    _all_dates = set(DATE_FOLDERS.values())
    df_map_date = (
        df_map
        if set(selected_dates) == _all_dates
        else df_map[df_map["date"].isin(selected_dates)]
    )
    if player_type == "Humans only":
        df_map_date = df_map_date[~df_map_date["is_bot"]]
    elif player_type == "Bots only":
        df_map_date = df_map_date[df_map_date["is_bot"]]

    # Use pre-computed match options for the default case (all dates, all players).
    # Recompute only when the date or player filter is narrowed — starting from the
    # already-small per-map DataFrame, so groupby cost is ~3× lower than before.
    if set(selected_dates) == _all_dates and player_type == "Humans + Bots":
        match_options_map = data["match_options"][selected_map]
    else:
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

    marker_opacity = st.slider("Marker opacity", 0.3, 1.0, 0.9, 0.05)

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
    heatmap_opacity = 0.65
    if heatmap_mode != "Off":
        heatmap_opacity = st.slider("Opacity", 0.2, 0.9, 0.65, 0.05)
        _captions = {
            "Traffic": "Black = no players. Red = high player concentration.",
            "Kill":    "Black = no kills. Red = kill hotspot.",
            "Death":   "Black = no deaths. Red = high death zone.",
        }
        st.caption(_captions[heatmap_mode])

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
    st.sidebar.markdown("### Map Legend")
    st.sidebar.markdown("**What happened**")
    st.sidebar.markdown('<span style="color:#FF0000">●</span> **Kill** — Human eliminated another human', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#FF6600">▽</span> **Killed** — Human was eliminated by another human', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#CC0000">△</span> **Bot Kill** — Human eliminated a bot', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#FF9999">■</span> **Bot Killed** — Human was killed by a bot', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#CC00FF">△</span> **Killed by Storm** — Player died to the storm', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#FFE000">●</span> **Loot** — Item picked up here', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#00BFFF">●</span> **Position (Human)** — Human player was here', unsafe_allow_html=True)
    st.sidebar.markdown('<span style="color:#888888">●</span> **Bot Position** — Bot was here', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown("🎨 **Color** → Red: Combat | Purple: Storm | Gold: Loot")
    st.sidebar.markdown("🔷 **Shape** → Circle: Human | Triangle: Bot involved | Square: Killed by bot")

# ---------------------------------------------------------------------------
# Filter dataframe
# ---------------------------------------------------------------------------

_t0 = time.perf_counter()

df_filtered = df_map_date.copy()
if selected_match_id:
    df_filtered = df_filtered[df_filtered["match_id"] == selected_match_id]
if selected_events:
    df_filtered = df_filtered[df_filtered["event"].isin(selected_events)]

# Add pixel coordinates
df_filtered = add_pixel_coords(df_filtered)

_t_filter_ms = (time.perf_counter() - _t0) * 1000

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
    marker_opacity: float = 0.9,
) -> go.Figure:
    """Build the Plotly map figure.

    All state that affects the output is an explicit parameter so that
    st.cache_data keys correctly on every dependency. Identical calls
    (same filtered df + same UI state) return the cached figure instantly.
    """
    fig = go.Figure()

    # --- Base layer: minimap image (pre-resized to 1024x1024, cached) ---
    # load_minimap never raises — returns a dark fallback array if the file
    # is missing or unreadable, so markers and heatmaps still display correctly.
    img_array = load_minimap(MINIMAP_FILES[selected_map])
    fig.add_trace(go.Image(z=img_array, name="minimap"))

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
                    showscale=True,
                    colorbar=dict(
                        title="Player density",
                        thickness=15,
                        len=0.5,
                        x=1.02,
                    ),
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
                    go.Scattergl(
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
                go.Scattergl(
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
                go.Scattergl(
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
                        go.Scattergl(
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
    # ts_base: used to compute human-readable elapsed time per marker.
    # Falls back to 0 if df is empty or ts is all-NaN.
    ts_base = int(df["ts"].min()) if not df.empty and df["ts"].notna().any() else 0

    if not df.empty and heatmap_mode == "Off":
        for event_type in selected_events:
            subset = df[df["event"] == event_type]
            if subset.empty:
                continue
            style = EVENT_STYLE[event_type]
            opacity = style.get("opacity", marker_opacity)

            # Pre-format elapsed time as "Xm XXs into match" for hover tooltip
            elapsed_s = (subset["ts"] - ts_base).clip(lower=0).fillna(0).astype(int)
            elapsed_str = elapsed_s.apply(lambda s: f"{s // 60}m {s % 60:02d}s into match")

            # Non-circle markers (triangles, squares) produce white particle/dust
            # artifacts in Scattergl when rendered with partial opacity or a visible
            # outline. Fix: force opacity=1.0 and zero-width transparent outline.
            # Circle markers are unaffected — keep their white outline.
            is_circle = style["symbol"] == "circle"
            marker_line = (
                dict(color="white", width=1.5)
                if is_circle
                else dict(width=0, color="rgba(0,0,0,0)")
            )
            marker_fill_opacity = opacity if is_circle else 1.0

            fig.add_trace(
                go.Scattergl(
                    x=subset["px_x"],
                    y=subset["px_y"],
                    mode="markers",
                    marker=dict(
                        color=style["color"],
                        size=style["size"],
                        symbol=style["symbol"],
                        opacity=marker_fill_opacity,
                        line=marker_line,
                    ),
                    name=_TRACE_NAMES.get(event_type, style["label"]),
                    hovertemplate=(
                        f"<b>{style['label']}</b><br>"
                        f"{style['tooltip']}<br>"
                        "%{customdata[0]}"
                        "<extra></extra>"
                    ),
                    customdata=elapsed_str.astype(str).to_numpy().reshape(-1, 1),
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
        showlegend=True,
        legend=dict(
            x=1.0,
            y=0.0,
            xanchor="right",
            yanchor="bottom",
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
            font=dict(color="white", size=11),
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
_t1 = time.perf_counter()
fig = build_figure(
    df_filtered,
    selected_map,
    heatmap_mode,
    heatmap_opacity,
    tuple(selected_events),   # list → tuple so st.cache_data can hash it
    selected_player_id,
    marker_opacity,
)
_t_figure_ms = (time.perf_counter() - _t1) * 1000

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
    f"Showing {total_events:,} of {len(data['all']):,} total events · "
    f"Filter: {_t_filter_ms:.0f}ms · Figure: {_t_figure_ms:.0f}ms"
)
