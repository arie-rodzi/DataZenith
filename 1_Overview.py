
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.llm_helper import compose_bullets
from utils.report import export_policy_pdf

st.header("Overview")

if "df" not in st.session_state:
    st.warning("Upload the merged Excel on the Home page first.")
    st.stop()

df = st.session_state["df"]

st.sidebar.subheader("YMI Weights")
w_u = st.sidebar.slider("Youth Unemployment", 0.0, 1.0, 0.6, 0.05)
w_s = st.sidebar.slider("Skills Underemployment", 0.0, 1.0, 0.3, 0.05)
w_t = st.sidebar.slider("Time Underemployment", 0.0, 1.0, 0.1, 0.05)

nat = df.groupby("quarter", as_index=False).agg({
    "youth_unemp_rate":"mean",
    "skills_underemp_rate":"mean",
    "time_underemp_rate":"mean",
    "u_rate":"mean",
    "cpi_index":"mean",
    "YMI":"mean"
})
nat["YMI_recomp"] = (w_u*nat["youth_unemp_rate"] + w_s*nat["skills_underemp_rate"] + w_t*nat["time_underemp_rate"]) / max(w_u+w_s+w_t, 1e-9)

c1, c2, c3, c4 = st.columns(4)
latest = nat.tail(1).squeeze()
c1.metric("YMI (weights)", f"{latest['YMI_recomp']:.1f}")
c2.metric("Youth Unemp %", f"{latest['youth_unemp_rate']:.1f}")
c3.metric("Skills Underemp %", f"{latest['skills_underemp_rate']:.1f}")
c4.metric("Overall Unemp %", f"{latest['u_rate']:.1f}")

st.subheader("National Trends")
fig, ax = plt.subplots(figsize=(10,5))
ax.plot(nat["quarter"], nat["u_rate"], label="Overall Unemployment")
ax.plot(nat["quarter"], nat["youth_unemp_rate"], label="Youth Unemployment")
ax.plot(nat["quarter"], nat["skills_underemp_rate"], label="Skills Underemployment")
ax.plot(nat["quarter"], nat["time_underemp_rate"], label="Time Underemployment")
ax.plot(nat["quarter"], nat["YMI_recomp"], label="YMI (weights)", linewidth=2)
ax.set_xlabel("Quarter"); ax.set_ylabel("Rate / Index")
ax.legend(); ax.grid(True); plt.xticks(rotation=45); st.pyplot(fig)

st.subheader("LLM Explainer (bullets)")
lang = st.radio("Language", ["ms","en"], horizontal=True)
sel_q = st.selectbox("Quarter", list(nat["quarter"]), index=len(nat)-1)
row = nat[nat["quarter"]==sel_q].iloc[0].to_dict()
row["quarter"] = sel_q
bullets = compose_bullets(row, lang)
st.text(bullets)

if st.button("Export PDF Brief"):
    path = "policy_brief.pdf"
    export_policy_pdf(path, f"Policy Brief — {sel_q}", bullets)
    with open(path, "rb") as f:
        st.download_button("Download PDF", f, file_name=f"policy_brief_{sel_q}.pdf")
