import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.title("🥧 Interactive Pie Chart")

# ---------- Load data ----------
# data/pie_demo.csv sits next to app.py (one level above /pages)
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "pie_demo.csv"

# No caching on purpose: edits to the CSV show up on the next refresh
df = pd.read_csv(DATA_PATH)

# ---------- Widgets ----------
chosen = st.multiselect(
    "Categories to include",
    options=df["category"].tolist(),
    default=df["category"].tolist(),
)
donut = st.checkbox("Show as donut", value=False)

view = df[df["category"].isin(chosen)]

# ---------- Chart ----------
if view.empty:
    st.warning("Pick at least one category.")
else:
    fig = px.pie(
        view,
        names="category",
        values="value",
        hole=0.4 if donut else 0,
        title="Tools I Use for Data Work",
    )
    fig.update_traces(textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Show raw data"):
    st.dataframe(view, use_container_width=True)

st.divider()
st.caption("Data: `data/pie_demo.csv`")
