
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Malaysia Youth Jobs Copilot — CSV Inputs (7 files)", layout="wide")
st.title("🇲🇾 Malaysia Youth Jobs Copilot — CSV Inputs (7 files)")
st.caption("Upload the seven raw CSV files from OpenDOSM. The app will clean, align to quarters, and combine. "
           "Tip: If you see many NaN values, enable 'Trim to common quarter range' below.")

st.sidebar.header("Upload 7 CSV files")
f1 = st.sidebar.file_uploader("1) Monthly Youth Unemployment (CSV)", type=["csv"], key="f1")
f2 = st.sidebar.file_uploader("2) Quarterly Skills-Related Underemployment by Age (CSV)", type=["csv"], key="f2")
f3 = st.sidebar.file_uploader("3) Quarterly Time-Related Underemployment by Age (CSV)", type=["csv"], key="f3")
f4 = st.sidebar.file_uploader("4) Quarterly Labour Force by State (CSV)", type=["csv"], key="f4")
f5 = st.sidebar.file_uploader("5) Annual Productivity by Economic Sector (CSV) [optional]", type=["csv"], key="f5")
f6 = st.sidebar.file_uploader("6) Monthly CPI by State & Division (2-digit) (CSV)", type=["csv"], key="f6")
f7 = st.sidebar.file_uploader("7) Household Income by State (CSV) [optional]", type=["csv"], key="f7")

ready = all([f1,f2,f3,f4,f6])
if not ready:
    st.info("Please upload at least files 1, 2, 3, 4, and 6. Files 5 and 7 are optional (annual context).")
    st.stop()

def to_quarter_from_date(s):
    dt = pd.to_datetime(s, errors="coerce")
    return dt.dt.to_period("Q")

# ------- CORE (national quarterly) -------
# Youth Unemployment (monthly) -> quarterly
yu = pd.read_csv(f1)
date_col = "date" if "date" in yu.columns else yu.columns[0]
yu[date_col] = pd.to_datetime(yu[date_col], errors="coerce")
cand = [c for c in yu.columns if re.search(r"(15.*30|youth|unemp)", c, flags=re.I)]
if "u_rate_15_30" in yu.columns:
    ycol = "u_rate_15_30"
elif cand:
    ycol = cand[0]
else:
    ycol = yu.columns[1]
yu = yu[[date_col, ycol]].rename(columns={date_col:"date", ycol:"youth_unemp_rate"})
yu["quarter"] = yu["date"].dt.to_period("Q")
yu_q = yu.groupby("quarter", as_index=False)["youth_unemp_rate"].mean()

# Skills-related Underemployment (quarterly)
su = pd.read_csv(f2)
dcol = "date" if "date" in su.columns else su.columns[0]
su[dcol] = pd.to_datetime(su[dcol], errors="coerce")
su["quarter"] = su[dcol].dt.to_period("Q")
srate = "sru" if "sru" in su.columns else [c for c in su.columns if re.search(r"(rate|under)", c, re.I)][0]
if "age" in su.columns:
    su = su[su["age"].astype(str).str.lower().isin(["overall","all","all ages","semua"])]
su_q = su.groupby("quarter", as_index=False)[srate].mean().rename(columns={srate:"skills_underemp_rate"})

# Time-related Underemployment (quarterly)
tu = pd.read_csv(f3)
dcol3 = "date" if "date" in tu.columns else tu.columns[0]
tu[dcol3] = pd.to_datetime(tu[dcol3], errors="coerce")
tu["quarter"] = tu[dcol3].dt.to_period("Q")
trate = "tru" if "tru" in tu.columns else [c for c in tu.columns if re.search(r"(rate|under)", c, re.I)][0]
if "age" in tu.columns:
    tu = tu[tu["age"].astype(str).str.lower().isin(["overall","all","all ages","semua"])]
tu_q = tu.groupby("quarter", as_index=False)[trate].mean().rename(columns={trate:"time_underemp_rate"})

nat = yu_q.merge(su_q, on="quarter", how="outer").merge(tu_q, on="quarter", how="outer")
nat = nat.sort_values("quarter").reset_index(drop=True)
w = {"youth_unemp_rate":0.6, "skills_underemp_rate":0.3, "time_underemp_rate":0.1}
nat["YMI"] = (w["youth_unemp_rate"]*nat["youth_unemp_rate"] +
              w["skills_underemp_rate"]*nat["skills_underemp_rate"] +
              w["time_underemp_rate"]*nat["time_underemp_rate"])

# ------- CONTEXT (state quarterly) -------
lf = pd.read_csv(f4)
lf_date = "date" if "date" in lf.columns else lf.columns[0]
lf[lf_date] = pd.to_datetime(lf[lf_date], errors="coerce")
lf["quarter"] = lf[lf_date].dt.to_period("Q")
# Find p_rate/u_rate robustly
def find_col(df, key):
    if key in df.columns: return key
    for c in df.columns:
        if c.lower()==key: return c
    for c in df.columns:
        if key.replace("_","") in c.lower().replace("_",""):
            return c
    return None
pcol = find_col(lf, "p_rate") or find_col(lf, "participation")
ucol = find_col(lf, "u_rate") or find_col(lf, "unemployment")
lf_q = lf.rename(columns={pcol:"p_rate", ucol:"u_rate"})[["state","quarter","p_rate","u_rate"]]

# CPI monthly -> quarterly avg; try to detect 'overall' division labels
cpi = pd.read_csv(f6)
cpi_d = "date" if "date" in cpi.columns else cpi.columns[0]
cpi[cpi_d] = pd.to_datetime(cpi[cpi_d], errors="coerce")
cpi["quarter"] = cpi[cpi_d].dt.to_period("Q")
if "division" in cpi.columns:
    # common labels for overall CPI
    overall_aliases = {"overall","all items","all-items","all item","semua barang","semua barangan"}
    mask = cpi["division"].astype(str).str.lower().isin(overall_aliases)
    if mask.any():
        cpi = cpi[mask]
# detect value column
ival = "index" if "index" in cpi.columns else None
if ival is None:
    cand = [c for c in cpi.columns if re.search(r"(index|cpi)", c, re.I)]
    ival = cand[0] if cand else cpi.columns[-1]
cpi_q = cpi.groupby(["state","quarter"], as_index=False)[ival].mean().rename(columns={ival:"cpi_index"})

state_q = lf_q.merge(cpi_q, on=["state","quarter"], how="outer")

merged = state_q.merge(nat, on="quarter", how="left")

# ------- Data Quality & Trimming -------
st.subheader("Data Quality Check")
def coverage(series):
    nonnull = merged[~series.isna()]
    if nonnull.empty: return ("—","—",0)
    q = merged.loc[~series.isna(),"quarter"]
    return (str(q.min()), str(q.max()), int(series.notna().sum()))

cols = {
    "p_rate":"Participation rate (state)",
    "u_rate":"Unemployment rate (state)",
    "cpi_index":"CPI index (state)",
    "youth_unemp_rate":"Youth unemployment (national)",
    "skills_underemp_rate":"Skills underemployment (national)",
    "time_underemp_rate":"Time underemployment (national)",
    "YMI":"Youth Mismatch Index (national)"
}
rows = []
for c, label in cols.items():
    qmin, qmax, nn = coverage(merged[c])
    rows.append({"Metric":label, "First quarter":qmin, "Last quarter":qmax, "Non-null rows":nn})
st.dataframe(pd.DataFrame(rows))

trim = st.checkbox("Trim to common quarter range (intersection of core metrics)", value=True)
if trim:
    # find common quarters across the three core series
    sets = []
    for c in ["youth_unemp_rate","skills_underemp_rate","time_underemp_rate"]:
        qs = merged.loc[merged[c].notna(),"quarter"].unique()
        if len(qs)>0: sets.append(set(qs))
    if sets:
        common_q = set.intersection(*sets) if len(sets)>1 else sets[0]
        merged = merged[merged["quarter"].isin(common_q)]
        st.caption(f"Trimmed to {len(common_q)} common quarters across core series.")
    else:
        st.warning("No overlap found across core series; showing full union (may contain many NaNs).")

st.success(f"Combined rows (after trim): {len(merged):,}")
st.dataframe(merged.head(20), use_container_width=True)

# Store for pages
st.session_state["df"] = merged.assign(quarter=merged["quarter"].astype(str))
qs = pd.PeriodIndex(st.session_state["df"]["quarter"].astype(str)).astype(str).tolist()
st.session_state["quarters"] = sorted(set(qs), key=lambda x: (int(x[:4]), int(x[-1])))
st.session_state["states"] = sorted(st.session_state["df"]["state"].dropna().unique())

st.markdown("### Pages")
st.markdown("- **Overview** — KPIs, national trends, YMI weights, LLM explain, PDF brief")
st.markdown("- **States Map** — Choropleth/bar + LLM explain for a selected quarter")
st.markdown("- **League & Gaps** — Rankings + youth vs overall gap")
st.markdown("- **Drivers & Correlations** — Contributions to YMI + correlation matrix")
