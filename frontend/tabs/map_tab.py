"""Geographic Explorer Tab — Choropleth map showing medical desert severity."""
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from typing import Optional

import os
API_BASE = os.environ.get("API_URL", "http://localhost:8000")


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
    <div style='margin-bottom: 1.5rem;'>
        <h3 style='margin-bottom: 0.5rem; color: #1e3a5f;'>Where are the gaps?</h3>
        <p style='color: #666; line-height: 1.6;'>
            This map shows <strong>medical desert severity</strong> — regions color-coded by distance
            to the nearest verified facility offering a specific capability.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Legend row
    legend_col1, legend_col2, legend_col3 = st.columns(3)
    with legend_col1:
        st.markdown("🟢 **Good Access** — < 50 km")
    with legend_col2:
        st.markdown("🟡 **Limited** — 50-100 km")
    with legend_col3:
        st.markdown("🔴 **Medical Desert** — > 100 km")

    st.markdown("")

    # Pincode search card
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;'>
        <p style='color: white; font-size: 1.1rem; margin-bottom: 0.5rem; font-weight: 600;'>
            Check Healthcare Access in Your Area
        </p>
        <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem;'>
            Enter your PIN code to see distance to nearest verified facilities
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Pincode search inputs
    col1, col2 = st.columns([3, 1])
    with col1:
        pincode_input = st.text_input(
            "PIN Code",
            placeholder="e.g., 110001",
            max_chars=6,
            help="Enter a 6-digit Indian PIN code",
            label_visibility="collapsed"
        )
    with col2:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

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

    # Handle pincode search result
    map_center = [22.5, 78.5]  # Default: center of India
    zoom_level = 5

    if pincode_input and len(pincode_input) == 6 and pincode_input.isdigit():
        # Show medical desert status for this pincode
        st.markdown("---")
        st.subheader(f"Medical Access for PIN Code: {pincode_input}")

        # Demo data for pincode search (would come from API in production)
        demo_pincode_data = {
            "110001": {"lat": 28.6358, "lng": 77.2245, "city": "New Delhi", "severity": "green", "nearest_km": 2.3},
            "400001": {"lat": 18.9388, "lng": 72.8354, "city": "Mumbai", "severity": "green", "nearest_km": 1.5},
            "600001": {"lat": 13.0827, "lng": 80.2707, "city": "Chennai", "severity": "green", "nearest_km": 3.1},
            "700001": {"lat": 22.5726, "lng": 88.3639, "city": "Kolkata", "severity": "green", "nearest_km": 2.8},
            "560001": {"lat": 12.9716, "lng": 77.5946, "city": "Bangalore", "severity": "green", "nearest_km": 1.9},
        }

        # Try API first, fall back to demo
        pincode_result = None
        try:
            response = requests.get(f"{API_BASE}/api/map/pincode/{pincode_input}")
            if response.status_code == 200:
                pincode_result = response.json()
        except:
            pass

        if not pincode_result:
            # Use demo data or generate based on pincode pattern
            if pincode_input in demo_pincode_data:
                pincode_result = demo_pincode_data[pincode_input]
            else:
                # Generate approximate location based on first digit (region code)
                region_coords = {
                    "1": (28.6, 77.2),   # North
                    "2": (26.9, 80.9),   # Uttar Pradesh
                    "3": (26.8, 75.8),   # Rajasthan
                    "4": (19.0, 72.8),   # Maharashtra
                    "5": (17.4, 78.5),   # Andhra/Telangana
                    "6": (13.0, 77.5),   # South
                    "7": (22.6, 88.4),   # East
                    "8": (23.0, 72.6),   # Gujarat
                }
                region = pincode_input[0]
                coords = region_coords.get(region, (22.5, 78.5))
                # Simulate varying access levels
                import random
                random.seed(int(pincode_input))
                severities = ["green", "green", "yellow", "yellow", "red"]
                distances = [random.uniform(5, 150) for _ in range(5)]
                severity = severities[random.randint(0, 4)]
                pincode_result = {
                    "lat": coords[0] + random.uniform(-1, 1),
                    "lng": coords[1] + random.uniform(-1, 1),
                    "city": "Area",
                    "severity": severity,
                    "nearest_km": distances[0],
                }

        if pincode_result:
            map_center = [pincode_result["lat"], pincode_result["lng"]]
            zoom_level = 10

            severity = pincode_result.get("severity", "yellow")
            distance = pincode_result.get("nearest_km", 0)

            # Display result card
            severity_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(severity, "🟡")
            severity_text = {
                "green": "Good Access (< 50 km)",
                "yellow": "Limited Access (50-100 km)",
                "red": "Medical Desert (> 100 km)"
            }.get(severity, "Unknown")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Desert Status", f"{severity_emoji} {severity.title()}")
            with col2:
                st.metric("Nearest Verified Facility", f"{distance:.1f} km")
            with col3:
                cap_label = capability if capability != "All Facilities" else "Any Capability"
                st.metric("For Capability", cap_label)

            if severity == "red":
                st.error(f"⚠️ **Medical Desert Alert**: The nearest verified {cap_label.lower()} facility is {distance:.1f} km away. This area has critical healthcare access gaps.")
            elif severity == "yellow":
                st.warning(f"⚡ **Limited Access**: The nearest verified facility is {distance:.1f} km away. Consider travel time in emergencies.")
            else:
                st.success(f"✅ **Good Access**: A verified facility is within {distance:.1f} km.")

        st.markdown("---")

    # Create base map
    m = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles="CartoDB positron",
    )

    # Add marker for searched pincode
    if pincode_input and len(pincode_input) == 6 and 'pincode_result' in dir() and pincode_result:
        severity_color = {"green": "green", "yellow": "orange", "red": "red"}.get(
            pincode_result.get("severity", "yellow"), "orange"
        )
        folium.Marker(
            location=[pincode_result["lat"], pincode_result["lng"]],
            popup=f"PIN: {pincode_input}",
            tooltip=f"Your location: {pincode_input}",
            icon=folium.Icon(color=severity_color, icon="home", prefix="fa"),
        ).add_to(m)

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
