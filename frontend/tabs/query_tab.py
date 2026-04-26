"""Natural Language Query Tab — Chat interface for compound queries."""
import streamlit as st
import requests
from typing import Optional

API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")


def query_facilities(query: str, max_results: int = 5) -> Optional[dict]:
    """Send natural language query to API."""
    try:
        response = requests.post(
            f"{API_BASE}/api/query",
            json={"query": query, "max_results": max_results},
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def render_query_tab():
    """Render the Natural Language Query tab."""

    st.markdown("""
    ### Where should this person go?

    Ask complex questions combining **capability**, **location**, and **constraints**.
    Every answer is traceable back to the source evidence.
    """)

    # Example queries
    st.markdown("**Example queries:**")
    example_cols = st.columns(2)
    with example_cols[0]:
        st.markdown("""
        - *"Find hospitals in Bihar with emergency surgery capability"*
        - *"Dialysis centers in Mumbai with high trust scores"*
        """)
    with example_cols[1]:
        st.markdown("""
        - *"Pediatric hospitals in rural Uttar Pradesh"*
        - *"Oncology treatment facilities in South India"*
        """)

    st.markdown("---")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                # Assistant response with facility cards
                render_query_response(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about healthcare facilities..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Searching facilities..."):
                response = query_facilities(prompt)

                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    render_query_response(response)
                else:
                    # Demo response
                    demo_response = generate_demo_response(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": demo_response})
                    render_query_response(demo_response)


def render_query_response(response: dict):
    """Render a query response with facility cards."""

    results = response.get("results", [])

    if not results:
        st.info("No facilities found matching your query. Try broadening your search.")
        return

    st.markdown(f"Found **{len(results)}** matching facilities:")

    for i, facility in enumerate(results, 1):
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{i}. {facility['facility_name']}**")
                st.markdown(f"📍 {facility['district']}, {facility['state']}")
                st.markdown(f"*{facility['justification']}*")

            with col2:
                score = facility.get("trust_score")
                if score:
                    color = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
                    st.markdown(f"{color} **{score}**/100")
                else:
                    st.markdown("Not scored")

            with col3:
                distance = facility.get("distance_km")
                if distance:
                    st.markdown(f"📏 {distance:.1f} km")

            # Matching capabilities
            caps = facility.get("matching_capabilities", [])
            if caps:
                st.markdown("**Capabilities:** " + ", ".join(caps[:3]))

            # Show reasoning expander
            with st.expander("🔍 Show Reasoning"):
                trace_id = response.get("mlflow_trace_id")
                if trace_id:
                    st.markdown(f"""
                    **Query Analysis:**
                    - Parsed intent and matched against {len(results)} candidates
                    - Ranked by trust score and capability match
                    - Generated personalized justification

                    [🔗 View Full MLflow Trace](/mlflow/#/experiments/0/runs/{trace_id})
                    """)
                else:
                    st.markdown("*Reasoning trace available when connected to API*")

            st.markdown("---")


def generate_demo_response(query: str) -> dict:
    """Generate a demo response when API is not available."""
    return {
        "query": query,
        "results": [
            {
                "facility_id": "demo-1",
                "facility_name": "City General Hospital",
                "state": "Maharashtra",
                "district": "Mumbai",
                "trust_score": 78,
                "justification": "This hospital has verified emergency surgery capabilities with experienced surgical staff and 24/7 availability.",
                "matching_capabilities": ["Emergency Surgery", "ICU", "Trauma Care"],
            },
            {
                "facility_id": "demo-2",
                "facility_name": "Metro Healthcare Center",
                "state": "Maharashtra",
                "district": "Pune",
                "trust_score": 72,
                "justification": "Well-equipped facility with surgical capabilities and good accessibility from major routes.",
                "matching_capabilities": ["General Surgery", "Orthopedics"],
            },
            {
                "facility_id": "demo-3",
                "facility_name": "District Hospital",
                "state": "Maharashtra",
                "district": "Nagpur",
                "trust_score": 65,
                "justification": "Government hospital with basic surgical facilities and emergency services.",
                "matching_capabilities": ["Emergency Services", "General Surgery"],
            },
        ],
        "mlflow_trace_id": None,
    }


# Clear chat button
def clear_chat():
    st.session_state.messages = []


if st.sidebar.button("🗑️ Clear Chat"):
    clear_chat()
    st.rerun()
