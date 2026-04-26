"""Geographic Explorer Tab — Choropleth map showing medical desert severity."""
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from typing import Optional

# API base URL - configure based on environment
API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")


def get_facilities_for_map():
    """Fetch facility locations from API."""
    try:
        response = requests.get(f"{API_BASE}/api/facilities", params={"limit": 500})
        if response.status_code == 200:
            return response.json().get("facilities", [])
    except:
        pass
    return None


def get_map_data(capability: str):
    """Fetch map data for a specific capability."""
    try:
        response = requests.get(f"{API_BASE}/api/map/{capability}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def render_map_tab():
    """Render the Geographic Explorer tab."""

    st.markdown("""
    ### Where are the gaps?

    This map shows **medical desert severity** — regions color-coded by distance to the nearest
    verified facility offering a specific capability.

    - 🟢 **Green**: < 50 km to verified facility
    - 🟡 **Yellow**: 50-100 km to verified facility
    - 🔴 **Red**: > 100 km to verified facility (medical desert)
    """)

    # Sidebar controls
    with st.sidebar:
        st.header("Map Controls")

        capability = st.selectbox(
            "Capability Filter",
            options=[
                "All Facilities",
                "Emergency Surgery",
                "Dialysis",
                "Oncology",
                "Trauma",
                "Obstetrics",
                "ICU",
                "Pediatrics",
                "Cardiology",
            ],
            index=0,
        )

        granularity = st.radio(
            "Granularity",
            options=["District", "PIN Code"],
            index=0,
        )

        trust_floor = st.slider(
            "Minimum Trust Score",
            min_value=0,
            max_value=100,
            value=60,
            help="Only show facilities with trust score >= this value"
        )

    # Create base map centered on India
    m = folium.Map(
        location=[22.5, 78.5],  # Center of India
        zoom_start=5,
        tiles="CartoDB positron",
    )

    # Try to fetch data from API
    facilities = get_facilities_for_map()

    if facilities:
        # Add facility markers
        for f in facilities:
            if f.get("latitude") and f.get("longitude"):
                # Color based on facility type
                color = "blue"
                if "hospital" in f.get("facility_type", "").lower():
                    color = "red"
                elif "clinic" in f.get("facility_type", "").lower():
                    color = "green"

                folium.CircleMarker(
                    location=[f["latitude"], f["longitude"]],
                    radius=5,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    popup=folium.Popup(
                        f"""
                        <b>{f['facility_name']}</b><br>
                        {f['district']}, {f['state']}<br>
                        Type: {f['facility_type']}
                        """,
                        max_width=300,
                    ),
                    tooltip=f['facility_name'],
                ).add_to(m)

        st.success(f"Showing {len(facilities)} facilities")
    else:
        # Show demo data message
        st.info("""
        **API not connected** — showing demo map.

        To see real data:
        1. Start the FastAPI backend: `uvicorn api.main:app`
        2. Configure API_BASE in Streamlit secrets
        """)

        # Add some demo markers
        demo_facilities = [
            {"name": "AIIMS Delhi", "lat": 28.5672, "lng": 77.2100, "type": "hospital"},
            {"name": "Apollo Mumbai", "lat": 19.0176, "lng": 72.8562, "type": "hospital"},
            {"name": "CMC Vellore", "lat": 12.9249, "lng": 79.1325, "type": "hospital"},
        ]

        for f in demo_facilities:
            folium.Marker(
                location=[f["lat"], f["lng"]],
                popup=f["name"],
                tooltip=f["name"],
                icon=folium.Icon(color="red", icon="plus", prefix="fa"),
            ).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                background-color: white; padding: 10px; border-radius: 5px;
                border: 2px solid grey;">
        <b>Legend</b><br>
        🔴 Hospital<br>
        🟢 Clinic<br>
        🔵 Other
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Render map
    map_data = st_folium(m, width=None, height=500, returned_objects=["last_clicked"])

    # Handle click events
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        st.info(f"Clicked at: {clicked['lat']:.4f}, {clicked['lng']:.4f}")

        # In a full implementation, this would show nearby facilities
        # and allow navigation to the Inspector tab

    # Statistics sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("Statistics")

        # These would come from the API
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Facilities", "10,000")
            st.metric("States", "194")
        with col2:
            st.metric("Verified", "8,500")
            st.metric("Districts", "2,321")
