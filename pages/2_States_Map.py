import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.header("States Map")

# ---- Guard: ensure data exists ----
if "df" not in st.session_state or st.session_state["df"] is None or len(st.session_state["df"]) == 0:
    st.warning("No data yet. Go to **Home (app.py)** and upload your CSV files first. "
               "Once the data loads, come back to this page.")
    st.stop()

df = st.session_state["df"]

# Ensure we have a 'state' column (handle alternative casings)
if "state" not in df.columns:
    for alt in ["State", "STATE", "negeri", "Negeri"]:
        if alt in df.columns:
            df = df.rename(columns={alt: "state"})
            break

# ---- Get quarters safely (fallback to compute from df) ----
quarters = st.session_state.get("quarters")
if not quarters:
    # compute from df if missing
    if "quarter" in df.columns:
        qlist = pd.PeriodIndex(df["quarter"].astype(str)).astype(str).tolist()
        quarters = sorted(set(qlist), key=lambda x: (int(x[:4]), int(x[-1])))
        st.session_state["quarters"] = quarters
    else:
        st.error("Couldn't find a 'quarter' column. Please check the upload/merge step on the Home page.")
        st.stop()

if len(quarters) == 0:
    st.warning("No quarters detected. Please ensure the CSVs have date/quarter fields and re-upload on the Home page.")
    st.stop()

# ---- UI controls ----
metric = st.selectbox("Metric", ["YMI", "youth_unemp_rate", "u_rate", "cpi_index"])
default_idx = max(0, len(quarters) - 1)
q = st.selectbox("Quarter", quarters, index=default_idx)

d = df[df["quarter"].astype(str) == q].copy()

# If no rows for this quarter, inform user
if d.empty:
    st.info(f"No rows found for {q}. Try a different quarter or re-check your CSV coverage.")
    st.stop()

st.info("If you place a Malaysia states GeoJSON at `assets/malaysia_states.geojson`, a choropleth will render. "
        "Otherwise, a fallback bar chart is shown.")

# ---- Try choropleth, else fallback ----
try:
    with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)

    # Ensure the 'state' column exists for locations
    if "state" not in d.columns:
        st.warning("No 'state' column in the filtered data; showing bar chart instead.")
        d = d.sort_values(metric, ascending=False)
        st.bar_chart(d.set_index(d.columns[0])[metric])
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
    # pick a reasonable index if 'state' missing
    index_col = "state" if "state" in d.columns else d.columns[0]
    if metric not in d.columns:
        st.error(f"Metric '{metric}' not found in data columns {list(d.columns)}. "
                 "Check earlier pages / the merge step.")
        st.stop()
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
