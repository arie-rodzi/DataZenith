import io
import pandas as pd
import streamlit as st

@st.cache_data
def load_merged_excel(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes))

def ensure_session_data(uploaded_file):
    df = load_merged_excel(uploaded_file.read())
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"].astype(str)
    for col in ["YMI","youth_unemp_rate","skills_underemp_rate","time_underemp_rate",
                "p_rate","u_rate","cpi_index","state"]:
        if col not in df.columns:
            df[col] = pd.NA
    st.session_state["df"] = df
    qs = sorted(df["quarter"].dropna().unique(), key=lambda x: (x[:4], x[-1:]))
    st.session_state["quarters"] = qs
    st.session_state["states"] = sorted(df["state"].dropna().unique())
