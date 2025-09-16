import streamlit as st
import pandas as pd
import re

st.header("League & Gaps")

# ---- Guard: ensure data exists ----
df = st.session_state.get("df")
if df is None or len(df) == 0:
    st.warning("No data yet. Go to **Home (app.py)** and upload your CSV files first. "
               "Once the data loads, come back to this page.")
    st.stop()

# Normalize column names if needed
rename_map = {}
# common alternatives for 'state'
for alt in ["State", "STATE", "negeri", "Negeri"]:
    if alt in df.columns:
        rename_map[alt] = "state"
# apply if any
if rename_map:
    df = df.rename(columns=rename_map)

# Robust quarter sorting (no PeriodIndex)
def quarter_sort_key(qstr: str):
    if qstr is None:
        return (9999, 9)
    s = str(qstr).strip()
    m = re.match(r"^(\d{4})\s*Q([1-4])$", s, flags=re.I)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.match(r"^Q([1-4])\D*(\d{4})$", s, flags=re.I)
    if m:
        return (int(m.group(2)), int(m.group(1)))
    dt = pd.to_datetime(s, errors="coerce")
    if pd.notna(dt):
        q = ((dt.month - 1) // 3) + 1
        return (dt.year, q)
    m = re.search(r"(\d{4}).*?([1-4])", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (9999, 9)

# Build quarters list safely
if "quarter" not in df.columns:
    st.error("Couldn't find a 'quarter' column. Please check the upload/merge step on the Home page.")
    st.stop()

quarters = st.session_state.get("quarters")
if not quarters:
    quarter_strings = sorted({str(x) for x in df["quarter"].dropna().astype(str).tolist()},
                             key=quarter_sort_key)
    quarters = quarter_strings
    st.session_state["quarters"] = quarters

if len(quarters) == 0:
    st.warning("No quarters detected. Please ensure the CSVs have date/quarter fields and re-upload on the Home page.")
    st.stop()

# ---- Ensure required metric columns exist ----
required_cols = ["state", "YMI", "youth_unemp_rate", "u_rate", "cpi_index"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing columns for this page: {missing}. "
             "Please verify the upload/merge step on the Home page.")
    st.stop()

# ---- UI / Filtering ----
default_idx = max(0, len(quarters) - 1)
q = st.selectbox("Quarter", quarters, index=default_idx)

d = df[df["quarter"].astype(str) == q].copy()
if d.empty:
    st.info(f"No rows found for {q}. Try another quarter or re-check your CSV coverage.")
    st.stop()

# Gap = youth unemployment minus overall unemployment (pp)
d["youth_gap"] = d["youth_unemp_rate"] - d["u_rate"]

st.subheader("Rankings (Highest YMI first)")
cols = ["state", "YMI", "youth_unemp_rate", "u_rate", "cpi_index"]
st.dataframe(d[cols].sort_values("YMI", ascending=False).reset_index(drop=True),
             use_container_width=True)

st.subheader("Youth vs Overall Unemployment Gap (percentage points)")
gap = d[["state", "youth_gap"]].sort_values("youth_gap", ascending=False).reset_index(drop=True)
st.dataframe(gap, use_container_width=True)

st.caption("Tip: If you expected different numbers, open the Home page and switch ON "
           "‘Trim to common quarter range’ to avoid NaNs from non-overlapping series.")
