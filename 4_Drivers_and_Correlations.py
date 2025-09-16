
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.header("Drivers & Correlations")

if "df" not in st.session_state:
    st.warning("Upload the merged Excel on the Home page first.")
    st.stop()

df = st.session_state["df"]
nat = df.groupby("quarter", as_index=False).agg({
    "youth_unemp_rate":"mean",
    "skills_underemp_rate":"mean",
    "time_underemp_rate":"mean",
    "u_rate":"mean",
    "cpi_index":"mean",
    "YMI":"mean"
})

st.subheader("Contributions to YMI (stack approx.)")
w_u = st.slider("Weight: Youth Unemployment", 0.0, 1.0, 0.6, 0.05)
w_s = st.slider("Weight: Skills Underemployment", 0.0, 1.0, 0.3, 0.05)
w_t = st.slider("Weight: Time Underemployment", 0.0, 1.0, 0.1, 0.05)

cont = nat.copy()
cont["yu_c"] = w_u*cont["youth_unemp_rate"]
cont["su_c"] = w_s*cont["skills_underemp_rate"]
cont["tu_c"] = w_t*cont["time_underemp_rate"]

fig, ax = plt.subplots(figsize=(10,5))
ax.stackplot(cont["quarter"], cont["yu_c"], cont["su_c"], cont["tu_c"],
             labels=["Youth Unemp","Skills Underemp","Time Underemp"], alpha=0.8)
ax.plot(cont["quarter"], (cont["yu_c"]+cont["su_c"]+cont["tu_c"])/(max(w_u+w_s+w_t,1e-9)),
        label="YMI (weights)", linewidth=2)
ax.set_xlabel("Quarter"); ax.set_ylabel("Contribution / Index"); ax.legend(); ax.grid(True); plt.xticks(rotation=45)
st.pyplot(fig)

st.subheader("Correlation Matrix (national averages)")
mat = cont[["YMI","youth_unemp_rate","skills_underemp_rate","time_underemp_rate","u_rate","cpi_index"]].corr()
st.dataframe(mat.style.background_gradient(cmap="RdBu", axis=None))
