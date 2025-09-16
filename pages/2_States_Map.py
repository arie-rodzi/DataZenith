import streamlit as st
import pandas as pd
import json
import plotly.express as px
import re
from datetime import datetime

st.header("States Map")

# ---- Guard: ensure data exists ----
df = st.session_state.get("df")
if df is None or len(df) == 0:
    st.warning("No data yet. Go to **Home (app.py)** and upload your CSV files first. "
               "Once the data loads, come back to this page.")
    st.stop()

# Normalize column name for state if needed
if "state" not in df.columns:
    for alt in ["State", "STATE", "negeri", "Negeri"]:
        if alt in df.columns:
            df = df.rename(columns={alt: "state"})
            break

# ---------- Robust quarter sorting ----------
def quarter_sort_key(qstr: str):
    """Return (year, quarter) from many possible formats; fallback big value if unknown."""
    if qstr is None:
        return (9999, 9)
    s = str(qstr).strip()

    # Common formats: 2019Q1 / 2021Q4
    m = re.match(r"^(\d{4})\s*Q([1-4])$", s, flags=re.I)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # Format: Q1 2019 / Q4-2021
    m = re.match(r"^Q([1-4])\D*(\d{4})$", s, flags=re.I)
    if m:
        return (int(m.group(2)), int(m.group(1)))

    # If it looks like a date, convert to quarter
    dt = pd.to_datetime(s, errors="coerce")
    if pd.notna(dt):
        q = ((dt.month - 1) // 3) + 1
        return (dt.year, q)

    # Last resort: try to extract any 4-digit year and a digit 1-4
    m = re.search(r"(\d{4}).*?([1-4])", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    return (9999, 9)

# Build quarters list safely
if "quarter" not in df.columns:
    st.error("Couldn't find a 'quarter' column. Please check the upload/merge step on the Home page.")
    st.stop()

quarter_strings = sorted(
    {str(x) for x in df["quarter"].dropna().astype(str).tolist()},
    key=quarter_sort_key
)

if not quarter_strings:
    st.warning("No quarters detected. Please ensure the CSVs have date/quarter fields and re-upload on the Home page.")
    st.stop()

# ---- UI controls ----
metric = st.selectbox("Metric", ["YMI", "youth_unemp_rate", "u_rate", "cpi_index"])
default_idx = max(0, len(quarter_strings) - 1)
q = st.selectbox("Quarter", quarter_strings, index=default_idx)

# Filter by selected quarter (compare as string)
d = df[df["quarter"].astype(str) == q].copy()
if d.empty:
    st.info(f"No rows found for {q}. Try a different quarter or re-check your CSV coverage.")
    st.stop()

st.info(
    "If you place a Malaysia states GeoJSON at `assets/malaysia_states.geojson`, a choropleth will render. "
    "Otherwise, a fallback bar chart is shown."
)

# ---- Try choropleth, else fallback ----
try:
    with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)

    if "state" not in d.columns:
        st.warning("No 'state' column in the filtered data; showing bar chart instead.")
        idx = d.columns[0]
        d = d.sort_values(metric, ascending=False)
        st.bar_chart(d.set_index(idx)[metric])
    else:
        fig = px.choropleth(
            d,
            geojson=gj,
            featureidkey="properties.name",  # ensure your geojson uses 'name' for state names
            locations="state",
            color=metric,
            color_continuous_scale="Viridis",
            projection="mercator",
        )
        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.warning("GeoJSON not found or invalid. Showing a bar chart instead.")
    index_col = "state" if "state" in d.columns else d.columns[0]
    if metric not in d.columns:
        st.error(
            f"Metric '{metric}' not found in data columns {list(d.columns)}. "
            "Check earlier pages / the merge step."
        )
        st.stop()
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
