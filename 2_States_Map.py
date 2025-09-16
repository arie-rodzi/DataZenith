
import streamlit as st
import pandas as pd
import json
import plotly.express as px
from utils.llm_helper import compose_bullets

st.header("States Map")

if "df" not in st.session_state:
    st.warning("Upload the merged Excel on the Home page first.")
    st.stop()

df = st.session_state["df"]
quarters = st.session_state["quarters"]

metric = st.selectbox("Metric", ["YMI","youth_unemp_rate","u_rate","cpi_index"])
q = st.selectbox("Quarter", quarters, index=len(quarters)-1 if quarters else 0)

d = df[df["quarter"]==q].copy()

st.info("Place 'malaysia_states.geojson' in assets/ for choropleth. Otherwise, a bar chart is shown.")

try:
    with open("assets/malaysia_states.geojson","r", encoding="utf-8") as f:
        gj = json.load(f)
    fig = px.choropleth(
        d, geojson=gj, featureidkey="properties.name",
        locations="state", color=metric, color_continuous_scale="Viridis",
        projection="mercator"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.warning("GeoJSON not found. Showing a bar chart instead.")
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index("state")[metric])

st.subheader("LLM Explainer for Selected Quarter")
# Aggregate national view to produce bullets
nat = d.agg({
    "YMI":"mean",
    "youth_unemp_rate":"mean",
    "skills_underemp_rate":"mean",
    "time_underemp_rate":"mean",
    "u_rate":"mean",
    "cpi_index":"mean"
}).to_dict()
nat["quarter"] = q
lang = st.radio("Language", ["ms","en"], horizontal=True, key="lang_map")
st.text(compose_bullets(nat, lang))
