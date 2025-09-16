import streamlit as st
import pandas as pd
import json
import plotly.express as px
import re

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
err_message = None
if geojson_file_obj is not None:
    try:
        geojson_data = json.load(geojson_file_obj)
    except Exception as e:
        err_message = f"Uploaded GeoJSON invalid: {e}"

if geojson_data is None:
    try:
        with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
    except Exception as e:
        err_message = f"GeoJSON not found/invalid at assets/malaysia_states.geojson ({e})."

if geojson_data is None or "features" not in geojson_data:
    if err_message:
        st.warning(err_message + " Showing bar chart fallback.")
    index_col = "state" if "state" in d.columns else d.columns[0]
    if metric not in d.columns:
        st.error(f"Metric '{metric}' not found in data columns {list(d.columns)}. "
                 "Check earlier pages / the merge step.")
        st.stop()
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
    st.stop()

# Inspect available property keys on the GeoJSON
prop_keys = sorted({k for feat in geojson_data["features"] for k in feat.get("properties", {}).keys()})
st.caption(f"GeoJSON property keys detected: {prop_keys}")

# Choose a usable property as feature id (auto-detects shapeName too)
candidate_props = ["name", "NAME_1", "state", "negeri", "shapeName"]
used_prop = None
for p in candidate_props:
    if p in prop_keys:
        used_prop = p
        break

if used_prop is None:
    st.warning("Couldn't find a suitable feature id key (tried name/NAME_1/state/negeri/shapeName). "
               "Showing bar chart instead.")
    index_col = "state" if "state" in d.columns else d.columns[0]
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
    st.stop()

featureidkey = f"properties.{used_prop}"

# ------- Harmonize state names to match the GeoJSON values -------
def canonicalize(x: str) -> str:
    s = str(x or "").lower().strip()
    # normalize common variants
    s = s.replace("wilayah persekutuan", "wp")
    s = s.replace("w.p.", "wp").replace("w. p.", "wp")
    s = s.replace("kuala lumpur", "kuala lumpur")
    s = s.replace("putrajaya", "putrajaya")
    s = s.replace("labuan", "labuan")
    s = s.replace("pulau pinang", "penang")  # normalize both to 'penang'
    s = s.replace("penang", "penang")
    s = s.replace(" negeri ", " negeri ")  # keep spacing for other states
    s = re.sub(r"[^a-z0-9 ]+", " ", s)     # remove punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s

# GeoJSON names set
gj_names = [feat["properties"].get(used_prop, "") for feat in geojson_data["features"]]
gj_canon_map = {canonicalize(n): n for n in gj_names if n}

# Map df['state'] -> GeoJSON property names by canonical match + a few manual fixes
if "state" in d.columns:
    # manual “nice” fixes (dataframe -> geojson)
    manual_fix = {
        "Penang": "Pulau Pinang",
        "Kuala Lumpur": "W.P. Kuala Lumpur",
        "Labuan": "W.P. Labuan",
        "Putrajaya": "W.P. Putrajaya",
        "Melaka": "Melaka",  # (same)
        "Negeri Sembilan": "Negeri Sembilan",
    }
    # try canonical map first, then manual override if needed
    mapped_states = []
    for sname in d["state"].astype(str):
        canon = canonicalize(sname)
        target = gj_canon_map.get(canon)
        if target is None and sname in manual_fix:
            target = manual_fix[sname]
        # if still None, keep original value (so mismatches are visible)
        mapped_states.append(target if target is not None else sname)
    d["state_mapped"] = mapped_states
else:
    d["state_mapped"] = d.iloc[:, 0]  # fallback: first column if 'state' missing

# Warn about any unmatched names
unmatched = sorted(set(d["state_mapped"]) - set(gj_names))
if unmatched:
    st.warning(f"Some states didn’t match GeoJSON names and may not render: {unmatched}")

# ---- Draw choropleth ----
try:
    fig = px.choropleth(
        d,
        geojson=geojson_data,
        featureidkey=featureidkey,  # e.g. properties.shapeName
        locations="state_mapped",   # mapped names to match the GeoJSON
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

# Show quick legend of what we matched
with st.expander("See matched names (data → GeoJSON)"):
    if "state" in d.columns:
        show = d[["state", "state_mapped"]].drop_duplicates().sort_values("state")
        st.dataframe(show, use_container_width=True)
    else:
        st.write("No 'state' column found in the data.")
