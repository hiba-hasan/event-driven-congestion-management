import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional, List
import numpy as np

app = FastAPI(
    title="Resilient City OS API",
    description="Event-driven congestion management using Event DNA clustering and Resilience Scoring",
    version="0.1.0"
)

junction_scores = {}
cluster_profiles = {}
learning_failures = {}
clustered_events = []
recovery_audit = {}
data_quality_metrics = {}


def load_data():
    global junction_scores, cluster_profiles, learning_failures, clustered_events, recovery_audit, data_quality_metrics

    junction_path = Path('results/junction_scores.json')
    if junction_path.exists():
        with open(junction_path) as f:
            junction_scores = json.load(f)

    cluster_path = Path('results/cluster_profiles.json')
    if cluster_path.exists():
        with open(cluster_path) as f:
            cluster_profiles = json.load(f)

    failure_path = Path('results/learning_failures.json')
    if failure_path.exists():
        with open(failure_path) as f:
            data = json.load(f)
            learning_failures = data

    audit_path = Path('results/recovery_audit.json')
    if audit_path.exists():
        with open(audit_path) as f:
            recovery_audit = json.load(f)
            # Extract data quality metrics
            data_quality_metrics['unknown_junction_pct'] = recovery_audit.get('unknown_junction_pct', 0)
            data_quality_metrics['total_records'] = recovery_audit.get('total_records', 0)
            data_quality_metrics['problematic_clusters'] = len(recovery_audit.get('problematic_clusters', []))

    print(f"Loaded {len(junction_scores)} junctions, {len(cluster_profiles)} clusters, {len(learning_failures)} learning failure data")
    print(f"Data Quality: {data_quality_metrics.get('unknown_junction_pct', 0):.1f}% records lack junction info")


@app.on_event("startup")
async def startup():
    load_data()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Resilient City OS API"}


@app.get("/api/junctions")
async def get_junctions(
    zone: Optional[str] = None,
    corridor: Optional[str] = None,
    sort_by: Optional[str] = "resilience",
    order: Optional[str] = "asc",
    limit: Optional[int] = 100,
    exclude_unknown: Optional[bool] = True
):
    """
    Get all junctions with their resilience scores.

    Query parameters:
    - zone: Filter by zone name
    - corridor: Filter by corridor name
    - sort_by: 'resilience', 'recovery_time', 'events' (default: resilience)
    - order: 'asc' or 'desc' (default: asc)
    - limit: Maximum results (default: 100)
    - exclude_unknown: Exclude Unknown_Junction from results (default: true)
    """
    results = list(junction_scores.values())

    if exclude_unknown:
        results = [j for j in results if j['junction_name'] != 'Unknown_Junction']

    if zone:
        results = [j for j in results if j.get('primary_zone') == zone]

    if corridor:
        results = [j for j in results if j.get('primary_corridor') == corridor]

    # Sort
    if sort_by == "resilience":
        results = sorted(results, key=lambda x: x['resilience_score'], reverse=(order == "desc"))
    elif sort_by == "recovery_time":
        results = sorted(results, key=lambda x: x['median_recovery_hours'], reverse=(order == "desc"))
    elif sort_by == "events":
        results = sorted(results, key=lambda x: x['event_count'], reverse=(order == "desc"))

    return {
        "total": len(results),
        "limit": limit,
        "junctions": results[:limit],
        "data_quality_note": f"Results exclude Unknown_Junction (36.2% of raw data). See /api/data-quality for details."
    }


@app.get("/api/cluster/{cluster_id}")
async def get_cluster(cluster_id: int):
    """Get Event DNA cluster profile and details."""
    cluster_key = str(cluster_id)
    if cluster_key not in cluster_profiles:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

    profile = cluster_profiles[cluster_key]

    # Find junctions affected by this cluster (excluding Unknown_Junction)
    affected_junctions_clean = [j for j in profile.get('affected_junctions', []) if j != 'Unknown_Junction']

    return {
        "cluster_id": cluster_id,
        "profile": profile,
        "affected_junctions_count": len(affected_junctions_clean),
        "affected_junctions": affected_junctions_clean[:20],
        "data_quality_note": "Affected junctions list excludes Unknown_Junction"
    }


@app.get("/api/junction/{junction_name}")
async def get_junction_details(junction_name: str):
    """Get detailed information about a specific junction."""
    if junction_name not in junction_scores:
        raise HTTPException(status_code=404, detail=f"Junction '{junction_name}' not found")

    junction_data = junction_scores[junction_name]

    return {
        "junction_name": junction_name,
        "resilience_score": junction_data['resilience_score'],
        "resilience_category": junction_data['resilience_category'],
        "event_count": junction_data['event_count'],
        "avg_recovery_hours": junction_data['avg_recovery_hours'],
        "median_recovery_hours": junction_data['median_recovery_hours'],
        "std_recovery_hours": junction_data['std_recovery_hours'],
        "zone": junction_data.get('primary_zone'),
        "corridor": junction_data.get('primary_corridor'),
        "event_types": junction_data.get('event_types', [])
    }


@app.get("/api/learning-failures")
async def get_learning_failures(
    severity: Optional[str] = None,
    limit: Optional[int] = 50
):
    """
    Get junctions with institutional memory gaps (learning failures).

    Query parameters:
    - severity: 'Critical' or 'High' (default: all)
    - limit: Maximum results (default: 50)
    """
    if not learning_failures:
        return {"total": 0, "failures": []}

    failures = learning_failures.get('failures', [])

    # Filter Unknown_Junction from failures
    failures = [f for f in failures if f.get('junction_name') != 'Unknown_Junction']

    if severity:
        failures = [f for f in failures if f.get('severity') == severity]

    failures = sorted(failures, key=lambda x: x['coefficient_of_variation'], reverse=True)

    return {
        "total": len(failures),
        "limit": limit,
        "failures": failures[:limit],
        "data_quality_note": "Results exclude Unknown_Junction learning failure records"
    }


@app.get("/api/data-quality")
async def get_data_quality():
    """Get data quality metrics and audit information."""
    if not recovery_audit:
        return {"status": "No audit data available"}

    unknown_audit = recovery_audit.get('unknown_junction_audit', {})

    return {
        "total_records": recovery_audit.get('total_records', 0),
        "unknown_junction": {
            "percentage": recovery_audit.get('unknown_junction_pct', 0),
            "record_count": unknown_audit.get('nonzero_count', 0),
            "mean_recovery_hours": unknown_audit.get('mean', 0),
            "median_recovery_hours": unknown_audit.get('median', 0),
            "confidence_note": unknown_audit.get('confidence_note', ''),
        },
        "problematic_clusters": recovery_audit.get('problematic_clusters', [])[:3],
        "recommendation": "Use median recovery times for operational decisions. Mean values may be inflated by administrative closure durations."
    }


@app.get("/api/summary")
async def get_summary():
    """Get overall system summary and statistics."""
    all_scores = list(junction_scores.values())

    # Exclude Unknown_Junction
    all_scores_clean = [j for j in all_scores if j['junction_name'] != 'Unknown_Junction']

    resilience_scores = [j['resilience_score'] for j in all_scores_clean]
    fragile_count = sum(1 for s in resilience_scores if s < 0.5)
    resilient_count = sum(1 for s in resilience_scores if s >= 0.5)

    recovery_times = [j['median_recovery_hours'] for j in all_scores_clean]

    return {
        "total_junctions": len(all_scores_clean),
        "total_clusters": len(cluster_profiles),
        "total_events_processed": sum(j['event_count'] for j in all_scores_clean),
        "fragile_junctions": fragile_count,
        "resilient_junctions": resilient_count,
        "avg_resilience_score": float(sum(resilience_scores) / len(resilience_scores)) if resilience_scores else 0,
        "median_recovery_hours": float(np.median(recovery_times)) if recovery_times else 0,
        "learning_failure_junctions": len(set(f['junction_name'] for f in learning_failures.get('failures', []) if f.get('junction_name') != 'Unknown_Junction')),
        "data_quality": {
            "unknown_junction_pct": data_quality_metrics.get('unknown_junction_pct', 0),
            "problematic_clusters": data_quality_metrics.get('problematic_clusters', 0),
        }
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)

