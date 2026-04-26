"""Facility Inspector Tab — Search and detail view for individual facilities."""
import streamlit as st
import requests
from typing import Optional

import os
API_BASE = os.environ.get("API_URL", "http://localhost:8000")


def get_facility_details(facility_id: str) -> Optional[dict]:
    """Fetch detailed facility information."""
    try:
        response = requests.get(f"{API_BASE}/api/facilities/{facility_id}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_trust_debate(facility_id: str) -> Optional[dict]:
    """Fetch the trust debate transcript."""
    try:
        response = requests.get(f"{API_BASE}/api/trust/{facility_id}/debate")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def search_facilities(query: str) -> list:
    """Search facilities by name."""
    try:
        response = requests.get(f"{API_BASE}/api/facilities", params={"limit": 20})
        if response.status_code == 200:
            facilities = response.json().get("facilities", [])
            # Filter by query
            if query:
                facilities = [
                    f for f in facilities
                    if query.lower() in f.get("facility_name", "").lower()
                ]
            return facilities
    except:
        pass
    return []


def render_inspector_tab():
    """Render the Facility Inspector tab."""

    st.markdown("""
    <div style='margin-bottom: 1.5rem;'>
        <h3 style='margin-bottom: 0.5rem; color: #1e3a5f;'>Can I trust this facility?</h3>
        <p style='color: #666; line-height: 1.6;'>
            Search for a facility to see its <strong>verified capabilities</strong>,
            <strong>flagged contradictions</strong>, and the full
            <strong>Advocate/Skeptic/Judge debate</strong> that produced its trust score.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Search box
    search_query = st.text_input(
        "🔍 Search facility by name",
        placeholder="e.g., Apollo Hospital, AIIMS Delhi...",
    )

    # Demo facility for when API is not connected
    demo_facility = {
        "facility_id": "demo-123",
        "facility_name": "Demo City Hospital",
        "state": "Maharashtra",
        "district": "Mumbai",
        "pin_code": "400001",
        "latitude": 19.076,
        "longitude": 72.877,
        "facility_type": "hospital",
        "bed_count": 200,
        "trust_score": 72,
        "verified_capabilities": [
            {"capability": "Emergency Surgery", "confidence": 0.85, "evidence_sentence": "24/7 emergency surgical services available with experienced surgeons."},
            {"capability": "ICU Care", "confidence": 0.90, "evidence_sentence": "Fully equipped ICU with 20 beds and ventilator support."},
            {"capability": "Cardiology", "confidence": 0.75, "evidence_sentence": "Cardiology department with ECG and basic cardiac care."},
        ],
        "staff": [
            {"role": "Surgeon", "specialty": "General Surgery"},
            {"role": "Physician", "specialty": "Internal Medicine"},
        ],
        "equipment": [
            {"item": "Ventilator", "functional": True},
            {"item": "ECG Machine", "functional": True},
            {"item": "X-Ray", "functional": False, "note": "Under repair"},
        ],
        "contradictions": [
            {
                "claim": "24/7 Emergency Services",
                "evidence_gap": "Staff schedule shows only daytime coverage",
                "trust_impact": -15,
                "severity": "high",
            }
        ],
        "citations": [],
    }

    demo_debate = {
        "advocate_argument": "This hospital demonstrates strong emergency care capabilities. The notes explicitly state '24/7 emergency surgical services available with experienced surgeons,' supported by a fully equipped ICU with 20 beds and ventilator support. The presence of cardiology services with ECG facilities further strengthens the facility's comprehensive care profile.",
        "skeptic_argument": "While the facility claims 24/7 emergency services, the staff schedule shows only daytime coverage, raising concerns about actual round-the-clock availability. -15 points: Claims 24/7 emergency but staff availability contradicts this. Additionally, the X-Ray machine is noted as 'under repair,' which could limit diagnostic capabilities. -5 points: Key diagnostic equipment non-functional.",
        "judge_reasoning": "The facility has legitimate emergency capabilities with a well-equipped ICU, but the contradiction between claimed 24/7 service and actual staff scheduling is significant. Score of 72 reflects strong infrastructure offset by operational concerns.",
    }

    # Try to fetch from API or use demo
    facilities = search_facilities(search_query) if search_query else []

    if not facilities and not search_query:
        # Show demo
        st.info("**Demo Mode** — Enter a search term or connect the API to see real facilities.")
        selected_facility = demo_facility
        debate = demo_debate
    elif facilities:
        # Show search results
        facility_options = {f["facility_name"]: f["facility_id"] for f in facilities}
        selected_name = st.selectbox("Select a facility", options=list(facility_options.keys()))
        selected_id = facility_options.get(selected_name)

        selected_facility = get_facility_details(selected_id)
        debate = get_trust_debate(selected_id) if selected_facility else None

        if not selected_facility:
            selected_facility = demo_facility
            debate = demo_debate
    else:
        st.warning("No facilities found matching your search.")
        return

    # Display facility details
    st.markdown("---")

    # Header with trust score
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(selected_facility["facility_name"])
        st.markdown(f"📍 {selected_facility['district']}, {selected_facility['state']} | {selected_facility['facility_type'].title()}")
    with col2:
        score = selected_facility.get("trust_score", "N/A")
        color = "🟢" if score and score >= 70 else "🟡" if score and score >= 50 else "🔴"
        st.metric("Trust Score", f"{color} {score}/100" if score else "Not scored")

    # Three sections
    st.markdown("---")

    # Section 1: Verified Capabilities
    st.markdown("#### ✅ Verified Capabilities")

    capabilities = selected_facility.get("verified_capabilities", [])
    if capabilities:
        for cap in capabilities:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{cap['capability']}**")
                    # Hoverable evidence
                    with st.expander("📄 View Evidence"):
                        st.markdown(f"*\"{cap['evidence_sentence']}\"*")
                with col2:
                    conf = cap.get('confidence', 0)
                    st.progress(conf, text=f"{conf*100:.0f}%")
    else:
        st.info("No capabilities extracted yet.")

    # Section 2: Flagged Contradictions
    st.markdown("#### ⚠️ Flagged Contradictions")

    contradictions = selected_facility.get("contradictions", [])
    if contradictions:
        for contra in contradictions:
            severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(contra.get("severity", "medium"), "🟡")
            with st.container():
                st.markdown(f"{severity_color} **{contra['claim']}**")
                st.markdown(f"*Gap: {contra['evidence_gap']}*")
                st.markdown(f"Trust impact: **{contra['trust_impact']} points**")
                st.markdown("---")
    else:
        st.success("No contradictions found.")

    # Section 3: Trust Reasoning (Debate Transcript)
    st.markdown("#### 🧠 Trust Reasoning")

    if debate:
        with st.expander("📜 View Full Advocate/Skeptic/Judge Debate", expanded=False):
            st.markdown("##### 📢 Advocate's Argument")
            st.info(debate.get("advocate_argument", "N/A"))

            st.markdown("##### 🔍 Skeptic's Argument")
            st.warning(debate.get("skeptic_argument", "N/A"))

            st.markdown("##### ⚖️ Judge's Verdict")
            st.success(debate.get("judge_reasoning", "N/A"))

            # MLflow trace link
            if debate.get("mlflow_trace_url"):
                st.markdown(f"[🔗 Open in MLflow]({debate['mlflow_trace_url']})")
    else:
        st.info("Trust debate not yet run for this facility.")
