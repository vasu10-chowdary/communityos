import json
import time
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.incident import (
    IncidentAnalysisRequest,
    IncidentAnalysisResponse,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    ResourceRecommendationRequest,
    ResourceRecommendationResponse,
    ResourceAssignmentRequest,
    IncidentStatusUpdateRequest,
    IncidentMergeRequest,
    IncidentCreateRequest,
    ResourceCreateRequest
)
from app.services.gemini_service import analyze_incident_with_gemini
from app.services.duplicate_service import detect_duplicates
from app.services.resource_matching_service import match_resources
from app.services.database import get_db, transaction, dict_from_row
from app.core.config import settings
from app.core.auth import (
    AuthenticatedUser,
    get_current_user,
    require_coordinator,
    require_responder
)
from app.core.rate_limit import rate_limit_analyze

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# ----------------- INCIDENT READ & CREATE (REST) -----------------

@router.get("", response_model=List[dict])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (e.g. Reported, In Progress, Resolved)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500)
):
    """Lists incidents from persistent SQLite store, ordered by created_at DESC."""
    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if status and status != "ALL":
        query += " AND status = ?"
        params.append(status)

    if category and category != "ALL":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict_from_row(r) for r in rows]

@router.post("", response_model=dict)
async def create_incident(
    payload: IncidentCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Creates a new community emergency hazard report."""
    now_iso = datetime.now(timezone.utc).isoformat()
    incident_id = f"inc-{int(time.time() * 1000)}"

    sev_str = "Medium"
    sev_lvl = 3
    urg_score = 50

    if payload.latest_analysis:
        sev_lvl = int(payload.latest_analysis.get("severity_level", 3))
        sev_str = payload.latest_analysis.get("severity", "Medium")
        urg_score = int(payload.latest_analysis.get("urgency_score", 50))

    analysis_json = json.dumps(payload.latest_analysis) if payload.latest_analysis else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incidents (
                id, title, description, category, severity, severity_level, urgency_score,
                status, location, latitude, longitude, reporter_id, reporter_name,
                image_url, image_base64, is_demo, latest_analysis, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            incident_id, payload.title, payload.description, payload.category,
            sev_str, sev_lvl, urg_score, "Reported", payload.location,
            payload.latitude, payload.longitude, current_user.uid,
            current_user.name or "Community Resident", payload.image_url,
            payload.image_base64, 1 if payload.is_demo else 0, analysis_json,
            now_iso, now_iso
        ))
        conn.commit()

        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        return dict_from_row(row)

@router.get("/{incident_id}", response_model=dict)
async def get_incident_detail(incident_id: str):
    """Retrieves full detail of a single incident."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        return dict_from_row(row)

# ----------------- AI ANALYSIS & HEURISTICS -----------------

@router.post(
    "/analyze",
    response_model=IncidentAnalysisResponse,
    dependencies=[Depends(rate_limit_analyze)]
)
async def analyze_incident(
    payload: IncidentAnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Executes server-side Google Gemini multimodal analysis."""
    try:
        analysis = await analyze_incident_with_gemini(payload)

        # If an incident_id is provided, persist analysis to SQLite
        if payload.incident_id:
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE incidents
                        SET severity = ?, severity_level = ?, urgency_score = ?, latest_analysis = ?, updated_at = ?
                        WHERE id = ?;
                    """, (
                        analysis.severity,
                        analysis.severity_level,
                        analysis.urgency_score,
                        json.dumps(analysis.model_dump()),
                        datetime.now(timezone.utc).isoformat(),
                        payload.incident_id
                    ))
                    conn.commit()
            except Exception as e:
                print(f"[Analyze Warning] Could not persist analysis to SQLite: {e}")

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "GEMINI_ANALYSIS_FAILED",
                "message": f"Gemini API analysis encountered an unexpected error: {str(e)}"
            }
        )

# ----------------- DUPLICATE DETECTION -----------------

@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates_endpoint(
    payload: DuplicateCheckRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Evaluates lexical and geospatial proximity against active reports."""
    try:
        # If caller did not provide existing incidents, load them from SQLite
        if not payload.existing_incidents:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, description, category, latitude, longitude
                    FROM incidents
                    ORDER BY created_at DESC LIMIT 50;
                """)
                rows = cursor.fetchall()
                payload.existing_incidents = [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "category": r["category"],
                        "latitude": r["latitude"],
                        "longitude": r["longitude"]
                    }
                    for r in rows
                ]

        return detect_duplicates(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate check failed: {str(e)}")

# ----------------- RESOURCE RECOMMENDATION & ASSIGNMENT -----------------

@router.post("/recommend-resources", response_model=ResourceRecommendationResponse)
async def recommend_resources_endpoint(
    payload: ResourceRecommendationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Ranks available civic equipment and crews based on hazard type."""
    try:
        # If caller did not supply resources, query from SQLite
        if not payload.available_resources:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM resources;")
                rows = cursor.fetchall()
                payload.available_resources = [dict_from_row(r) for r in rows]

        return match_resources(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resource recommendation failed: {str(e)}")

@router.post("/assign-resource")
async def assign_resource(
    payload: ResourceAssignmentRequest,
    current_user: AuthenticatedUser = Depends(require_coordinator)
):
    """
    Assigns an emergency resource to an incident via atomic transaction.
    Enforces concurrency lock: if resource is already Busy, rejects with 409 Conflict.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with transaction() as conn:
            cursor = conn.cursor()

            # 1. Inspect resource under lock
            cursor.execute("SELECT * FROM resources WHERE id = ?", (payload.resource_id,))
            res_row = cursor.fetchone()
            if not res_row:
                raise HTTPException(status_code=404, detail="Resource not found")

            res_dict = dict(res_row)
            if res_dict.get("availability") == "Busy" or res_dict.get("assigned_incident"):
                assigned_to = res_dict.get("assigned_incident", "another incident")
                raise HTTPException(
                    status_code=409,
                    detail=f"Resource conflict: '{res_dict.get('name', 'Resource')}' is already assigned to incident {assigned_to}."
                )

            # 2. Inspect incident
            cursor.execute("SELECT * FROM incidents WHERE id = ?", (payload.incident_id,))
            inc_row = cursor.fetchone()
            if not inc_row:
                raise HTTPException(status_code=404, detail="Incident not found")

            # 3. Update resource state to Busy
            cursor.execute("""
                UPDATE resources
                SET availability = 'Busy', assigned_incident = ?, notes = ?, updated_at = ?
                WHERE id = ?;
            """, (payload.incident_id, payload.notes, now_iso, payload.resource_id))

            # 4. Update incident status to Resource Dispatched
            cursor.execute("""
                UPDATE incidents
                SET status = 'Resource Dispatched',
                    assigned_resource_id = ?,
                    assigned_resource_name = ?,
                    assigned_by = ?,
                    updated_at = ?
                WHERE id = ?;
            """, (payload.resource_id, res_dict.get("name"), current_user.uid, now_iso, payload.incident_id))

        return {
            "status": "success",
            "message": "Resource successfully assigned via atomic transaction",
            "assigned_by": current_user.uid
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- INCIDENT MERGE -----------------

@router.post("/merge")
async def merge_incidents(
    payload: IncidentMergeRequest,
    current_user: AuthenticatedUser = Depends(require_coordinator)
):
    """Links duplicate incident to primary incident and marks duplicate In Review."""
    now_iso = datetime.now(timezone.utc).isoformat()
    link_id = f"dup-link-{int(time.time()*1000)}"

    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO duplicate_links (id, primary_id, duplicate_id, reason, merged_by, merged_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (link_id, payload.primary_incident_id, payload.duplicate_incident_id, payload.merge_reason, current_user.uid, now_iso))

            cursor.execute("""
                UPDATE incidents
                SET duplicate_of = ?, status = 'In Review', updated_at = ?
                WHERE id = ?;
            """, (payload.primary_incident_id, now_iso, payload.duplicate_incident_id))

        return {
            "status": "merged",
            "primary_incident_id": payload.primary_incident_id,
            "duplicate_incident_id": payload.duplicate_incident_id,
            "merged_by": current_user.uid,
            "message": f"Incident {payload.duplicate_incident_id} successfully linked to primary {payload.primary_incident_id}. History preserved."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- STATUS LIFECYCLE & ATOMIC RELEASE -----------------

@router.post("/update-status")
async def update_status(
    payload: IncidentStatusUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Updates incident operational lifecycle status.
    - Resolving requires Coordinator or Admin role.
    - Field progress notes require Responder, Coordinator, or Admin.
    - Citizens cannot transition status.
    - When marked Resolved, atomically releases any assigned resource back to Available.
    """
    # 1. Resolving incidents is privileged to Coordinators
    if payload.status == "Resolved" and current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only Coordinators can approve and mark an incident as Resolved."
        )

    # 2. Marking In Progress or logging responder progress requires Responder or Coordinator
    if payload.status == "In Progress" or payload.responder_progress_note:
        if current_user.role not in ["responder", "coordinator", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Only assigned Responders or Coordinators can update field progress."
            )

    # 3. Citizens cannot transition status
    if current_user.role == "citizen" and payload.status not in ["Reported", "Cancelled"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Citizens cannot transition incident status."
        )

    released_resource_id = None
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM incidents WHERE id = ?", (payload.incident_id,))
            inc_row = cursor.fetchone()
            if not inc_row:
                raise HTTPException(status_code=404, detail="Incident not found")

            inc_dict = dict(inc_row)

            if payload.status == "Resolved":
                assigned_res_id = inc_dict.get("assigned_resource_id")
                if assigned_res_id:
                    cursor.execute("SELECT * FROM resources WHERE id = ?", (assigned_res_id,))
                    res_row = cursor.fetchone()
                    if res_row:
                        res_dict = dict(res_row)
                        if res_dict.get("assigned_incident") == payload.incident_id or res_dict.get("availability") == "Busy":
                            cursor.execute("""
                                UPDATE resources
                                SET availability = 'Available', assigned_incident = NULL, updated_at = ?
                                WHERE id = ?;
                            """, (now_iso, assigned_res_id))
                            released_resource_id = assigned_res_id

                resolution_note = payload.resolution_notes or inc_dict.get("resolution_notes")
                responder_note = payload.responder_progress_note or inc_dict.get("responder_notes")

                cursor.execute("""
                    UPDATE incidents
                    SET status = 'Resolved',
                        resolution_notes = ?,
                        responder_notes = ?,
                        last_updated_by = ?,
                        updated_at = ?
                    WHERE id = ?;
                """, (resolution_note, responder_note, current_user.uid, now_iso, payload.incident_id))

            else:
                resolution_note = payload.resolution_notes or inc_dict.get("resolution_notes")
                responder_note = payload.responder_progress_note or inc_dict.get("responder_notes")

                cursor.execute("""
                    UPDATE incidents
                    SET status = ?,
                        resolution_notes = ?,
                        responder_notes = ?,
                        last_updated_by = ?,
                        updated_at = ?
                    WHERE id = ?;
                """, (payload.status, resolution_note, responder_note, current_user.uid, now_iso, payload.incident_id))

        return {
            "status": "updated",
            "new_status": payload.status,
            "actor_role": current_user.role,
            "actor_id": current_user.uid,
            "released_resource_id": released_resource_id,
            "notes": payload.resolution_notes or payload.responder_progress_note
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- CIVIC RESOURCES REST ENDPOINTS -----------------

@router.get("/resources/pool", response_model=List[dict])
async def list_resources():
    """Lists all civic emergency mitigation resources."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources ORDER BY updated_at DESC;")
        rows = cursor.fetchall()
        return [dict_from_row(r) for r in rows]

@router.post("/resources/pool", response_model=dict)
async def create_resource(
    payload: ResourceCreateRequest,
    current_user: AuthenticatedUser = Depends(require_coordinator)
):
    """Creates a new civic emergency resource (Coordinator only)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    res_id = f"res-{payload.category or 'unit'}-{int(time.time()*1000)}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resources (
                id, name, category, type, capacity, availability,
                service_area, location, contact, latitude, longitude,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'Available', ?, ?, ?, ?, ?, ?, ?);
        """, (
            res_id, payload.name, payload.category, payload.type, payload.capacity,
            payload.service_area, payload.location, payload.contact,
            payload.latitude, payload.longitude, now_iso, now_iso
        ))
        conn.commit()

        cursor.execute("SELECT * FROM resources WHERE id = ?", (res_id,))
        return dict_from_row(cursor.fetchone())

# ----------------- ANALYTICS AGGREGATION -----------------

@router.get("/metrics/summary")
async def get_analytics_metrics():
    """Provides high-level incident, urgency, and resource readiness metrics."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM incidents;")
        total_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resolved';")
        resolved_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'In Progress';")
        in_progress_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Reported';")
        reported_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resource Dispatched';")
        dispatched_count = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(urgency_score) FROM incidents;")
        avg_urgency = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT category, COUNT(*) FROM incidents GROUP BY category;")
        category_counts = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM resources;")
        total_resources = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM resources WHERE availability = 'Available';")
        available_resources = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM resources WHERE availability = 'Busy';")
        busy_resources = cursor.fetchone()[0]

        return {
            "total_incidents": total_incidents,
            "resolved_incidents": resolved_count,
            "in_progress_incidents": in_progress_count,
            "reported_incidents": reported_count,
            "dispatched_incidents": dispatched_count,
            "average_urgency": round(float(avg_urgency), 1),
            "category_distribution": category_counts,
            "total_resources": total_resources,
            "available_resources": available_resources,
            "busy_resources": busy_resources
        }
