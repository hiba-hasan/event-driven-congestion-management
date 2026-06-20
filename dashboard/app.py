import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List
import json

st.set_page_config(
    page_title="Resilient City OS",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏙️ Resilient City OS - Event-Driven Congestion Management")
st.markdown("---")

API_BASE_URL = "http://localhost:8000/api"

@st.cache_data
def fetch_summary():
    try:
        response = requests.get(f"{API_BASE_URL}/summary")
        return response.json()
    except:
        return {}

@st.cache_data
def fetch_junctions(zone=None, corridor=None):
    try:
        params = {"limit": 500}
        if zone:
            params["zone"] = zone
        if corridor:
            params["corridor"] = corridor
        response = requests.get(f"{API_BASE_URL}/junctions", params=params)
        return response.json()
    except:
        return {"junctions": []}

@st.cache_data
def fetch_clusters():
    try:
        response = requests.get(f"{API_BASE_URL}/clusters")
        return response.json()
    except:
        return {}

@st.cache_data
def fetch_learning_failures():
    try:
        response = requests.get(f"{API_BASE_URL}/learning-failures", params={"limit": 100})
        return response.json()
    except:
        return {"failures": []}

@st.cache_data
def fetch_junction_details(junction_name):
    try:
        response = requests.get(f"{API_BASE_URL}/junction/{junction_name}")
        return response.json()
    except:
        return {}

summary = fetch_summary()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Junctions", summary.get('total_junctions', 0))
with col2:
    st.metric("Event Clusters", summary.get('total_clusters', 0))
with col3:
    st.metric("Resilient", summary.get('resilient_junctions', 0))
with col4:
    st.metric("Fragile", summary.get('fragile_junctions', 0))
with col5:
    st.metric("Avg Resilience", f"{summary.get('avg_resilience_score', 0):.2f}")

st.markdown("---")

tabs = st.tabs(["🗺️ Resilience Map", "🧬 Event Archetypes", "⚠️ Learning Failures", "🚦 Response Planner"])

with tabs[0]:
    st.subheader("Junction Resilience Scores")
    st.markdown("Junctions colored by their ability to recover from traffic events. Green = Resilient, Red = Fragile")

    col1, col2 = st.columns([3, 1])
    with col1:
        zone_filter = st.multiselect("Filter by Zone", ["All"], default=["All"])
    with col2:
        sort_by = st.selectbox("Sort by", ["resilience", "recovery_time", "events"])

    junctions_data = fetch_junctions()
    junctions = junctions_data.get('junctions', [])

    if junctions:
        df_junctions = pd.DataFrame(junctions)
        df_junctions['color'] = df_junctions['resilience_score'].apply(
            lambda x: 'red' if x < 0.3 else 'orange' if x < 0.5 else 'yellow' if x < 0.7 else 'lightgreen' if x < 0.85 else 'green'
        )

        fig = go.Figure(data=[
            go.Bar(
                x=df_junctions.head(20)['junction_name'],
                y=df_junctions.head(20)['resilience_score'],
                marker_color=df_junctions.head(20)['color'],
                text=df_junctions.head(20)['resilience_score'].round(3),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Resilience: %{y:.3f}<extra></extra>'
            )
        ])
        fig.update_layout(
            title="Top 20 Junctions by Resilience Score",
            xaxis_title="Junction",
            yaxis_title="Resilience Score (0-1)",
            height=500,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Resilience Distribution")
        fig_hist = px.histogram(
            df_junctions,
            x='resilience_score',
            nbins=20,
            title="Distribution of Resilience Scores",
            color_discrete_sequence=['#1f77b4']
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        with st.expander("View All Junctions Table"):
            st.dataframe(
                df_junctions[['junction_name', 'resilience_score', 'resilience_category', 'avg_recovery_hours', 'event_count', 'primary_zone']].head(100),
                use_container_width=True,
                height=600
            )

with tabs[1]:
    st.subheader("Event DNA Archetypes")
    st.markdown("Clusters of similar events that create predictable traffic impacts")

    try:
        with open('results/cluster_profiles.json') as f:
            clusters = json.load(f)

        col1, col2 = st.columns([2, 1])
        with col1:
            selected_clusters = st.multiselect(
                "Select Clusters to View",
                list(clusters.keys()),
                default=list(clusters.keys())[:3]
            )
        with col2:
            st.write("")  # Spacer

        for cluster_id in selected_clusters:
            if cluster_id in clusters:
                cluster = clusters[cluster_id]
                with st.expander(f"Cluster {cluster_id}: {cluster.get('dominant_event_type')} ({cluster.get('event_count')} events)", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Events", cluster.get('event_count'))
                    with col2:
                        st.metric("Avg Recovery (h)", f"{cluster.get('avg_recovery_hours', 0):.1f}")
                    with col3:
                        st.metric("Event Type", cluster.get('dominant_event_type'))
                    with col4:
                        st.metric("Priority", cluster.get('dominant_priority'))

                    st.markdown("**Characteristics:**")
                    st.write(f"- Primary Corridor: {cluster.get('dominant_corridor')}")
                    st.write(f"- Primary Zone: {cluster.get('dominant_zone')}")
                    st.write(f"- Event Causes: {', '.join(cluster.get('event_causes', [])[:3])}")

                    affected_junctions = cluster.get('affected_junctions', [])
                    st.markdown(f"**Affected Junctions ({len(affected_junctions)} total):**")
                    st.write(", ".join(affected_junctions[:10]))
                    if len(affected_junctions) > 10:
                        st.write(f"... and {len(affected_junctions) - 10} more")

    except Exception as e:
        st.error(f"Error loading clusters: {e}")

with tabs[2]:
    st.subheader("Institutional Learning Failures")
    st.markdown("Junctions where similar events have wildly different recovery times, indicating the city is not learning from past events")

    failures_data = fetch_learning_failures()
    failures = failures_data.get('failures', [])

    if failures:
        df_failures = pd.DataFrame(failures)

        severity_filter = st.selectbox("Filter by Severity", ["All", "Critical", "High"])
        if severity_filter != "All":
            df_failures = df_failures[df_failures['severity'] == severity_filter]

        if len(df_failures) > 0:
            fig_cv = px.bar(
                df_failures.head(15),
                x='junction_name',
                y='coefficient_of_variation',
                color='severity',
                color_discrete_map={'Critical': 'red', 'High': 'orange'},
                title="Top Learning Failures by Coefficient of Variation",
                labels={'coefficient_of_variation': 'Variation in Recovery Time', 'junction_name': 'Junction'}
            )
            fig_cv.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_cv, use_container_width=True)

            st.subheader("Detailed Failures")
            with st.expander("View All Learning Failures"):
                st.dataframe(
                    df_failures[['junction_name', 'cluster_id', 'event_type', 'coefficient_of_variation', 'severity', 'event_count']],
                    use_container_width=True,
                    height=500
                )
        else:
            st.info("No learning failures found for selected severity level")
    else:
        st.info("No learning failures detected in this data")

with tabs[3]:
    st.subheader("🚦 Response Planner")
    st.markdown("Transform historical data into actionable operational recommendations for managing event-driven traffic impact")

    # HELPER FUNCTIONS FOR RESPONSE PLANNER

    def load_clusters():
        try:
            with open('results/cluster_profiles.json') as f:
                return json.load(f)
        except:
            return {}

    def load_learning_failures():
        try:
            with open('results/learning_failures.json') as f:
                return json.load(f)
        except:
            return {"failures": []}

    def map_event_cause(cause):
        """Map specific causes to broader categories for matching"""
        cause_mapping = {
            "festival": "public_event",
            "political_rally": "procession",
            "sports_event": "public_event",
            "sudden_gathering": "procession"
        }
        return cause_mapping.get(cause, cause)

    def determine_event_type(cause):
        """Determine if event is planned or unplanned based on cause"""
        planned_causes = ["construction", "public_event", "procession", "sports_event", "festival", "political_rally"]
        return "planned" if cause in planned_causes else "unplanned"

    def get_zones_from_clusters(clusters):
        """Extract unique zones from cluster profiles"""
        zones = set()
        for cluster in clusters.values():
            zone = cluster.get('dominant_zone')
            if zone:
                zones.add(zone)
        return sorted(list(zones))

    def calculate_event_dna_similarity(event_cause, zone, priority, clusters):
        """
        Calculate similarity score to find closest matching cluster.
        Weighted scoring: cause_match=40, zone_match=30, priority_match=20, planned_match=10
        """
        event_type = determine_event_type(event_cause)
        mapped_cause = map_event_cause(event_cause)

        best_score = -1
        best_cluster_id = None

        for cluster_id, cluster in clusters.items():
            score = 0

            # Cause matching (40 points)
            cluster_causes = cluster.get('event_causes', [])
            if any(cause in cluster_causes for cause in [event_cause, mapped_cause]):
                score += 40
            elif cluster_causes:  # Partial credit for any event type match
                score += 10

            # Zone matching (30 points)
            if cluster.get('dominant_zone') == zone:
                score += 30

            # Priority matching (20 points)
            cluster_priority = cluster.get('dominant_priority', 'Low')
            if (priority == "High" and cluster_priority == "High") or \
               (priority == "Low" and cluster_priority == "Low"):
                score += 20
            elif cluster_priority == "High" and priority == "Low":
                score += 5  # Partial credit

            # Event type matching (10 points)
            if event_type == cluster.get('dominant_event_type'):
                score += 10

            if score > best_score:
                best_score = score
                best_cluster_id = cluster_id

        confidence = (best_score / 100) if best_score >= 0 else 0
        return best_cluster_id, best_score, confidence

    def get_cluster_failures(cluster_id, failures_data):
        """Get learning failures associated with a cluster"""
        failures = failures_data.get('failures', [])
        cluster_failures = [f for f in failures if f.get('cluster_id') == int(cluster_id)]
        return cluster_failures

    def has_critical_failures(cluster_failures):
        """Check if cluster has critical severity failures"""
        return any(f.get('severity') == 'Critical' for f in cluster_failures)

    def has_high_failures(cluster_failures):
        """Check if cluster has high severity failures"""
        return any(f.get('severity') == 'High' for f in cluster_failures)

    def calculate_police_deployment(recovery_hours, affected_junctions, learning_penalty):
        """
        Calculate recommended police officers based on:
        - Recovery hours
        - Number of affected junctions
        - Learning failure severity penalty
        """
        officers = 2 + (recovery_hours / 100) + (affected_junctions / 10) + learning_penalty
        return max(round(officers), 2)

    def calculate_barricades(road_closure, affected_junctions, recovery_hours):
        """
        Calculate recommended barricades based on:
        - Road closure requirement
        - Number of affected junctions
        - Recovery time
        """
        barricades = 0
        if road_closure == "Yes":
            barricades += 2
        if affected_junctions > 20:
            barricades += 1
        if recovery_hours > 300:
            barricades += 1
        return barricades

    def get_institutional_warning(cluster_failures):
        """Generate institutional warning based on learning failure severity"""
        if has_critical_failures(cluster_failures):
            return "critical", "⚠️ Historical responses for similar events have been inconsistent.\n\nRecommendation: Follow standardized playbooks and deploy experienced coordinators."
        elif has_high_failures(cluster_failures):
            return "high", "⚠️ Moderate institutional learning gaps detected.\n\nRecommendation: Review past incident reports and ensure team awareness."
        else:
            return "none", "✓ Historical responses have been consistent."

    # LOAD DATA
    clusters = load_clusters()
    failures_data = load_learning_failures()
    zones = get_zones_from_clusters(clusters)

    #SECTION 1: EVENT INPUTS
    st.markdown("### 1. Event Inputs")
    st.markdown("Provide details about the upcoming or current event")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        event_cause = st.selectbox(
            "Event Cause",
            ["construction", "public_event", "procession", "sports_event",
             "festival", "political_rally", "sudden_gathering"]
        )
    with col2:
        zone = st.selectbox("Zone", zones) if zones else st.selectbox("Zone", ["Central Zone 2"])
    with col3:
        priority = st.selectbox("Priority", ["High", "Low"])
    with col4:
        road_closure = st.selectbox("Requires Road Closure", ["Yes", "No"])

    #SECTION 2: EVENT DNA MATCHING
    st.markdown("---")
    st.markdown("### 2. Closest Event DNA Archetype")

    # Calculate similarity
    cluster_id, similarity_score, confidence = calculate_event_dna_similarity(event_cause, zone, priority, clusters)

    if cluster_id is not None:
        matched_cluster = clusters.get(str(cluster_id), {})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Closest Archetype", f"Cluster {cluster_id}")
        with col2:
            st.metric("Similarity Score", f"{similarity_score}/100")
        with col3:
            st.metric("Confidence", f"{confidence*100:.0f}%")
    else:
        st.warning("No matching cluster found")
        matched_cluster = {}

    # SECTION 3: PREDICTED IMPACT
    st.markdown("---")
    st.markdown("### 3. Predicted Impact")

    if matched_cluster:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Cluster ID", matched_cluster.get('cluster_id'))
        with col2:
            st.metric("Expected Recovery (h)", f"{matched_cluster.get('avg_recovery_hours', 0):.1f}")
        with col3:
            st.metric("Primary Corridor", matched_cluster.get('dominant_corridor', 'N/A'))
        with col4:
            st.metric("Primary Zone", matched_cluster.get('dominant_zone', 'N/A'))
        with col5:
            affected_junctions = matched_cluster.get('affected_junctions', [])
            st.metric("Affected Junctions", len(affected_junctions))

        st.markdown("**Event Characteristics:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- **Priority:** {matched_cluster.get('dominant_priority')}")
            st.write(f"- **Event Type:** {matched_cluster.get('dominant_event_type').title()}")
        with col2:
            event_causes = matched_cluster.get('event_causes', [])
            st.write(f"- **Event Causes:** {', '.join(event_causes) if event_causes else 'N/A'}")

    #SECTION 4: OPERATIONAL RECOMMENDATIONS
    st.markdown("---")
    st.markdown("### 4. Operational Recommendations")

    if matched_cluster:
        recovery_hours = matched_cluster.get('avg_recovery_hours', 0)
        affected_junctions_list = matched_cluster.get('affected_junctions', [])
        num_affected_junctions = len(affected_junctions_list)

        # Get learning failures for this cluster
        cluster_failures = get_cluster_failures(cluster_id, failures_data)

        # Calculate learning penalty
        learning_penalty = 0
        if has_critical_failures(cluster_failures):
            learning_penalty = 3
        elif has_high_failures(cluster_failures):
            learning_penalty = 1

        # Recommendations
        officers = calculate_police_deployment(recovery_hours, num_affected_junctions, learning_penalty)
        barricades = calculate_barricades(road_closure, num_affected_junctions, recovery_hours)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🚔 Recommended Officers", officers)
        with col2:
            coordinator_needed = learning_penalty >= 3
            st.metric(
                "👮 Traffic Coordinator",
                "Senior ⭐" if coordinator_needed else "Standard"
            )
        with col3:
            st.metric("🚧 Barricades Required", barricades)
        with col4:
            primary_corridor = matched_cluster.get('dominant_corridor', 'Non-corridor')
            if primary_corridor != "Non-corridor":
                st.metric("🚦 Diversion", "Required")
            else:
                st.metric("🚦 Diversion", "Localized")

        # Detailed recommendations
        st.markdown("**Detailed Recommendations:**")

        st.markdown(f"**Police Deployment:** Deploy **{officers} officers** for this event.")
        st.caption(f"Based on recovery hours ({recovery_hours:.1f}h), affected junctions ({num_affected_junctions}), and institutional learning penalty")

        if coordinator_needed:
            st.markdown("**🌟 Deploy Senior Traffic Coordinator** - Historical responses for similar events have shown inconsistency")
        else:
            st.markdown("**Standard Supervision** - Coordinate through standard traffic management channels")

        st.markdown(f"**Barricade Deployment:** Set up **{barricades} barricade units**")
        st.caption(f"Road closure: {'Yes' if road_closure == 'Yes' else 'No'} | Junctions affected: {num_affected_junctions} | Recovery hours: {recovery_hours:.1f}h")

        primary_corridor = matched_cluster.get('dominant_corridor', 'Non-corridor')
        if primary_corridor != "Non-corridor":
            st.markdown(f"**Diversion Required:** Avoid **{primary_corridor}** corridor. Use neighboring corridors for traffic diversion.")
        else:
            st.markdown("**Localized Diversion Recommended:** Manage traffic within immediate vicinity.")

    #SECTION 5: INSTITUTIONAL LEARNING WARNING
    st.markdown("---")
    st.markdown("### 5. Institutional Learning Warning")

    if matched_cluster:
        cluster_failures = get_cluster_failures(cluster_id, failures_data)
        severity, warning_message = get_institutional_warning(cluster_failures)

        if severity == "critical":
            st.error(warning_message)
        elif severity == "high":
            st.warning(warning_message)
        else:
            st.success(warning_message)

    #SECTION 6: CONFIDENCE SCORE
    st.markdown("---")
    st.markdown("### 6. Recommendation Confidence")

    if cluster_id is not None:
        confidence_pct = confidence * 100

        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(confidence)
        with col2:
            st.metric("Score", f"{confidence_pct:.0f}%")

        if confidence >= 0.8:
            st.success("✓ High confidence in recommendations")
        elif confidence >= 0.5:
            st.info("~ Medium confidence - verify with recent data")
        else:
            st.warning("⚠ Low confidence - use caution with recommendations")

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**Resilient City OS** - An event-driven congestion management system using:

1. **Event DNA Clustering** - Groups similar events into archetypes
2. **Resilience Scoring** - Measures junction recovery ability
3. **Learning Failure Detection** - Identifies institutional memory gaps

This system helps cities forecast event-related traffic impacts and optimize resource deployment.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**API Endpoint:** `http://localhost:8000/api`")
