
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Malaysia Youth Jobs Copilot", layout="wide")
st.title("🇲🇾 Malaysia Youth Jobs Copilot — CSV Inputs (7 files)")
st.caption("Upload the seven raw CSV files from OpenDOSM. The app will clean, align to quarters, and combine into one dataset for all pages.")

st.sidebar.header("Upload 7 CSV files")

# 1) Monthly Youth Unemployment (national)
f1 = st.sidebar.file_uploader("1) Monthly Youth Unemployment (CSV)", type=["csv"], key="f1")

# 2) Quarterly Skills-Related Underemployment by Age (national)
f2 = st.sidebar.file_uploader("2) Quarterly Skills-Related Underemployment by Age (CSV)", type=["csv"], key="f2")

# 3) Quarterly Time-Related Underemployment by Age (national)
f3 = st.sidebar.file_uploader("3) Quarterly Time-Related Underemployment by Age (CSV)", type=["csv"], key="f3")

# 4) Quarterly Principal Labour Force Statistics by State
f4 = st.sidebar.file_uploader("4) Quarterly Labour Force by State (CSV)", type=["csv"], key="f4")

# 5) Annual Productivity by Economic Sector (optional for quarterly merge)
f5 = st.sidebar.file_uploader("5) Annual Productivity by Economic Sector (CSV)", type=["csv"], key="f5")

# 6) Monthly CPI by State & Division (2-digit)
f6 = st.sidebar.file_uploader("6) Monthly CPI by State & Division (CSV)", type=["csv"], key="f6")

# 7) Household Income by State (annual)
f7 = st.sidebar.file_uploader("7) Household Income by State (CSV)", type=["csv"], key="f7")

ready = all([f1,f2,f3,f4,f6])  # minimal set for quarterly merge (f5, f7 optional)
if not ready:
    st.info("Please upload at least files 1, 2, 3, 4, and 6. Files 5 and 7 are used for annual context and can be added later.")
else:
    # ------- Load & clean core (national) -------
    # 1) Youth Unemployment monthly -> quarterly avg
    yu = pd.read_csv(f1)
    # Expect columns like: date, u_rate_15_30 (rename if needed)
    date_col = "date" if "date" in yu.columns else yu.columns[0]
    yu[date_col] = pd.to_datetime(yu[date_col])
    # try common youth rate column names
    cand = [c for c in yu.columns if "15" in c or "youth" in c or "unemp" in c]
    ycol = "u_rate_15_30" if "u_rate_15_30" in yu.columns else (cand[0] if cand else yu.columns[1])
    yu = yu[[date_col, ycol]].rename(columns={date_col:"date", ycol:"youth_unemp_rate"})
    yu["quarter"] = yu["date"].dt.to_period("Q")
    yu_q = yu.groupby("quarter", as_index=False)["youth_unemp_rate"].mean()

    # 2) Skills-related underemployment quarterly (filter overall age if present)
    su = pd.read_csv(f2)
    dcol = "date" if "date" in su.columns else su.columns[0]
    su[dcol] = pd.to_datetime(su[dcol])
    su["quarter"] = su[dcol].dt.to_period("Q")
    # detect rate column
    srate = "sru" if "sru" in su.columns else [c for c in su.columns if "rate" in c or "under" in c][0]
    if "age" in su.columns:
        su = su[su["age"].str.lower().eq("overall")]
    su_q = su.groupby("quarter", as_index=False)[srate].mean().rename(columns={srate:"skills_underemp_rate"})

    # 3) Time-related underemployment quarterly (filter overall age if present)
    tu = pd.read_csv(f3)
    dcol3 = "date" if "date" in tu.columns else tu.columns[0]
    tu[dcol3] = pd.to_datetime(tu[dcol3])
    tu["quarter"] = tu[dcol3].dt.to_period("Q")
    trate = "tru" if "tru" in tu.columns else [c for c in tu.columns if "rate" in c or "under" in c][0]
    if "age" in tu.columns:
        tu = tu[tu["age"].str.lower().eq("overall")]
    tu_q = tu.groupby("quarter", as_index=False)[trate].mean().rename(columns={trate:"time_underemp_rate"})

    # Merge core -> national quarterly
    nat = yu_q.merge(su_q, on="quarter", how="outer").merge(tu_q, on="quarter", how="outer")
    nat = nat.sort_values("quarter").reset_index(drop=True)
    # Simple YMI
    w = {"youth_unemp_rate":0.6, "skills_underemp_rate":0.3, "time_underemp_rate":0.1}
    nat["YMI"] = (w["youth_unemp_rate"]*nat["youth_unemp_rate"] +
                  w["skills_underemp_rate"]*nat["skills_underemp_rate"] +
                  w["time_underemp_rate"]*nat["time_underemp_rate"])

    # ------- Load & clean context (state quarterly) -------
    # 4) Labour force by state quarterly
    lf = pd.read_csv(f4)
    lf_date = "date" if "date" in lf.columns else lf.columns[0]
    lf[lf_date] = pd.to_datetime(lf[lf_date])
    lf["quarter"] = lf[lf_date].dt.to_period("Q")
    # expect state, p_rate, u_rate
    lcols = {"p_rate":"p_rate","u_rate":"u_rate"}
    # soft map if different casing
    for k in list(lcols.keys()):
        if lcols[k] not in lf.columns:
            cand = [c for c in lf.columns if c.lower()==k]
            if cand:
                lcols[k] = cand[0]
    lf_q = lf.rename(columns={lcols["p_rate"]:"p_rate", lcols["u_rate"]:"u_rate"})[["state","quarter","p_rate","u_rate"]]

    # 6) CPI monthly -> quarterly avg (overall division only)
    cpi = pd.read_csv(f6)
    cpi_d = "date" if "date" in cpi.columns else cpi.columns[0]
    cpi[cpi_d] = pd.to_datetime(cpi[cpi_d])
    cpi["quarter"] = cpi[cpi_d].dt.to_period("Q")
    if "division" in cpi.columns:
        cpi = cpi[cpi["division"].str.lower().eq("overall")]
    # value column name
    ival = "index" if "index" in cpi.columns else [c for c in cpi.columns if "index" in c or "cpi" in c][0]
    cpi_q = cpi.groupby(["state","quarter"], as_index=False)[ival].mean().rename(columns={ival:"cpi_index"})

    # Join state context
    state_q = lf_q.merge(cpi_q, on=["state","quarter"], how="outer")

    # Spread national core into each state row (repeat per quarter for comparison on the same row)
    merged = state_q.merge(nat, on="quarter", how="left")

    # Optional annual context loads (5 & 7) — kept separate for now
    if f5 is not None:
        prod = pd.read_csv(f5)
        st.sidebar.caption("Productivity loaded (annual, sector). Used on future 'Annual context' page.")
    if f7 is not None:
        inc = pd.read_csv(f7)
        st.sidebar.caption("Household Income by State loaded (annual). Used on future 'Annual context' page.")

    st.success(f"Combined rows: {len(merged):,}")
    st.dataframe(merged.head(20), use_container_width=True)

    # Store for pages
    st.session_state["df"] = merged.assign(quarter=merged["quarter"].astype(str))
    qs = sorted(st.session_state["df"]["quarter"].dropna().unique(), key=lambda x: (x[:4], x[-1:]))
    st.session_state["quarters"] = qs
    st.session_state["states"] = sorted(st.session_state["df"]["state"].dropna().unique())

st.markdown("### Pages")
st.markdown("- **Overview** — KPIs, national trends, YMI weights, LLM explain, PDF brief")
st.markdown("- **States Map** — Choropleth/bar + LLM explain for a selected quarter")
st.markdown("- **League & Gaps** — Rankings + youth vs overall gap")
st.markdown("- **Drivers & Correlations** — Contributions to YMI + correlation matrix")
