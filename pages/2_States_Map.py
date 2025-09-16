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

# ---- Choropleth with diagnostics (or fallback bar chart) ----
st.info("If you place a Malaysia states GeoJSON at `assets/malaysia_states.geojson`, a choropleth will render. "
        "Otherwise, upload it below or a fallback bar chart is shown.")

# Allow manual GeoJSON upload (works on Streamlit Cloud)
geojson_file_obj = st.file_uploader("Upload Malaysia states GeoJSON (optional)", type=["geojson","json"], key="gj_upload")

geojson_data = None
if geojson_file_obj is not None:
    try:
        geojson_data = json.load(geojson_file_obj)
    except Exception as e:
        st.warning(f"Uploaded GeoJSON invalid: {e}")

if geojson_data is None:
    try:
        with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
    except Exception as e:
        st.warning(f"GeoJSON not found/invalid at assets/malaysia_states.geojson ({e}). Showing bar chart fallback.")

if geojson_data is not None and "features" in geojson_data:
    # Inspect available property keys
    prop_keys = sorted({k for feat in geojson_data["features"] for k in feat.get("properties", {}).keys()})
    st.caption(f"GeoJSON property keys detected: {prop_keys}")

    # Try common feature id keys
    candidate_keys = ["properties.name", "properties.NAME_1", "properties.state", "properties.negeri"]
    used_key = None
    for k in candidate_keys:
        prop = k.split(".", 1)[1]  # e.g. 'name'
        if prop in geojson_data["features"][0].get("properties", {}):
            used_key = k
            break

    # Optional: harmonize state names to match GeoJSON if needed
    name_fix = {
        "Pulau Pinang": "Penang",          # adjust if your GeoJSON uses Penang
        "W.P. Kuala Lumpur": "Kuala Lumpur",
        "W.P. Labuan": "Labuan",
        "W.P. Putrajaya": "Putrajaya",
    }
    if "state" in d.columns:
        d["state"] = d["state"].replace(name_fix)

    if used_key is None:
        st.warning("Couldn't find a suitable feature id key (tried name/NAME_1/state/negeri). "
                   "Showing bar chart instead.")
        index_col = "state" if "state" in d.columns else d.columns[0]
        d = d.sort_values(metric, ascending=False)
        st.bar_chart(d.set_index(index_col)[metric])
    else:
        try:
            fig = px.choropleth(
                d,
                geojson=geojson_data,
                featureidkey=used_key,
                locations="state",
                color=metric,
                color_continuous_scale="Viridis",
                projection="mercator",
            )
            fig.update_geos(fitbounds="locations", visible=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Choropleth failed ({e}). Showing bar chart instead.")
            index_col = "state" if "state" in d.columns else d.columns[0]
            d = d.sort_values(metric, ascending=False)
            st.bar_chart(d.set_index(index_col)[metric])
else:
    # Fallback bar chart
    index_col = "state" if "state" in d.columns else d.columns[0]
    if metric not in d.columns:
        st.error(f"Metric '{metric}' not found in data columns {list(d.columns)}. "
                 "Check earlier pages / the merge step.")
        st.stop()
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
