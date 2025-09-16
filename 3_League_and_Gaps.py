
import streamlit as st
import pandas as pd

st.header("League & Gaps")

if "df" not in st.session_state:
    st.warning("Upload the merged Excel on the Home page first.")
    st.stop()

df = st.session_state["df"]
quarters = st.session_state["quarters"]

q = st.selectbox("Quarter", quarters, index=len(quarters)-1 if quarters else 0)

d = df[df["quarter"]==q].copy()
d["youth_gap"] = d["youth_unemp_rate"] - d["u_rate"]

st.subheader("Rankings (Highest YMI first)")
cols = ["state","YMI","youth_unemp_rate","u_rate","cpi_index"]
st.dataframe(d[cols].sort_values("YMI", ascending=False).reset_index(drop=True))

st.subheader("Youth vs Overall Unemployment Gap (pp)")
gap = d[["state","youth_gap"]].sort_values("youth_gap", ascending=False).reset_index(drop=True)
st.dataframe(gap)
