"""Approach Tab — Explains the complete Veritas methodology."""
import streamlit as st


def render_approach_tab():
    """Render the approach explanation page."""

    st.header("Our Approach")
    st.markdown("### How Veritas Verifies Healthcare Facility Claims")

    st.markdown("---")

    # Problem Statement
    st.subheader("The Problem")
    st.markdown("""
    India has **10,000+ healthcare facilities** with self-reported, unverified capability claims.
    A hospital might claim "24/7 emergency surgery" while their notes reveal "limited weekend staff."

    **This creates critical issues:**
    - State health departments can't accurately plan infrastructure
    - Policymakers allocate budgets based on unreliable data
    - NGOs waste resources intervening in wrong locations
    - Hospital networks make referrals to facilities that can't deliver
    """)

    st.markdown("---")

    # Solution Overview
    st.subheader("The Solution: 5-Stage AI Pipeline")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("""
        **Stage 1: Ingestion**
        Load facility records into Delta Lake

        **Stage 2: Extraction**
        LLM extracts structured capabilities

        **Stage 3: Trust Debate**
        3-agent adversarial verification

        **Stage 4: Geographic**
        Medical desert identification

        **Stage 5: Vector Index**
        Semantic search embeddings
        """)

    with col2:
        st.image("https://img.icons8.com/color/200/artificial-intelligence.png", width=150)

    st.markdown("---")

    # Multi-Agent Trust Debate - The Core Innovation
    st.subheader("Core Innovation: Multi-Agent Trust Debate")

    st.markdown("""
    Unlike simple RAG systems that just retrieve information, Veritas **actively challenges claims**
    through an adversarial debate between three AI agents:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Advocate")
        st.markdown("""
        Presents evidence **supporting** the facility's claims.

        *"This hospital has 750 beds with documented emergency surgery capability..."*
        """)

    with col2:
        st.markdown("#### Skeptic")
        st.markdown("""
        **Cross-examines** claims, hunting for contradictions and gaps.

        *"WAIT — the notes say 'limited staff on weekends.' This contradicts 24/7 surgery. -15 points."*
        """)

    with col3:
        st.markdown("#### Judge")
        st.markdown("""
        **Weighs arguments** and assigns an explainable score (0-100).

        *"Valid concern. Score: 62/100. Recommend for weekday emergencies only."*
        """)

    st.markdown("---")

    # Example Debate
    st.subheader("Example: AIIMS Patna Debate")

    with st.expander("View Full Debate Transcript", expanded=True):
        st.markdown("**Facility Claim:** Emergency surgery available")
        st.markdown("**Bed Count:** 750")

        st.markdown("---")

        st.markdown("**Advocate:**")
        st.info("""
        AIIMS Patna is a premier government medical institute with an extraordinary 750-bed capacity.
        Emergency surgery is available, indicating surgical capabilities. As a government institution,
        it serves a critical role in Bihar's healthcare infrastructure.
        """)

        st.markdown("**Skeptic:**")
        st.warning("""
        Major concerns identified:
        - "Limited staff on weekends" **directly contradicts** emergency surgery availability claim. **-15 points**
        - "Oncology department under construction" means cancer care is **not actually available**. **-10 points**
        - Government hospitals often face resource constraints not mentioned. **-8 points**
        """)

        st.markdown("**Judge:**")
        st.success("""
        AIIMS Patna has significant credibility issues. The weekend staffing limitation is a serious
        concern for emergency care. The oncology claim is misleading since the department is incomplete.

        **Final Score: 62/100** — Use for weekday emergencies only, verify oncology status before referral.
        """)

    st.markdown("---")

    # Medical Desert Detection
    st.subheader("Medical Desert Detection")

    st.markdown("""
    Using Haversine distance calculations, we identify regions where critical healthcare is inaccessible:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🟢 Green Zone")
        st.markdown("< 50 km to verified facility")

    with col2:
        st.markdown("### 🟡 Yellow Zone")
        st.markdown("50-100 km to verified facility")

    with col3:
        st.markdown("### 🔴 Red Zone")
        st.markdown("> 100 km — **Medical Desert**")

    st.markdown("---")

    # Technology Stack
    st.subheader("Technology Stack")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Platform**
        - Databricks (Delta Lake, Unity Catalog)
        - MLflow Tracing for observability

        **AI Models**
        - Llama 3.3 70B — Trust debate
        - BGE-Large-EN — Semantic embeddings
        """)

    with col2:
        st.markdown("""
        **Backend**
        - FastAPI (deployed on Vercel)
        - RESTful API architecture

        **Frontend**
        - Streamlit with Folium maps
        - Interactive visualizations
        """)

    st.markdown("---")

    # Results
    st.subheader("Results")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Facilities Processed", "10,000")

    with col2:
        st.metric("Contradictions Found", "56")

    with col3:
        st.metric("Trust Score Range", "45-92")

    with col4:
        st.metric("Medical Deserts", "Identified")

    st.markdown("---")

    # Why This Matters
    st.subheader("Why This Matters")

    st.markdown("""
    **For State Health Departments:**
    Identify where to build new facilities based on verified gaps, not self-reported data.

    **For Policymakers:**
    Allocate healthcare budgets using evidence-based trust scores and medical desert maps.

    **For NGOs:**
    Target interventions in areas with genuine need, not facilities with inflated claims.

    **For Hospital Networks:**
    Verify partner facility claims before making patient referrals.
    """)

    st.markdown("---")

    st.caption("Built for Hack-Nation 5th Global AI Hackathon — Databricks Track")
