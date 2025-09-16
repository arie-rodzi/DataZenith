import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.title("Malaysia States Choropleth")

# 1) Load GeoJSON (from assets or upload)
gj = None
try:
    with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)
except Exception:
    pass

upload_gj = st.file_uploader("Upload Malaysia states GeoJSON (optional)", type=["geojson","json"], key="gj_upload")
if upload_gj is not None:
    gj = json.load(upload_gj)

if not gj:
    st.warning("No GeoJSON found. Showing fallback bar chart.")
    # Fallback demo data
    df = pd.DataFrame({"state": ["Johor","Kedah"], "value": [10,20]})
    st.bar_chart(df.set_index("state"))
    st.stop()

# 2) Detect a suitable feature id key
props = list(gj["features"][0]["properties"].keys())
st.caption(f"GeoJSON property keys detected: {props}")

# Prefer shapeName if present
if "shapeName" in props:
    feature_id_key = "properties.shapeName"
    name_key = "shapeName"
elif "name" in props:
    feature_id_key = "properties.name"
    name_key = "name"
elif "NAME_1" in props:
    feature_id_key = "properties.NAME_1"
    name_key = "NAME_1"
else:
    st.error("Couldn't find a suitable feature id key (e.g., shapeName/name/NAME_1).")
    st.stop()

# 3) Extract canonical names from GeoJSON
gj_names = sorted({feat["properties"][name_key] for feat in gj["features"]})
st.write("GeoJSON state names:", gj_names)

# 4) Your data — replace with your real dataframe
#    Must have a column 'state' and a numeric column to visualize, e.g. 'value'
df = pd.DataFrame({
    "state": ["Johor","Kedah","Kelantan","Melaka","Negeri Sembilan","Pahang","Perak","Perlis",
              "Pulau Pinang","Sabah","Sarawak","Selangor","Terengganu","W.P. Kuala Lumpur",
              "W.P. Labuan","W.P. Putrajaya"],
    "value": [5,3,4,6,5,7,8,2,5,6,7,9,4,10,1,2]
})

# 5) Normalize your state labels to match the GeoJSON labels
#    Adjust the right-hand side to EXACTLY what your GeoJSON uses
normalize = {
    # Common variants — edit RHS to match your gj_names exactly
    "Pulau Pinang": "Pulau Pinang",   # or "Penang" if your GeoJSON uses that
    "Melaka": "Melaka",               # or "Malacca"
    "W.P. Kuala Lumpur": "Wilayah Persekutuan Kuala Lumpur",
    "W.P. Labuan": "Wilayah Persekutuan Labuan",
    "W.P. Putrajaya": "Wilayah Persekutuan Putrajaya",
    # If your GeoJSON already uses simple names ("Johor", etc.), leave them as-is:
    "Johor": "Johor",
    "Kedah": "Kedah",
    "Kelantan": "Kelantan",
    "Negeri Sembilan": "Negeri Sembilan",
    "Pahang": "Pahang",
    "Perak": "Perak",
    "Perlis": "Perlis",
    "Sabah": "Sabah",
    "Sarawak": "Sarawak",
    "Selangor": "Selangor",
    "Terengganu": "Terengganu",
}

df["state_norm"] = df["state"].map(normalize).fillna(df["state"])

# 6) Report any names still not matching the GeoJSON names
unmatched = sorted(set(df["state_norm"]) - set(gj_names))
if unmatched:
    st.warning(f"Some states didn’t match GeoJSON names and may not render: {unmatched}")

# 7) Plot
fig = px.choropleth(
    df,
    geojson=gj,
    locations="state_norm",
    featureidkey=feature_id_key,  # <-- critical line
    color="value",
    projection="mercator"
)
fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, use_container_width=True)
