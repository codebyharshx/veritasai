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

# Custom CSS for better responsiveness and margins
st.markdown("""
<style>
    /* Main container padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Header styling */
    h1 {
        color: #1e3a5f;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
    }

    /* Card-like containers */
    .stContainer {
        background: #ffffff;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a5f;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #666;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .stButton > button[kind="primary"] {
        background-color: #ff4b4b;
        color: white;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 0.6rem 1rem;
    }

    .stTextInput > div > div > input:focus {
        border-color: #ff4b4b;
        box-shadow: 0 0 0 2px rgba(255,75,75,0.2);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        padding: 1rem;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #1e3a5f;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        font-weight: 500;
    }

    /* Alert boxes */
    .stAlert {
        border-radius: 8px;
        padding: 1rem;
    }

    /* Progress bar */
    .stProgress > div > div {
        border-radius: 10px;
        background-color: #ff4b4b;
    }

    /* Divider */
    hr {
        margin: 1.5rem 0;
        border: none;
        border-top: 1px solid #e0e0e0;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px;
            font-size: 0.9rem;
        }
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Import tab components
from tabs.map_tab import render_map_tab
from tabs.inspector_tab import render_inspector_tab
from tabs.query_tab import render_query_tab
from tabs.approach_tab import render_approach_tab

# Header with better spacing
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏥 Veritas")
    st.markdown("**Truth Layer for Indian Healthcare** — Verified facility capabilities with full traceability")
with col2:
    st.markdown("")
    st.markdown("")
    st.caption("Hack-Nation 2026 | Databricks Track")

st.markdown("")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Geographic Explorer", "🔍 Facility Inspector", "💬 Ask", "📋 Our Approach"])

with tab1:
    render_map_tab()

with tab2:
    render_inspector_tab()

with tab3:
    render_query_tab()

with tab4:
    render_approach_tab()

# Footer
st.markdown("")
st.markdown("")
st.markdown(
    """
    <div style='text-align: center; padding: 2rem 0; border-top: 1px solid #e0e0e0; margin-top: 2rem;'>
        <p style='color: #666; font-size: 0.85rem; margin-bottom: 0.5rem;'>
            <strong>Powered by</strong>
        </p>
        <p style='color: #888; font-size: 0.8rem;'>
            Llama 3.3 70B &nbsp;•&nbsp; Databricks AI Gateway &nbsp;•&nbsp;
            Mosaic AI Vector Search &nbsp;•&nbsp; Unity Catalog &nbsp;•&nbsp; MLflow Tracing
        </p>
        <p style='color: #aaa; font-size: 0.75rem; margin-top: 1rem;'>
            Built for Hack-Nation 5th Global AI Hackathon 2026
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
