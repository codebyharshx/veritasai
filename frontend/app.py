"""Veritas Frontend — Streamlit app with three tabs.

Tab 1: Geographic Explorer (Map)
Tab 2: Facility Inspector
Tab 3: Natural Language Query (Ask)
"""
import streamlit as st

st.set_page_config(
    page_title="Veritas — Healthcare Trust Layer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import tab components
from frontend.tabs.map_tab import render_map_tab
from frontend.tabs.inspector_tab import render_inspector_tab
from frontend.tabs.query_tab import render_query_tab

# Header
st.title("🏥 Veritas")
st.markdown("**Truth Layer for Indian Healthcare** — Verified facility capabilities with full traceability")

st.markdown("---")

# Main tabs
tab1, tab2, tab3 = st.tabs(["🗺️ Geographic Explorer", "🔍 Facility Inspector", "💬 Ask"])

with tab1:
    render_map_tab()

with tab2:
    render_inspector_tab()

with tab3:
    render_query_tab()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    Veritas runs on Llama 3.3 70B via Databricks AI Gateway |
    Mosaic AI Vector Search | Unity Catalog | MLflow Tracing
    </div>
    """,
    unsafe_allow_html=True,
)
