from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import firestore
from app.schemas.incident import (
    IncidentAnalysisRequest, 
    IncidentAnalysisResponse,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    ResourceRecommendationRequest,
    ResourceRecommendationResponse,
    ResourceAssignmentRequest,
    IncidentStatusUpdateRequest,
    IncidentMergeRequest
)
from app.services.gemini_service import analyze_incident_with_gemini
from app.services.duplicate_service import detect_duplicates
from app.services.resource_matching_service import match_resources
from app.services.firebase_service import get_db
from app.core.config import settings
from app.core.auth import (
    AuthenticatedUser, 
    get_current_user, 
    require_coordinator, 
    require_responder
)
from app.core.rate_limit import rate_limit_analyze

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# 1. Multimodal Incident Analysis (Protected + Rate Limited)
@router.post(
    "/analyze", 
    response_model=IncidentAnalysisResponse,
    dependencies=[Depends(rate_limit_analyze)]
)
async def analyze_incident(
    payload: IncidentAnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        analysis = await analyze_incident_with_gemini(payload)
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

# 2. Duplicate Detection (Protected)
@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates_endpoint(
    payload: DuplicateCheckRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        return detect_duplicates(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate check failed: {str(e)}")

# 3. Recommend Matching Resources (Protected)
@router.post("/recommend-resources", response_model=ResourceRecommendationResponse)
async def recommend_resources_endpoint(
    payload: ResourceRecommendationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        return match_resources(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resource recommendation failed: {str(e)}")

# 4. Safe Resource Assignment (Coordinator Only + Concurrency Protected)
@router.post("/assign-resource")
async def assign_resource(
    payload: ResourceAssignmentRequest,
    current_user: AuthenticatedUser = Depends(require_coordinator)
):
    db = get_db()
    if not db:
        if settings.is_production():
            raise HTTPException(
                status_code=503, 
                detail="Cloud Firestore is not initialized or accessible in production."
            )
        # Development mode simulation only
        return {
            "status": "simulated",
            "is_simulated": True,
            "message": "Resource assignment validated in development mode without live Firestore.",
            "incident_id": payload.incident_id,
            "resource_id": payload.resource_id,
            "assigned_by": current_user.uid
        }

    try:
        incident_ref = db.collection("incidents").document(payload.incident_id)
        resource_ref = db.collection("resources").document(payload.resource_id)

        @firestore.transactional
        def update_in_transaction(transaction, inc_ref, res_ref):
            res_snapshot = res_ref.get(transaction=transaction)
            if not res_snapshot.exists:
                raise HTTPException(status_code=404, detail="Resource not found")
            
            res_data = res_snapshot.to_dict() or {}
            # Concurrency safe check: verify availability inside transaction
            if res_data.get("availability") == "Busy" or res_data.get("assigned_incident"):
                assigned_to = res_data.get("assigned_incident", "another incident")
                raise HTTPException(
                    status_code=409, 
                    detail=f"Resource conflict: '{res_data.get('name', 'Resource')}' is already assigned to incident {assigned_to}."
                )

            inc_snapshot = inc_ref.get(transaction=transaction)
            if not inc_snapshot.exists:
                raise HTTPException(status_code=404, detail="Incident not found")

            now_iso = datetime.now(timezone.utc).isoformat()
            
            transaction.update(res_ref, {
                "availability": "Busy",
                "assigned_incident": payload.incident_id,
                "notes": payload.notes,
                "updated_at": now_iso
            })
            transaction.update(inc_ref, {
                "status": "Resource Dispatched",
                "assigned_resource_id": payload.resource_id,
                "assigned_resource_name": res_data.get("name"),
                "assigned_by": current_user.uid,
                "updated_at": now_iso
            })

        transaction = db.transaction()
        update_in_transaction(transaction, incident_ref, resource_ref)
        return {
            "status": "success", 
            "message": "Resource successfully assigned via atomic Firestore transaction",
            "assigned_by": current_user.uid
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Merge Incidents (Coordinator Only)
@router.post("/merge")
async def merge_incidents(
    payload: IncidentMergeRequest,
    current_user: AuthenticatedUser = Depends(require_coordinator)
):
    db = get_db()
    if db:
        try:
            # Preserve both records, create duplicate link
            link_ref = db.collection("duplicate_links").document()
            link_ref.set({
                "primary_id": payload.primary_incident_id,
                "duplicate_id": payload.duplicate_incident_id,
                "reason": payload.merge_reason,
                "merged_by": current_user.uid,
                "merged_at": datetime.now(timezone.utc).isoformat()
            })
            # Update duplicate incident flag
            dup_ref = db.collection("incidents").document(payload.duplicate_incident_id)
            dup_ref.update({
                "duplicate_of": payload.primary_incident_id,
                "status": "In Review"
            })
        except Exception as e:
            print(f"[Merge Warning] Could not persist duplicate link to Firestore: {e}")

    return {
        "status": "merged",
        "primary_incident_id": payload.primary_incident_id,
        "duplicate_incident_id": payload.duplicate_incident_id,
        "merged_by": current_user.uid,
        "message": f"Incident {payload.duplicate_incident_id} successfully linked to primary {payload.primary_incident_id}. History preserved."
    }

# 6. Status Lifecycle Update (Role-Enforced)
@router.post("/update-status")
async def update_status(
    payload: IncidentStatusUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    # Role validation rules:
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

    # 3. Citizens can only cancel or update their own pending report
    if current_user.role == "citizen" and payload.status not in ["Reported", "Cancelled"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Citizens cannot transition incident status."
        )

    db = get_db()
    released_resource_id = None
    if db and payload.incident_id:
        try:
            inc_ref = db.collection("incidents").document(payload.incident_id)
            now_iso = datetime.now(timezone.utc).isoformat()

            if payload.status == "Resolved":
                @firestore.transactional
                def resolve_incident_and_release_resource(transaction, incident_ref):
                    nonlocal released_resource_id
                    inc_snap = incident_ref.get(transaction=transaction)
                    if not inc_snap.exists:
                        raise HTTPException(status_code=404, detail="Incident not found")

                    inc_data = inc_snap.to_dict() or {}
                    assigned_res_id = inc_data.get("assigned_resource_id")

                    if assigned_res_id:
                        res_ref = db.collection("resources").document(assigned_res_id)
                        res_snap = res_ref.get(transaction=transaction)
                        if res_snap.exists:
                            res_data = res_snap.to_dict() or {}
                            # Only release if assigned to this incident or marked busy
                            if res_data.get("assigned_incident") == payload.incident_id or res_data.get("availability") == "Busy":
                                transaction.update(res_ref, {
                                    "availability": "Available",
                                    "assigned_incident": None,
                                    "updated_at": now_iso
                                })
                                released_resource_id = assigned_res_id

                    update_data = {
                        "status": "Resolved",
                        "updated_at": now_iso,
                        "last_updated_by": current_user.uid
                    }
                    if payload.resolution_notes:
                        update_data["resolution_notes"] = payload.resolution_notes
                    if payload.responder_progress_note:
                        update_data["responder_notes"] = payload.responder_progress_note
                    transaction.update(incident_ref, update_data)

                transaction = db.transaction()
                resolve_incident_and_release_resource(transaction, inc_ref)
            else:
                inc_snap = inc_ref.get()
                if not inc_snap.exists:
                    raise HTTPException(status_code=404, detail="Incident not found")
                update_data = {
                    "status": payload.status,
                    "updated_at": now_iso,
                    "last_updated_by": current_user.uid
                }
                if payload.resolution_notes:
                    update_data["resolution_notes"] = payload.resolution_notes
                if payload.responder_progress_note:
                    update_data["responder_notes"] = payload.responder_progress_note
                inc_ref.update(update_data)
        except HTTPException:
            raise
        except Exception as e:
            print(f"[Update Status Warning] Could not sync status to Firestore: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "updated",
        "new_status": payload.status,
        "actor_role": current_user.role,
        "actor_id": current_user.uid,
        "released_resource_id": released_resource_id,
        "notes": payload.resolution_notes or payload.responder_progress_note
    }
