
import streamlit as st
from utils.data_loader import ensure_session_data

st.set_page_config(page_title="Malaysia Youth Jobs Copilot", layout="wide")
st.title("🇲🇾 Malaysia Youth Jobs Copilot")
st.caption("Core + Context (Quarterly) • OpenDOSM • Geospatial • LLM explainers • PDF export")

st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload merged Excel (Cleaned_CorePlusContext_Quarterly.xlsx)", type=["xlsx"])

if uploaded is not None:
    ensure_session_data(uploaded)
    st.success("Data loaded. Use the pages in the sidebar to explore.")
else:
    st.info("Upload the merged Excel to begin.")

st.markdown("### Pages")
st.markdown("- **Overview** — KPIs, national trends, YMI weights, LLM explain, PDF brief")
st.markdown("- **States Map** — Choropleth/bar + LLM explain for a selected quarter")
st.markdown("- **League & Gaps** — Rankings + youth vs overall gap")
st.markdown("- **Drivers & Correlations** — Contributions to YMI + correlation matrix")
