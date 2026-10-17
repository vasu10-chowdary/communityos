import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from firebase_admin import auth as fb_auth
from app.main import app
from app.core.rate_limit import analyze_rate_limiter
from app.core.auth import AuthenticatedUser, get_current_user, create_access_token
from app.core.config import settings
from app.services.database import get_db

client = TestClient(app)

# Helper mock for auth.verify_id_token
def mock_verify_id_token(token, **kwargs):
    if token == "mock-citizen-token":
        return {
            "uid": "citizen-uid-100",
            "email": "citizen@communityos.org",
            "name": "Citizen Alex",
            "role": "citizen",
            "firebase": {"sign_in_provider": "password"}
        }
    elif token == "mock-coordinator-token":
        return {
            "uid": "coord-uid-200",
            "email": "coordinator@communityos.org",
            "name": "Commander Sarah",
            "role": "coordinator",
            "firebase": {"sign_in_provider": "password"}
        }
    elif token == "mock-responder-token":
        return {
            "uid": "resp-uid-300",
            "email": "responder@communityos.org",
            "name": "Officer Taylor",
            "role": "responder",
            "firebase": {"sign_in_provider": "password"}
        }
    elif token == "mock-no-role-token":
        # Simulates token where role is not in custom claims, defaults to citizen
        return {
            "uid": "norole-uid-400",
            "email": "guest@communityos.org",
            "name": "Guest User",
            "firebase": {"sign_in_provider": "anonymous"}
        }
    else:
        raise ValueError("Invalid ID token provided.")

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    analyze_rate_limiter.reset()
    yield
    analyze_rate_limiter.reset()

# ----------------- SYSTEM & HEALTH TESTS -----------------
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "cors_origins" in data
    assert isinstance(data["cors_origins"], list)
    # Ensure no wildcard in allowed origins
    assert "*" not in data["cors_origins"]

# ----------------- AUTHENTICATION TESTS -----------------
def test_protected_endpoint_no_token():
    # Calling assign-resource with no Authorization header must fail with 401
    response = client.post("/api/incidents/assign-resource", json={
        "incident_id": "inc-101",
        "resource_id": "res-101"
    })
    assert response.status_code == 401
    assert "Missing or invalid Bearer token" in response.json()["detail"]

def test_protected_endpoint_invalid_token():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/assign-resource",
            headers={"Authorization": "Bearer bad-token-12345"},
            json={"incident_id": "inc-101", "resource_id": "res-101"}
        )
        assert response.status_code == 401
        assert "Invalid or expired authentication token" in response.json()["detail"]

# ----------------- ROLE-BASED ACCESS CONTROL (RBAC) TESTS -----------------
def test_citizen_cannot_assign_resource():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/assign-resource",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={"incident_id": "inc-101", "resource_id": "res-101"}
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

def test_spoofed_role_header_or_body_ignored():
    """
    CRITICAL SECURITY CHECK:
    Verify that if a client passes a spoofed 'X-Role: coordinator' header
    or 'actor_role: coordinator' in body with a citizen token, it is strictly REJECTED with 403.
    """
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/assign-resource",
            headers={
                "Authorization": "Bearer mock-citizen-token",
                "X-Role": "coordinator",
                "X-User-Role": "admin"
            },
            json={
                "incident_id": "inc-101",
                "resource_id": "res-101",
                "actor_role": "coordinator"
            }
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

def test_coordinator_can_assign_resource():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO incidents (id, title, description, category, status, created_at, updated_at) VALUES ('inc-demo-101', 'Severe Stormwater Backflow', 'Flood test', 'Flooding and waterlogging', 'In Review', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        cursor.execute("INSERT OR REPLACE INTO resources (id, name, type, availability, created_at, updated_at) VALUES ('res-demo-202', 'Demo Pump Trailer 202', 'Pumps', 'Available', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        conn.commit()

    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/assign-resource",
            headers={"Authorization": "Bearer mock-coordinator-token"},
            json={"incident_id": "inc-demo-101", "resource_id": "res-demo-202"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "simulated"]
        assert data["assigned_by"] == "coord-uid-200"

def test_citizen_cannot_resolve_incident():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/update-status",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={"status": "Resolved", "incident_id": "inc-demo-101"}
        )
        assert response.status_code == 403
        assert "Only Coordinators can approve and mark an incident as Resolved" in response.json()["detail"]

def test_coordinator_can_resolve_incident():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/update-status",
            headers={"Authorization": "Bearer mock-coordinator-token"},
            json={"status": "Resolved", "incident_id": "inc-demo-101", "resolution_notes": "Cleared flood waters"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "Resolved"
        assert data["actor_role"] == "coordinator"

def test_resolution_releases_assigned_resource():
    """
    Verifies that resolving an incident with an assigned resource executes a transaction
    that releases the resource back to 'Available' and clears assigned_incident.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO resources (id, name, type, availability, assigned_incident, created_at, updated_at) VALUES ('res-pump-101', 'High-Capacity Sump Pump', 'Pumps', 'Busy', 'inc-test-res-1', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        cursor.execute("INSERT OR REPLACE INTO incidents (id, title, description, category, status, assigned_resource_id, created_at, updated_at) VALUES ('inc-test-res-1', 'Severe flooding on Main St', 'Flood test', 'Flooding and waterlogging', 'In Progress', 'res-pump-101', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        conn.commit()

    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/update-status",
            headers={"Authorization": "Bearer mock-coordinator-token"},
            json={
                "status": "Resolved",
                "incident_id": "inc-test-res-1",
                "resolution_notes": "Hazard cleared, restoring equipment."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "Resolved"
        assert data["released_resource_id"] == "res-pump-101"

    # Verify resource update was committed in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT availability, assigned_incident FROM resources WHERE id = 'res-pump-101';")
        res_row = cursor.fetchone()
        assert res_row[0] == "Available"
        assert res_row[1] is None

def test_resolution_unassigned_incident():
    """
    Verifies that resolving an incident without any assigned resource succeeds safely.
    """
    mock_db = MagicMock()
    mock_transaction = MagicMock()
    mock_inc_ref = MagicMock()

    mock_inc_snap = MagicMock()
    mock_inc_snap.exists = True
    mock_inc_snap.to_dict.return_value = {
        "title": "Minor pothole",
        "status": "Reported",
        "assigned_resource_id": None
    }
    mock_inc_ref.get.return_value = mock_inc_snap
    mock_db.collection.return_value.document.return_value = mock_inc_ref
    mock_db.transaction.return_value = mock_transaction

    def fake_transactional(fn):
        def wrapper(transaction, inc_ref):
            return fn(transaction, inc_ref)
        return wrapper

    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        with patch("app.routes.incidents.get_db", return_value=mock_db):
            with patch("firebase_admin.firestore.transactional", side_effect=fake_transactional):
                response = client.post(
                    "/api/incidents/update-status",
                    headers={"Authorization": "Bearer mock-coordinator-token"},
                    json={"status": "Resolved", "incident_id": "inc-demo-102"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["new_status"] == "Resolved"
                assert data["released_resource_id"] is None

def test_resolution_nonexistent_incident_returns_404():
    mock_db = MagicMock()
    mock_transaction = MagicMock()
    mock_inc_ref = MagicMock()

    mock_inc_snap = MagicMock()
    mock_inc_snap.exists = False
    mock_inc_ref.get.return_value = mock_inc_snap
    mock_db.collection.return_value.document.return_value = mock_inc_ref
    mock_db.transaction.return_value = mock_transaction

    def fake_transactional(fn):
        def wrapper(transaction, inc_ref):
            return fn(transaction, inc_ref)
        return wrapper

    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        with patch("app.routes.incidents.get_db", return_value=mock_db):
            with patch("firebase_admin.firestore.transactional", side_effect=fake_transactional):
                response = client.post(
                    "/api/incidents/update-status",
                    headers={"Authorization": "Bearer mock-coordinator-token"},
                    json={"status": "Resolved", "incident_id": "inc-nonexistent"}
                )
                assert response.status_code == 404

def test_responder_can_update_in_progress():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/update-status",
            headers={"Authorization": "Bearer mock-responder-token"},
            json={
                "status": "In Progress",
                "incident_id": "inc-demo-101",
                "responder_progress_note": "Vacuum pump deployed, water receding 6 inches."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "In Progress"
        assert data["actor_role"] == "responder"

# ----------------- CONCURRENCY & TRANSACTION CONFLICT TESTS -----------------
def test_resource_assignment_concurrency_conflict():
    """
    Verifies that when a resource is already marked Busy or assigned to another incident,
    the transaction rejects the assignment with HTTP 409 Conflict.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO resources (id, name, type, availability, assigned_incident, created_at, updated_at) VALUES ('res-busy-999', 'Vacuum Pump Unit 1', 'Pumps', 'Busy', 'inc-other-999', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        cursor.execute("INSERT OR REPLACE INTO incidents (id, title, description, category, status, created_at, updated_at) VALUES ('inc-demo-101', 'Stormwater Backflow', 'Test flood', 'Flooding', 'In Review', '2026-10-17T00:00:00Z', '2026-10-17T00:00:00Z');")
        conn.commit()

    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/assign-resource",
            headers={"Authorization": "Bearer mock-coordinator-token"},
            json={"incident_id": "inc-demo-101", "resource_id": "res-busy-999"}
        )
        assert response.status_code == 409
        assert "Resource conflict" in response.json()["detail"]

# ----------------- INPUT & IMAGE VALIDATION TESTS -----------------
def test_image_validation_exceeds_size():
    # 7MB payload exceeds size limit
    large_payload = "A" * (8 * 1024 * 1024)
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/analyze",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Severe flooding on Main St",
                "description": "Water overflowing storm drains.",
                "image_base64": large_payload,
                "image_mime_type": "image/jpeg"
            }
        )
        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"]

def test_image_validation_invalid_mime():
    # Payload not matching jpeg/png/webp
    bad_image = "data:text/plain;base64,SGVsbG8gV29ybGQ="
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/analyze",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Severe flooding on Main St",
                "description": "Water overflowing storm drains.",
                "image_base64": bad_image,
                "image_mime_type": "text/plain"
            }
        )
        assert response.status_code == 400
        assert "Unsupported image format" in response.json()["detail"]

def test_image_validation_valid_base64_png():
    valid_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAc0lEQVR4nO3PQQ3AIADAQLTwmkQ8YAeBk3EhNKmA3ph7Xt3gBwH0QQB9EEAfBNAHAfRBAH0QQB8E0AcB9EEAfRBAHwTQBwH0QQB9EEAfPA/41rm6ALoAugC6ALoAugC6ALoAugC6ALoAugC6ALoAugALA37gVfexEtKyCAAAAABJRU5ErkJggg=="
    mock_analysis = {
        "category": "Flooding and waterlogging",
        "severity_level": 4,
        "severity": "High",
        "urgency_score": 80,
        "explanation": "Valid image processed",
        "visual_evidence_detected": ["Standing water"],
        "potential_risks": ["Property damage"],
        "uncertainties": [],
        "recommended_next_actions": ["Deploy pump"],
        "suggested_resources": ["High-Capacity Pump"],
        "human_review_required": True,
        "model_identifier": "models/gemini-3.8-flash",
        "provider": "Google Gen AI",
        "timestamp": "2026-10-17T03:00:00Z"
    }
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        with patch("app.routes.incidents.analyze_incident_with_gemini", return_value=mock_analysis):
            response = client.post(
                "/api/incidents/analyze",
                headers={"Authorization": "Bearer mock-citizen-token"},
                json={
                    "title": "Severe flooding on Main St",
                    "description": "Water overflowing storm drains.",
                    "image_base64": valid_png_b64,
                    "image_mime_type": "image/png"
                }
            )
            assert response.status_code == 200
            assert response.json()["severity"] == "High"

def test_image_validation_external_url_rejected():
    """
    Ensures raw external URLs passed as image_base64 are rejected with 400.
    The backend must NOT perform arbitrary URL fetching (SSRF prevention).
    """
    raw_url = "https://images.unsplash.com/photo-1547683905-f686c993aae5?auto=format&fit=crop&w=800"
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/analyze",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Severe flooding on Main St",
                "description": "Water overflowing storm drains.",
                "image_base64": raw_url,
                "image_mime_type": "image/jpeg"
            }
        )
        assert response.status_code == 400
        assert "Invalid base64" in response.json()["detail"]

def test_image_validation_corrupted_base64_rejected():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/analyze",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Severe flooding on Main St",
                "description": "Water overflowing storm drains.",
                "image_base64": "data:image/png;base64,%%%corrupted_payload%%%",
                "image_mime_type": "image/png"
            }
        )
        assert response.status_code == 400

# ----------------- RATE LIMITING TESTS -----------------
def test_rate_limiting_analyze_endpoint():
    # Submit requests exceeding rate limit (10 per minute)
    mock_analysis = {
        "category": "Flooding and waterlogging",
        "severity_level": 3,
        "severity": "Medium",
        "urgency_score": 60,
        "explanation": "Simulated flood analysis",
        "visual_evidence_detected": [],
        "potential_risks": ["Surface runoff"],
        "uncertainties": [],
        "recommended_next_actions": ["Cordon area"],
        "suggested_resources": ["High-Capacity Water Pump"],
        "human_review_required": False,
        "model_identifier": "models/gemini-3.8-flash",
        "provider": "Google Gen AI",
        "timestamp": "2026-10-17T03:00:00Z"
    }
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        with patch("app.routes.incidents.analyze_incident_with_gemini", return_value=mock_analysis):
            for i in range(10):
                res = client.post(
                    "/api/incidents/analyze",
                    headers={"Authorization": "Bearer mock-citizen-token"},
                    json={
                        "title": f"Incident Flood Report {i}",
                        "description": "Water rising above sidewalk."
                    }
                )
                assert res.status_code == 200

            # 11th request must be rate limited with 429
            limited_res = client.post(
                "/api/incidents/analyze",
                headers={"Authorization": "Bearer mock-citizen-token"},
                json={
                    "title": "Incident Flood Report Overflow",
                    "description": "Water rising above sidewalk."
                }
            )
            assert limited_res.status_code == 429
            assert "Rate limit exceeded" in limited_res.json()["detail"]
            assert "Retry-After" in limited_res.headers

# ----------------- DUPLICATES & RECOMMENDATIONS TESTS -----------------
def test_duplicate_detection_logic():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/check-duplicates",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Deep water logging on Oak Street",
                "description": "Culvert blocked by tree limbs and water entering yards.",
                "category": "Flooding and waterlogging",
                "latitude": 37.7750,
                "longitude": -122.4195,
                "existing_incidents": [
                    {
                        "id": "inc-demo-101",
                        "title": "Severe Stormwater Backflow on North Oak Ave",
                        "description": "Culvert is heavily obstructed by storm debris and tree limbs after torrential rain. Water has risen 1.5 feet.",
                        "category": "Flooding and waterlogging",
                        "latitude": 37.7749,
                        "longitude": -122.4194
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_potential_duplicate"] is True
        assert len(data["matches"]) >= 1
        assert data["matches"][0]["incident_id"] == "inc-demo-101"

def test_duplicate_detection_empty_existing_list():
    """Verifies that an empty existing incidents queue produces is_potential_duplicate=False without errors."""
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/check-duplicates",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Broken pipe on 4th Ave",
                "description": "Clean water bubbling up through pavement.",
                "category": "Water shortages",
                "latitude": 37.7800,
                "longitude": -122.4100,
                "existing_incidents": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_potential_duplicate"] is False
        assert data["matches"] == []

def test_duplicate_detection_privacy_safeguard():
    """Verifies that private fields (phone, email, reporter UID) are never exposed in DuplicateMatch schemas."""
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/check-duplicates",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Severe Stormwater Backflow on North Oak Ave",
                "description": "Culvert is heavily obstructed by storm debris. Water has risen 1.5 feet.",
                "category": "Flooding and waterlogging",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "existing_incidents": [
                    {
                        "id": "inc-live-999",
                        "title": "Severe Stormwater Backflow on North Oak Ave",
                        "description": "Culvert is heavily obstructed by storm debris.",
                        "category": "Flooding and waterlogging",
                        "latitude": 37.7749,
                        "longitude": -122.4194,
                        "reporter_id": "secret-uid-999",
                        "reporter_phone": "+1-555-0199",
                        "reporter_email": "private@example.com"
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_potential_duplicate"] is True
        match = data["matches"][0]
        # Ensure private fields are strictly excluded by the schema
        assert "reporter_id" not in match
        assert "reporter_phone" not in match
        assert "reporter_email" not in match
        assert match["incident_id"] == "inc-live-999"

def test_duplicate_detection_distinct_incident_no_false_positive():
    """Verifies that an incident with completely distinct category and distant coordinates is not flagged as duplicate."""
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/check-duplicates",
            headers={"Authorization": "Bearer mock-citizen-token"},
            json={
                "title": "Fallen oak tree blocking lane",
                "description": "Large tree fell across roadway completely blocking westbound traffic.",
                "category": "Fallen trees and blocked roads",
                "latitude": 37.7750,
                "longitude": -122.4195,
                "existing_incidents": [
                    {
                        "id": "inc-water-1",
                        "title": "Low water pressure in municipal line",
                        "description": "Residents experiencing low flow from taps.",
                        "category": "Water shortages",
                        "latitude": 37.8500,
                        "longitude": -122.3000
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_potential_duplicate"] is False
        assert len(data["matches"]) == 0

def test_resource_matching_engine():
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        response = client.post(
            "/api/incidents/recommend-resources",
            headers={"Authorization": "Bearer mock-coordinator-token"},
            json={
                "incident_id": "test-inc-1",
                "category": "Flooding and waterlogging",
                "severity_level": 4,
                "urgency_score": 85,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "service_area": "District 3",
                "available_resources": [
                    {
                        "id": "res-1",
                        "name": "High-Flow Vacuum Unit",
                        "type": "Flooding & Sump Pump Mitigation",
                        "availability": "Available",
                        "service_area": "District 3",
                        "latitude": 37.7750,
                        "longitude": -122.4190
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["resource_id"] == "res-1"
        assert data["recommendations"][0]["suitability_score"] > 0.6

# ----------------- COMPREHENSIVE SECURITY, FORGED-ROLE & CORS TESTS -----------------
def test_unauthorized_endpoints_reject_without_token():
    """
    Verifies that all protected endpoints return 401 when no token is supplied.
    """
    endpoints = [
        ("POST", "/api/incidents/analyze", {"title": "Test", "description": "Short description"}),
        ("POST", "/api/incidents/check-duplicates", {"title": "Test", "description": "Test"}),
        ("POST", "/api/incidents/recommend-resources", {"incident_id": "i1", "category": "pumps"}),
        ("POST", "/api/incidents/update-status", {"status": "Resolved", "incident_id": "i1"}),
        ("POST", "/api/incidents/merge", {"primary_incident_id": "i1", "duplicate_incident_id": "i2", "merge_reason": "duplicate"}),
    ]
    for method, path, payload in endpoints:
        res = client.request(method, path, json=payload)
        assert res.status_code == 401, f"Endpoint {path} did not reject unauthenticated request with 401 (got {res.status_code})"

def test_forged_role_rejected_on_merge():
    """
    Verifies that a citizen cannot merge incidents even if sending spoofed role headers or body.
    """
    with patch("firebase_admin.auth.verify_id_token", side_effect=mock_verify_id_token):
        res = client.post(
            "/api/incidents/merge",
            headers={
                "Authorization": "Bearer mock-citizen-token",
                "X-Role": "coordinator",
                "X-Custom-Claim": "admin"
            },
            json={
                "primary_incident_id": "inc-1",
                "duplicate_incident_id": "inc-2",
                "merge_reason": "Same hazard",
                "role": "coordinator"
            }
        )
        assert res.status_code == 403
        assert "Forbidden" in res.json()["detail"]

def test_cors_preflight_and_unauthorized_origin():
    """
    Verifies strict CORS origin allowlisting.
    Allowed origins (http://localhost:3000) get CORS headers; untrusted origins do not.
    """
    # 1. Allowed origin preflight
    res_allowed = client.options(
        "/api/incidents/assign-resource",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res_allowed.status_code == 200
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # 2. Untrusted origin
    res_untrusted = client.options(
        "/api/incidents/assign-resource",
        headers={
            "Origin": "https://malicious-attacker.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    # Untrusted origin should not receive access-control-allow-origin
    assert res_untrusted.headers.get("access-control-allow-origin") != "https://malicious-attacker.com"


# ----------------- SQLITE PERSISTENCE & REST ENDPOINTS TESTS -----------------
def test_jwt_auth_token_issuance_and_rbac():
    # 1. Citizen token generation (open to all)
    res_citizen = client.post("/api/auth/token", json={"role": "citizen", "name": "Test Citizen"})
    assert res_citizen.status_code == 200
    citizen_token = res_citizen.json()["access_token"]
    assert res_citizen.json()["role"] == "citizen"

    # Test /api/auth/me with JWT token
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res_me.status_code == 200
    assert res_me.json()["role"] == "citizen"

    # 2. Coordinator token generation under DEMO_MODE
    with patch.object(settings, "DEMO_MODE", True):
        res_coord = client.post("/api/auth/token", json={"role": "coordinator"})
        assert res_coord.status_code == 200
        assert res_coord.json()["role"] == "coordinator"
        assert res_coord.json()["is_demo_auth"] is True

    # 3. Coordinator token rejected in strict production without valid PIN
    with patch.object(settings, "DEMO_MODE", False):
        res_strict_fail = client.post("/api/auth/token", json={"role": "coordinator", "pin": "wrong-pin"})
        assert res_strict_fail.status_code == 403

        res_strict_ok = client.post("/api/auth/token", json={"role": "coordinator", "pin": settings.COORDINATOR_PIN})
        assert res_strict_ok.status_code == 200
        assert res_strict_ok.json()["role"] == "coordinator"

def test_sqlite_incidents_crud_flow():
    # Issue citizen JWT token
    res_token = client.post("/api/auth/token", json={"role": "citizen", "name": "Elena Citizen"})
    token = res_token.json()["access_token"]

    # 1. Create incident via POST /api/incidents
    create_payload = {
        "title": "Severe Flash Flood at Elm & 4th",
        "description": "Culvert clogged, street submerged 1 foot.",
        "category": "Flooding and waterlogging",
        "severity": "High",
        "severity_level": 4,
        "urgency_score": 85,
        "location": "Elm St & 4th Ave",
        "latitude": 37.7790,
        "longitude": -122.4180
    }
    res_create = client.post(
        "/api/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json=create_payload
    )
    assert res_create.status_code == 200
    created_data = res_create.json()
    incident_id = created_data["id"]
    assert created_data["title"] == "Severe Flash Flood at Elm & 4th"
    assert created_data["status"] == "Reported"

    # 2. Retrieve single incident via GET /api/incidents/{id}
    res_get = client.get(f"/api/incidents/{incident_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == incident_id

    # 3. Retrieve incident list via GET /api/incidents
    res_list = client.get("/api/incidents")
    assert res_list.status_code == 200
    items = res_list.json()
    assert isinstance(items, list)
    assert any(i["id"] == incident_id for i in items)

def test_sqlite_resources_pool_and_metrics():
    # Issue coordinator token
    coord_token = create_access_token(uid="coord-lead", role="coordinator")

    # 1. Retrieve resource pool
    res_pool = client.get("/api/incidents/resources/pool")
    assert res_pool.status_code == 200
    pool = res_pool.json()
    assert isinstance(pool, list)
    assert len(pool) >= 1

    # 2. Create resource via Coordinator
    res_create = client.post(
        "/api/incidents/resources/pool",
        headers={"Authorization": f"Bearer {coord_token}"},
        json={
            "name": "Heavy Duty Arborist Chipper Unit",
            "category": "cleanup teams",
            "type": "Tree Clearance",
            "capacity": "15 ton/hr chipper",
            "service_area": "District 5",
            "location": "South Yard",
            "contact": "tree@city.gov",
            "latitude": 37.7700,
            "longitude": -122.4200
        }
    )
    assert res_create.status_code == 200
    assert res_create.json()["name"] == "Heavy Duty Arborist Chipper Unit"

    # 3. Retrieve metrics summary
    res_metrics = client.get("/api/incidents/metrics/summary")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert "total_incidents" in metrics
    assert "available_resources" in metrics
    assert "busy_resources" in metrics

