import streamlit as st
import pandas as pd
import numpy as np
import re  # regex for flexible column detection

st.set_page_config(page_title="Malaysia Youth Jobs Copilot — CSV Inputs (8 files)", layout="wide")
st.title("🇲🇾 Malaysia Youth Jobs Copilot — CSV Inputs (8 files)")
st.caption(
    "Upload the eight raw CSV files from OpenDOSM. The app cleans, aligns to quarters, and combines core+state context. "
    "If you see many NaNs, enable ‘Trim to common quarter range’ below. "
    "District income (file 8) is annual & kept separate for future geospatial analysis."
)

# ---------------------------
# Uploaders (8 files)
# ---------------------------
st.sidebar.header("Upload 8 CSV files")

# CORE (national):
f1 = st.sidebar.file_uploader("1) Monthly Youth Unemployment (CSV)", type=["csv"], key="f1")
f2 = st.sidebar.file_uploader("2) Quarterly Skills-Related Underemployment by Age (CSV)", type=["csv"], key="f2")
f3 = st.sidebar.file_uploader("3) Quarterly Time-Related Underemployment by Age (CSV)", type=["csv"], key="f3")

# CONTEXT (state, quarterly; and annual):
f4 = st.sidebar.file_uploader("4) Quarterly Labour Force by State (CSV)", type=["csv"], key="f4")
f5 = st.sidebar.file_uploader("5) Annual Productivity by Economic Sector (CSV) [optional annual]", type=["csv"], key="f5")
f6 = st.sidebar.file_uploader("6) Monthly CPI by State & Division (2-digit) (CSV)", type=["csv"], key="f6")
f7 = st.sidebar.file_uploader("7) Household Income by State (CSV) [optional annual]", type=["csv"], key="f7")
f8 = st.sidebar.file_uploader("8) Household Income by Administrative District (CSV) [optional annual, district-level]", type=["csv"], key="f8")

# For the quarterly merged dataset we minimally need 1,2,3,4,6
ready = all([f1, f2, f3, f4, f6])
if not ready:
    st.info("Please upload at least files 1, 2, 3, 4, and 6. Files 5, 7, and 8 are optional (annual / district context).")
    st.stop()

# ---------------------------
# Helpers
# ---------------------------
def to_quarter_from_date(s):
    dt = pd.to_datetime(s, errors="coerce")
    return dt.dt.to_period("Q")

def find_col(df, key):
    """Find a column by exact, lowercase-equal, or loose match (remove underscores)."""
    if key in df.columns:
        return key
    for c in df.columns:
        if c.lower() == key:
            return c
    k = key.replace("_", "")
    for c in df.columns:
        if k in c.lower().replace("_", ""):
            return c
    return None

# ---------------------------
# CORE (national quarterly)
# ---------------------------
# (1) Youth Unemployment (monthly -> quarterly)
yu = pd.read_csv(f1)
date_col = "date" if "date" in yu.columns else yu.columns[0]
yu[date_col] = pd.to_datetime(yu[date_col], errors="coerce")

candidates = [c for c in yu.columns if re.search(r"(15.*30|youth|unemp)", c, flags=re.I)]
if "u_rate_15_30" in yu.columns:
    ycol = "u_rate_15_30"
elif candidates:
    ycol = candidates[0]
else:
    ycol = yu.columns[1]  # fallback
yu = yu[[date_col, ycol]].rename(columns={date_col: "date", ycol: "youth_unemp_rate"})
yu["quarter"] = yu["date"].dt.to_period("Q")
yu_q = yu.groupby("quarter", as_index=False)["youth_unemp_rate"].mean()

# (2) Skills-related Underemployment (quarterly)
su = pd.read_csv(f2)
dcol = "date" if "date" in su.columns else su.columns[0]
su[dcol] = pd.to_datetime(su[dcol], errors="coerce")
su["quarter"] = su[dcol].dt.to_period("Q")
if "sru" in su.columns:
    srate = "sru"
else:
    rate_candidates = [c for c in su.columns if re.search(r"(rate|under)", c, re.I)]
    srate = rate_candidates[0] if rate_candidates else su.columns[-1]
if "age" in su.columns:
    su = su[su["age"].astype(str).str.lower().isin(["overall", "all", "all ages", "semua"])]
su_q = su.groupby("quarter", as_index=False)[srate].mean().rename(columns={srate: "skills_underemp_rate"})

# (3) Time-related Underemployment (quarterly)
tu = pd.read_csv(f3)
dcol3 = "date" if "date" in tu.columns else tu.columns[0]
tu[dcol3] = pd.to_datetime(tu[dcol3], errors="coerce")
tu["quarter"] = tu[dcol3].dt.to_period("Q")
if "tru" in tu.columns:
    trate = "tru"
else:
    rate_candidates = [c for c in tu.columns if re.search(r"(rate|under)", c, re.I)]
    trate = rate_candidates[0] if rate_candidates else tu.columns[-1]
if "age" in tu.columns:
    tu = tu[tu["age"].astype(str).str.lower().isin(["overall", "all", "all ages", "semua"])]
tu_q = tu.groupby("quarter", as_index=False)[trate].mean().rename(columns={trate: "time_underemp_rate"})

# Merge core national quarterly + compute YMI
nat = yu_q.merge(su_q, on="quarter", how="outer").merge(tu_q, on="quarter", how="outer")
nat = nat.sort_values("quarter").reset_index(drop=True)
w = {"youth_unemp_rate": 0.6, "skills_underemp_rate": 0.3, "time_underemp_rate": 0.1}
nat["YMI"] = (
    w["youth_unemp_rate"] * nat["youth_unemp_rate"]
    + w["skills_underemp_rate"] * nat["skills_underemp_rate"]
    + w["time_underemp_rate"] * nat["time_underemp_rate"]
)

# ---------------------------
# CONTEXT (state quarterly)
# ---------------------------
# (4) Labour force by state (quarterly)
lf = pd.read_csv(f4)
lf_date = "date" if "date" in lf.columns else lf.columns[0]
lf[lf_date] = pd.to_datetime(lf[lf_date], errors="coerce")
lf["quarter"] = lf[lf_date].dt.to_period("Q")

pcol = find_col(lf, "p_rate") or find_col(lf, "participation")
ucol = find_col(lf, "u_rate") or find_col(lf, "unemployment")
state_col = find_col(lf, "state") or "state"
if pcol is None or ucol is None or state_col is None:
    st.error("Could not detect labour force columns (need state, p_rate, u_rate). Check file 4.")
    st.stop()

lf_q = lf.rename(columns={pcol: "p_rate", ucol: "u_rate", state_col: "state"})[
    ["state", "quarter", "p_rate", "u_rate"]
]

# (6) CPI monthly -> quarterly average (overall division only)
cpi = pd.read_csv(f6)
cpi_d = "date" if "date" in cpi.columns else cpi.columns[0]
cpi[cpi_d] = pd.to_datetime(cpi[cpi_d], errors="coerce")
cpi["quarter"] = cpi[cpi_d].dt.to_period("Q")

if "division" in cpi.columns:
    overall_aliases = {"overall", "all items", "all-items", "all item", "semua barang", "semua barangan"}
    mask = cpi["division"].astype(str).str.lower().isin(overall_aliases)
    if mask.any():
        cpi = cpi[mask]

if "index" in cpi.columns:
    ival = "index"
else:
    cpi_candidates = [c for c in cpi.columns if re.search(r"(index|cpi)", c, re.I)]
    ival = cpi_candidates[0] if cpi_candidates else cpi.columns[-1]

state_cpi_col = find_col(cpi, "state") or "state"
cpi_q = cpi.groupby([state_cpi_col, "quarter"], as_index=False)[ival].mean().rename(
    columns={state_cpi_col: "state", ival: "cpi_index"}
)

# Merge state context
state_q = lf_q.merge(cpi_q, on=["state", "quarter"], how="outer")

# Spread national core into each state-quarter row
merged = state_q.merge(nat, on="quarter", how="left")

# ---------------------------
# OPTIONAL annual context (kept separate)
# ---------------------------
if f5 is not None:
    try:
        prod = pd.read_csv(f5)
        st.sidebar.caption("✓ Productivity (annual, sector) loaded.")
        st.session_state["productivity_annual"] = prod
    except Exception as e:
        st.sidebar.error(f"Productivity load error: {e}")

if f7 is not None:
    try:
        inc_state = pd.read_csv(f7)
        st.sidebar.caption("✓ Household Income by State (annual) loaded.")
        st.session_state["income_state_annual"] = inc_state
    except Exception as e:
        st.sidebar.error(f"Income-by-state load error: {e}")

if f8 is not None:
    try:
        inc_dist = pd.read_csv(f8)
        # Soft checks for expected columns
        # common: state, district, date/year, income_mean/median
        have_cols = set([c.lower() for c in inc_dist.columns])
        needed_any = {"state", "district"} & have_cols
        if not needed_any:
            st.sidebar.warning("Household Income by District loaded, but no obvious 'state'/'district' columns found.")
        st.sidebar.caption("✓ Household Income by District (annual) loaded.")
        st.session_state["income_district_annual"] = inc_dist
    except Exception as e:
        st.sidebar.error(f"Income-by-district load error: {e}")

# ---------------------------
# Data Quality & Trimming
# ---------------------------
st.subheader("Data Quality Check (Quarterly Merge)")

def coverage(series):
    nonnull = merged[~series.isna()]
    if nonnull.empty:
        return ("—", "—", 0)
    q = merged.loc[~series.isna(), "quarter"]
    return (str(q.min()), str(q.max()), int(series.notna().sum()))

cols = {
    "p_rate": "Participation rate (state)",
    "u_rate": "Unemployment rate (state)",
    "cpi_index": "CPI index (state)",
    "youth_unemp_rate": "Youth unemployment (national)",
    "skills_underemp_rate": "Skills underemployment (national)",
    "time_underemp_rate": "Time underemployment (national)",
    "YMI": "Youth Mismatch Index (national)",
}
rows = []
for c, label in cols.items():
    qmin, qmax, nn = coverage(merged[c])
    rows.append({"Metric": label, "First quarter": qmin, "Last quarter": qmax, "Non-null rows": nn})
st.dataframe(pd.DataFrame(rows))

trim = st.checkbox("Trim to common quarter range (intersection of core metrics)", value=True)
if trim:
    sets = []
    for c in ["youth_unemp_rate", "skills_underemp_rate", "time_underemp_rate"]:
        qs = merged.loc[merged[c].notna(), "quarter"].unique()
        if len(qs) > 0:
            sets.append(set(qs))
    if sets:
        common_q = set.intersection(*sets) if len(sets) > 1 else sets[0]
        merged = merged[merged["quarter"].isin(common_q)]
        st.caption(f"Trimmed to {len(common_q)} common quarters across core series.")
    else:
        st.warning("No quarter overlap across core series; showing full union (may contain NaNs).")

st.success(f"Combined rows (after trim): {len(merged):,}")
st.dataframe(merged.head(20), use_container_width=True)

# Store for the other Streamlit pages
st.session_state["df"] = merged.assign(quarter=merged["quarter"].astype(str))
qs = pd.PeriodIndex(st.session_state["df"]["quarter"].astype(str)).astype(str).tolist()
st.session_state["quarters"] = sorted(set(qs), key=lambda x: (int(x[:4]), int(x[-1])))
st.session_state["states"] = sorted(st.session_state["df"]["state"].dropna().unique())

st.markdown("### Pages")
st.markdown("- **Overview** — KPIs, national trends, YMI weights, LLM explain, PDF brief")
st.markdown("- **States Map** — Choropleth/bar + LLM explain for a selected quarter")
st.markdown("- **League & Gaps** — Rankings + youth vs overall gap")
st.markdown("- **Drivers & Correlations** — Contributions to YMI + correlation matrix")
st.caption("Note: Files 5, 7, and 8 (annual) are loaded for future ‘Annual Context’ / geospatial drilldowns.")
