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
def fetch_data_quality():
    try:
        response = requests.get(f"{API_BASE_URL}/data-quality")
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

# Show data quality warning if needed
data_quality = fetch_data_quality()
if data_quality and data_quality.get('unknown_junction', {}).get('percentage', 0) > 30:
    st.warning(
        f"⚠️ **Data Quality Note:** {data_quality.get('unknown_junction', {}).get('percentage', 0):.1f}% of records lack junction information. "
        f"Operational recommendations exclude these records. "
        f"[View audit](/api/data-quality)"
    )

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
                        st.metric("Operational Duration (h)",f"{cluster.get('avg_recovery_hours', 0):.1f}")
                        st.caption("Represents the historical operational duration associated with similar disruption archetypes. "
                        "For planned events, this may reflect scheduled event duration; for incidents, it may reflect resolution periods."
                        )
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
    st.subheader("Institutional Learning DashBoard")
    st.markdown("Junctions where similar events have wildly different recovery times, indicating the city is not learning from past events")

    failures_data = fetch_learning_failures()
    failures = failures_data.get('failures', [])

    # =========================================================================
    # 🧠 INSTITUTIONAL MEMORY REPORT
    # Computed entirely from existing artifacts — no new ML, no pipeline rerun.
    # Mirrors Phase 1 Unknown_Junction exclusion for consistency.
    # =========================================================================
    st.markdown("### 🧠 Institutional Memory Report")
    st.markdown(
        "An executive summary of what Bengaluru's traffic network has **learned** — "
        "and where it continues to struggle — across **2,195 historical disruption events**."
    )

    # Load junction scores for mastered-playbook computation
    try:
        with open('results/junction_scores.json') as _f:
            _junction_scores = json.load(_f)
    except Exception:
        _junction_scores = {}

    # Build working sets ─ consistent with Phase 1 Unknown_Junction exclusion
    _failed_junctions = {
        r['junction_name'] for r in failures
        if r['junction_name'] != 'Unknown_Junction'
    }
    _all_clean = {
        k: v for k, v in _junction_scores.items()
        if k != 'Unknown_Junction'
    }

    # Mastered: ≥3 events and never flagged as a learning failure
    _mastered = sorted(
        [v for k, v in _all_clean.items()
         if k not in _failed_junctions and v.get('event_count', 0) >= 3],
        key=lambda x: x['event_count'],
        reverse=True
    )

    # Persistent gaps: failure records excluding Unknown_Junction, ranked by CV
    _gap_records = sorted(
        [r for r in failures if r['junction_name'] != 'Unknown_Junction'],
        key=lambda x: x['coefficient_of_variation'],
        reverse=True
    )

    # Derived executive metrics
    _total_clean   = len(_all_clean)
    _mastered_count = len(_mastered)
    _gap_count     = len({r['junction_name'] for r in _gap_records})
    _stable_pct    = round(_mastered_count / _total_clean * 100, 1) if _total_clean else 0
    _total_events  = sum(v.get('event_count', 0) for v in _all_clean.values())
    _gap_events    = sum(
        _all_clean[j]['event_count']
        for j in _failed_junctions
        if j in _all_clean
    )
    _avg_cv_gaps   = round(
        sum(r['coefficient_of_variation'] for r in _gap_records) / len(_gap_records), 2
    ) if _gap_records else 0

    # ── EXECUTIVE METRICS ROW ─────────────────────────────────────────────
    _mc1, _mc2, _mc3, _mc4 = st.columns(4)
    with _mc1:
        st.metric(
            "✅ Mastered Junctions", _mastered_count,
            help="Junctions with ≥3 events and no detected response inconsistency (CV < 0.5 threshold)"
        )
    with _mc2:
        st.metric(
            "⚠️ Persistent Gaps", _gap_count,
            help="Junctions where similar events produce widely different recovery outcomes"
        )
    with _mc3:
        st.metric(
            "📋 Stable Playbook Coverage", f"{_stable_pct}%",
            help="Proportion of analysed junctions (≥3 events) with consistent operational responses"
        )
    with _mc4:
        st.metric(
            "📊 Events Analysed", f"{_total_events:,}",
            help="Total historical disruption events across all clean (non-Unknown) junctions"
        )

    st.markdown("")

    # ── KEY FINDING CALLOUT ───────────────────────────────────────────────
    st.info(
        f"🔍 **Key Finding:** **{_gap_count} junctions** have never achieved a consistent operational "
        f"response across similar disruptions — showing an average response variability of "
        f"**{_avg_cv_gaps}×** against an operational target of <0.5×. "
        f"These junctions collectively account for **{_gap_events} historical events**, "
        f"representing the highest-priority target for standardised playbook intervention."
    )

    st.markdown("")

    # ── MASTERED PLAYBOOKS  |  PERSISTENT GAPS (two-column layout) ────────
    _left_col, _right_col = st.columns(2)

    with _left_col:
        st.markdown("#### ✅ Mastered Playbooks")
        st.caption(
            "These junctions show stable response behaviour across similar events. "
            "They can serve as reference templates when building response playbooks for new personnel."
        )
        if _mastered:
            for _j in _mastered[:5]:
                _jname  = _j['junction_name']
                _jevts  = _j.get('event_count', 0)
                _jres   = _j.get('resilience_score', 0)
                _rlabel = "High" if _jres >= 0.7 else "Moderate" if _jres >= 0.4 else "Low"
                _rclr   = "#27ae60" if _jres >= 0.7 else "#f39c12" if _jres >= 0.4 else "#e74c3c"
                st.markdown(
                    f'<div style="border-left:4px solid #27ae60; padding:8px 12px; '
                    f'margin-bottom:8px; background:#0a1f12; border-radius:0 6px 6px 0;">'
                    f'<span style="font-weight:700;color:#f0f0f0;">{_jname}</span><br>'
                    f'<span style="color:#aab;font-size:0.82em;">'
                    f'📊 {_jevts} events &nbsp;|&nbsp; Resilience: '
                    f'<span style="color:{_rclr};font-weight:600;">{_rlabel} ({_jres:.2f})</span>'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            if len(_mastered) > 5:
                st.caption(f"… and {len(_mastered) - 5} more junctions with stable playbooks.")
        else:
            st.info("Insufficient data to identify mastered junctions.")

    with _right_col:
        st.markdown("#### ⚠️ Persistent Operational Gaps")
        st.caption(
            "These junctions continue to exhibit inconsistent responses across similar disruptions "
            "and should be prioritised for targeted playbook development."
        )
        if _gap_records:
            for _r in _gap_records[:5]:
                _rname   = _r['junction_name']
                _rcv     = _r['coefficient_of_variation']
                _revts   = _r['event_count']
                _rsev    = _r['severity']
                _sclr    = "#e74c3c" if _rsev == "Critical" else "#e67e22"
                _sborder = "#c0392b" if _rsev == "Critical" else "#d35400"
                _sbg     = "#1f0a0a" if _rsev == "Critical" else "#1f150a"
                st.markdown(
                    f'<div style="border-left:4px solid {_sborder}; padding:8px 12px; '
                    f'margin-bottom:8px; background:{_sbg}; border-radius:0 6px 6px 0;">'
                    f'<span style="font-weight:700;color:#f0f0f0;">{_rname}</span><br>'
                    f'<span style="color:#aab;font-size:0.82em;">'
                    f'CV: <span style="color:{_sclr};font-weight:700;">{_rcv:.2f}×</span>'
                    f' &nbsp;|&nbsp; {_revts} events'
                    f' &nbsp;|&nbsp; <span style="color:{_sclr};">{_rsev}</span>'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No persistent gap junctions detected in clean data.")

    # ── WHY THIS MATTERS ──────────────────────────────────────────────────
    st.markdown("")
    with st.expander("📌 Why This Matters", expanded=True):
        st.markdown(
            """
Traffic management systems typically respond to disruptions without systematically capturing
institutional knowledge. Each event is handled in isolation — there is no feedback loop
connecting past responses to future decisions.

**This system changes that.**

By tracking response variability (Coefficient of Variation) across recurring event archetypes,
it identifies:

- 🟢 **Where operational knowledge has stabilised** — junctions where responders have implicitly
  developed reliable playbooks through repeated experience
- 🔴 **Where it has not** — junctions where identical disruption types produce wildly different
  recovery outcomes, signalling a failure to institutionalise learning

The goal is not to replace experienced traffic controllers.
It is to make their institutional knowledge **explicit, transferable, and improvable** —
so that every officer benefits from the city's collective experience, not just the veterans.
"""
        )
        if _gap_events > 0:
            st.markdown(
                f"**Priority Intervention Targets:** The **{_gap_count} persistent-gap junctions** "
                f"account for **{_gap_events} historical events**. Standardising response "
                f"playbooks at these locations — using mastered junctions as reference templates — "
                f"represents the most immediate, evidence-based opportunity for measurable "
                f"improvement in the city's operational resilience.\n\n"
                f"*Assumption: playbook standardisation does not guarantee CV improvement; "
                f"actual outcomes depend on implementation quality and field conditions.*"
            )

    st.markdown("---")
    st.markdown("#### 📉 Response Variability Analysis")
    st.markdown("Detailed breakdown of junctions where institutional learning has not yet stabilised.")

    # =========================================================================
    # EXISTING CONTENT — unchanged below
    # =========================================================================
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
                title="Highest Priority Intervention Junctions",
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
    
    def get_all_dataset_zones():
        """Return all operational zones present in the Astram dataset"""
        return [
            "Central Zone 1",
            "Central Zone 2",
            "East Zone 1",
            "East Zone 2",
            "North Zone 1",
            "North Zone 2",
            "South Zone 1",
            "South Zone 2",
            "West Zone 1",
            "West Zone 2"
        ]

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
        - Recovery hours (1 officer per ~100 hours)
        - Number of affected junctions (1 officer per ~10 junctions)
        - Learning failure severity penalty
        Returns: (total_officers, breakdown_dict)
        """
        base = 2
        recovery_component = recovery_hours / 100
        junction_component = affected_junctions / 10

        total = base + recovery_component + junction_component + learning_penalty
        officers = max(round(total), 2)

        breakdown = {
            'base': base,
            'recovery': round(recovery_component, 1),
            'junctions': round(junction_component, 1),
            'learning_penalty': round(learning_penalty, 1),
            'total': round(total, 1),
            'recommended': officers,
        }

        return officers, breakdown

    def calculate_barricades(road_closure, affected_junctions, recovery_hours):
        """
        Calculate recommended barricades based on:
        - Road closure requirement (+2)
        - Number of affected junctions (>20: +1)
        - Recovery time (>300h: +1)
        Returns: (total_barricades, breakdown_dict)
        """
        breakdown = {
            'rules': []
        }

        barricades = 0

        # Rule 1: Road closure
        if road_closure == "Yes":
            barricades += 2
            breakdown['rules'].append({'rule': 'Road closure', 'value': 2, 'applied': True})
        else:
            breakdown['rules'].append({'rule': 'Road closure', 'value': 0, 'applied': False})

        # Rule 2: Affected junctions
        if affected_junctions > 20:
            barricades += 1
            breakdown['rules'].append({
                'rule': f'Affected junctions > 20 ({affected_junctions})',
                'value': 1,
                'applied': True
            })
        else:
            breakdown['rules'].append({
                'rule': f'Affected junctions ≤ 20 ({affected_junctions})',
                'value': 0,
                'applied': False
            })

        # Rule 3: Recovery time
        if recovery_hours > 300:
            barricades += 1
            breakdown['rules'].append({
                'rule': f'Recovery hours > 300 ({recovery_hours:.1f}h)',
                'value': 1,
                'applied': True
            })
        else:
            breakdown['rules'].append({
                'rule': f'Recovery hours ≤ 300 ({recovery_hours:.1f}h)',
                'value': 0,
                'applied': False
            })

        breakdown['total'] = barricades

        return barricades, breakdown

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

    # ---------------------------------------------------------------------------
    # SEEDED UPCOMING EVENTS
    # Grounded in actual dataset event types and Astram zone names.
    # These act as proactive "intelligence feed" — no new ML required.
    # ---------------------------------------------------------------------------
    SEEDED_EVENTS = [
        {
            "title": "Political Rally",
            "location": "North Zone 1",
            "emoji": "📢",
            "event_cause": "political_rally",
            "zone": "North Zone 1",
            "priority": "High",
            "road_closure": "Yes",
            "time": "14:00 – 18:00",
            "duration": "~4 hrs",
            "risk": "High",
            "risk_emoji": "🔴",
            "risk_bg": "#c0392b",
            "description": "Large political gathering expected near Central Junction. High crowd density, road closure likely.",
        },
        {
            "title": "Religious Festival",
            "location": "South Zone 2",
            "emoji": "🪔",
            "event_cause": "festival",
            "zone": "South Zone 2",
            "priority": "Low",
            "road_closure": "No",
            "time": "09:00 – 15:00",
            "duration": "~6 hrs",
            "risk": "Moderate",
            "risk_emoji": "🟡",
            "risk_bg": "#b7950b",
            "description": "Annual procession through arterial roads. Partial crowd spillover and localised slow-downs anticipated.",
        },
        {
            "title": "Road Construction",
            "location": "East Zone 1",
            "emoji": "🚧",
            "event_cause": "construction",
            "zone": "East Zone 1",
            "priority": "High",
            "road_closure": "Yes",
            "time": "06:00 – 20:00",
            "duration": "All day",
            "risk": "High",
            "risk_emoji": "🔴",
            "risk_bg": "#c0392b",
            "description": "Scheduled flyover construction causing full lane closure on a major corridor.",
        },
    ]

    # ---------------------------------------------------------------------------
    # SESSION STATE — drives selectbox pre-population when a card is clicked
    # ---------------------------------------------------------------------------
    _ALL_CAUSES = ["construction", "public_event", "procession", "sports_event",
                   "festival", "political_rally", "sudden_gathering"]

    if "planner_cause" not in st.session_state:
        st.session_state.planner_cause = _ALL_CAUSES[0]
        st.session_state.planner_zone = zones[0] if zones else "Central Zone 1"
        st.session_state.planner_priority = "High"
        st.session_state.planner_road_closure = "No"
        st.session_state.planner_preset_name = None

    # ---------------------------------------------------------------------------
    # SECTION 0: TODAY'S UPCOMING EVENTS (Forecast Card panel)
    # ---------------------------------------------------------------------------
    st.markdown("### Event Twin Simulator")
    st.markdown(
        "Proactively flagged disruptions based on historical archetypes. "
        "Click **Generate Playbook** on any event to instantly load a full operational response plan."
    )

    card_cols = st.columns(3)
    for _i, _evt in enumerate(SEEDED_EVENTS):
        with card_cols[_i]:
            # Card body — styled HTML for visual impact
            st.markdown(
                f"""
<div style="
    border: 1px solid #2c2c3e;
    border-radius: 12px;
    padding: 18px 16px 14px 16px;
    background: linear-gradient(145deg, #1a1a2e, #16213e);
    min-height: 230px;
    display: flex;
    flex-direction: column;
    gap: 4px;
">
    <div style="font-size: 1.6em; line-height: 1;">{_evt['emoji']}</div>
    <div style="font-weight: 700; font-size: 1.05em; color: #f0f0f0; margin-top: 6px;">
        {_evt['title']}
    </div>
    <div style="color: #8899aa; font-size: 0.83em;">📍 {_evt['location']}</div>
    <div style="color: #aabbcc; font-size: 0.82em;">🕐 {_evt['time']}</div>
    <div style="color: #aabbcc; font-size: 0.82em;">⏱️ Duration: {_evt['duration']}</div>
    <div style="margin-top: 8px;">
        <span style="
            background: {_evt['risk_bg']};
            color: white;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 0.78em;
            font-weight: 700;
            letter-spacing: 0.03em;
        ">{_evt['risk_emoji']} {_evt['risk']} Risk</span>
    </div>
    <div style="color: #99aabb; font-size: 0.8em; margin-top: 8px; line-height: 1.4;">
        {_evt['description']}
    </div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.write("")  # vertical breathing room before button
            if st.button("📋 Generate Playbook", key=f"preset_btn_{_i}", use_container_width=True):
                # Resolve zone: fall back to first available if preset zone not in cluster zones
                _zone_list = zones if zones else ["Central Zone 1"]
                _resolved_zone = _evt["zone"] if _evt["zone"] in _zone_list else _zone_list[0]
                st.session_state.planner_cause = _evt["event_cause"]
                st.session_state.planner_zone = _resolved_zone
                st.session_state.planner_priority = _evt["priority"]
                st.session_state.planner_road_closure = _evt["road_closure"]
                st.session_state.planner_preset_name = _evt["title"]
                st.rerun()

    # Confirmation banner shown after a preset is loaded
    if st.session_state.planner_preset_name:
        st.success(
            f"✅ Playbook pre-loaded for **{st.session_state.planner_preset_name}** — "
            f"inputs are auto-populated below. Review and scroll down for recommendations."
        )

    st.markdown("---")

    # ---------------------------------------------------------------------------
    #SECTION 1: EVENT INPUTS
    # ---------------------------------------------------------------------------
    st.markdown("### 1. Event Inputs")
    st.markdown("Provide details about the upcoming or current event")

    # Selectboxes use index= so session state can pre-populate them when a
    # Forecast Card button is clicked. All existing downstream logic is unchanged.
    _zone_list = zones if zones else ["Central Zone 2"]
    _cause_idx = _ALL_CAUSES.index(st.session_state.planner_cause) \
        if st.session_state.planner_cause in _ALL_CAUSES else 0
    _zone_idx = _zone_list.index(st.session_state.planner_zone) \
        if st.session_state.planner_zone in _zone_list else 0
    _priority_list = ["High", "Low"]
    _priority_idx = _priority_list.index(st.session_state.planner_priority) \
        if st.session_state.planner_priority in _priority_list else 0
    _closure_list = ["Yes", "No"]
    _closure_idx = _closure_list.index(st.session_state.planner_road_closure) \
        if st.session_state.planner_road_closure in _closure_list else 1

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        event_cause = st.selectbox(
            "Event Cause",
            _ALL_CAUSES,
            index=_cause_idx,
        )
    with col2:
        zone = st.selectbox(
            "Zone",
            _zone_list,
            index=_zone_idx,
        )
        st.caption("Operational zones sourced from the Astram Bengaluru dataset.")
    with col3:
        priority = st.selectbox("Priority", _priority_list, index=_priority_idx)
    with col4:
        road_closure = st.selectbox("Requires Road Closure", _closure_list, index=_closure_idx)

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
        col1, col2, col3, col4, col5  = st.columns(5)
        with col1:
            archetype_name = matched_cluster.get(
                "archetype_name",
                f"Cluster {matched_cluster.get('cluster_id')}"
            )

            st.metric(
                "Closest Event Archetype",
                archetype_name
            )


        with col2:
            affected_junctions = matched_cluster.get('affected_junctions', [])
            junction_count = len(affected_junctions)

            if junction_count >= 30:
                impact_level = "🔴 Severe"
            elif junction_count >= 15:
                impact_level = "🟠 Moderate"
            else:
                impact_level = "🟢 Localized"

            st.metric(
                "Historical Impact Level",
                impact_level
            )


        with col3:
            st.metric(
                "Primary Corridor",
                matched_cluster.get('dominant_corridor', 'N/A')
            )


        with col4:
            st.metric(
                "Primary Zone",
                matched_cluster.get('dominant_zone', 'N/A')
            )


        with col5:
            st.metric(
                "Historically Affected Junctions",
                junction_count
            )
        
        st.caption(
    "Impact estimates are derived from historical events with similar "
    "characteristics. Junction counts represent locations historically "
    "affected by comparable disruptions and should be interpreted as "
    "decision-support indicators rather than deterministic forecasts."
)

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
        officers, officers_breakdown = calculate_police_deployment(recovery_hours, num_affected_junctions, learning_penalty)
        barricades, barricades_breakdown = calculate_barricades(road_closure, num_affected_junctions, recovery_hours)

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

        # Police deployment with breakdown
        st.markdown(f"**🚔 Police Deployment:** {officers} officers")
        with st.expander("📊 View calculation breakdown", expanded=False):
            st.markdown("**Formula:** Base + Recovery Component + Junction Component + Learning Penalty")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Base", officers_breakdown['base'])
            with col2:
                st.metric("Recovery", f"{officers_breakdown['recovery']:.1f}")
            with col3:
                st.metric("Junctions", f"{officers_breakdown['junctions']:.1f}")
            with col4:
                st.metric("Learning", f"{officers_breakdown['learning_penalty']:.1f}")
            with col5:
                st.metric("Total", f"{officers_breakdown['total']:.1f}→{officers}")
            st.caption(
                f"Operational Duration: {recovery_hours:.1f}h ÷ 100 | "
                f"Junctions: {num_affected_junctions} ÷ 10 | "
                f"Learning Penalty: {'Critical' if learning_penalty >= 3 else 'High' if learning_penalty >= 1 else 'None'}"
            )

        if coordinator_needed:
            st.markdown("**👮 Deploy Senior Traffic Coordinator** - Historical responses for similar events have shown inconsistency")
        else:
            st.markdown("**Standard Supervision** - Coordinate through standard traffic management channels")

        # Barricades with breakdown
        st.markdown(f"**🚧 Barricades Required:** {barricades} units")
        with st.expander("📊 View calculation breakdown", expanded=False):
            st.markdown("**Rules Applied:**")
            for rule in barricades_breakdown['rules']:
                status = "✓" if rule['applied'] else "✗"
                st.write(f"{status} {rule['rule']}: +{rule['value']} units")
            st.caption(
                f"Road closure: {'Yes' if road_closure == 'Yes' else 'No'} | "
                f"Junctions: {num_affected_junctions} | "
                f"Operational Duration: {recovery_hours:.1f}h"
            )

        primary_corridor = matched_cluster.get('dominant_corridor', 'Non-corridor')
        if primary_corridor != "Non-corridor":
            st.markdown(f"**🚦 Diversion Required:** Avoid **{primary_corridor}** corridor. Use neighboring corridors for traffic diversion.")
        else:
            st.markdown("**🚦 Localized Diversion Recommended:** Manage traffic within immediate vicinity.")

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

        # Show confidence factors
        with st.expander("📊 View confidence factors", expanded=False):
            st.markdown("**Factors affecting confidence:**")

            col1, col2, col3 = st.columns(3)

            with col1:
                cluster_size = matched_cluster.get('event_count', 0)
                if cluster_size >= 100:
                    cluster_factor = 1.0
                    cluster_note = "✓ Large cluster"
                elif cluster_size >= 50:
                    cluster_factor = 0.85
                    cluster_note = "~ Medium cluster"
                else:
                    cluster_factor = 0.7
                    cluster_note = "⚠ Small cluster"

                st.metric("Cluster Size Factor", f"{cluster_factor:.0%}")
                st.caption(f"{cluster_note} ({cluster_size} events)")

            with col2:
                has_failures = len(get_cluster_failures(cluster_id, failures_data)) > 0
                learning_factor = 0.8 if has_failures else 1.0
                learning_note = "⚠ Inconsistency" if has_failures else "✓ Consistent"

                st.metric("Learning Factor", f"{learning_factor:.0%}")
                st.caption(f"{learning_note} responses")

            with col3:
                unknown_pct = 36.2  # From audit
                data_factor = 0.85 if unknown_pct > 30 else 1.0
                data_note = "⚠ Data quality" if unknown_pct > 30 else "✓ Good quality"

                st.metric("Data Quality Factor", f"{data_factor:.0%}")
                st.caption(f"{data_note}")

            st.caption(
                f"Final confidence = Base score ({similarity_score}/100) × "
                f"Cluster factor × Learning factor × Data quality factor"
            )

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

This system helps cities learn from historical disruptions, estimate operational burden, and generate response playbooks for future events.""")

st.sidebar.markdown("---")
st.sidebar.markdown("**API Endpoint:** `http://localhost:8000/api`")
