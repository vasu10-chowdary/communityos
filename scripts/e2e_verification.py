import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Add workspace root and backend directory to path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

import firebase_admin
from firebase_admin import credentials, firestore, auth

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

TEST_INCIDENT_ID = f"test-e2e-inc-{int(time.time())}"
TEST_RESOURCE_ID = f"test-e2e-res-{int(time.time())}"
TEST_REPORTER_UID = f"test-reporter-uid-{int(time.time())}"

RESULTS = {}

def log_step(name, status, details=""):
    RESULTS[name] = {"status": status, "details": details}
    icon = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[INFO]"
    print(f"{icon} {name}: {details}")

def get_web_api_key():
    env_file = os.path.join("frontend", ".env.local")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("NEXT_PUBLIC_FIREBASE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None

def exchange_custom_token_for_id_token(custom_token: str, api_key: str) -> str:
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
    payload = json.dumps({"token": custom_token, "returnSecureToken": True}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["idToken"]

def run_e2e():
    print("=" * 65)
    print("      COMMUNITYOS COMPLETE E2E VERIFICATION SUITE")
    print("=" * 65)

    # 1. Verify Backend and Frontend Servers Running
    print("\n[Step 1] Checking server availability...")
    try:
        req = urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=5)
        health_data = json.loads(req.read().decode())
        if health_data.get("status") == "healthy":
            log_step("Backend Server Live", "PASS", f"FastAPI healthy on {BACKEND_URL} (Gemini: {health_data.get('gemini_model')})")
        else:
            log_step("Backend Server Live", "FAIL", f"Unexpected health response: {health_data}")
            return
    except Exception as e:
        log_step("Backend Server Live", "FAIL", f"Cannot connect to backend: {e}")
        return

    try:
        f_req = urllib.request.urlopen(FRONTEND_URL, timeout=5)
        if f_req.status == 200:
            log_step("Frontend Server Live", "PASS", f"Next.js 15 responding with HTTP 200 on {FRONTEND_URL}")
        else:
            log_step("Frontend Server Live", "FAIL", f"Frontend returned status {f_req.status}")
    except Exception as e:
        log_step("Frontend Server Live", "FAIL", f"Cannot connect to frontend: {e}")

    # 2. Firebase Initialization & Auth
    print("\n[Step 2] Verifying Firebase Admin and Cloud Firestore...")
    try:
        if not firebase_admin._apps:
            key_path = os.path.join("backend", "serviceAccountKey.json")
            if not os.path.exists(key_path):
                key_path = "serviceAccountKey.json"
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {'projectId': 'communityos-a36f0'})

        db = firestore.client()
        log_step("Firebase Admin & Firestore Initialized", "PASS", "Connected to Firestore project 'communityos-a36f0'")
    except Exception as e:
        log_step("Firebase Admin & Firestore Initialized", "FAIL", str(e))
        return

    # Mint genuine ID tokens with verified roles for E2E testing
    print("\n[Step 3] Minting genuine Firebase ID tokens with custom claims...")
    api_key = get_web_api_key()
    if not api_key:
        log_step("Firebase Auth Token Exchange", "FAIL", "Could not locate NEXT_PUBLIC_FIREBASE_API_KEY in frontend/.env.local")
        return

    try:
        coord_custom_token = auth.create_custom_token("e2e-coord-101", {"role": "coordinator"}).decode()
        resp_custom_token = auth.create_custom_token("e2e-resp-202", {"role": "responder"}).decode()
        citizen_custom_token = auth.create_custom_token(TEST_REPORTER_UID, {"role": "citizen"}).decode()
        
        # Exchange for genuine Google Firebase ID Tokens
        coord_id_token = exchange_custom_token_for_id_token(coord_custom_token, api_key)
        resp_id_token = exchange_custom_token_for_id_token(resp_custom_token, api_key)
        citizen_id_token = exchange_custom_token_for_id_token(citizen_custom_token, api_key)

        # Store user profile in Firestore users/{uid} for server-side role resolution
        db.collection("users").document("e2e-coord-101").set({
            "role": "coordinator",
            "name": "E2E Commander Sarah (Coordinator)",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        db.collection("users").document("e2e-resp-202").set({
            "role": "responder",
            "name": "E2E Officer Torres (Responder)",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        db.collection("users").document(TEST_REPORTER_UID).set({
            "role": "citizen",
            "name": "E2E Resident Alex (Citizen)",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        log_step("Genuine Firebase ID Token Exchange & RBAC", "PASS", "Exchanged custom tokens for live Google ID tokens; synced users/{uid}")
    except Exception as e:
        log_step("Genuine Firebase ID Token Exchange & RBAC", "FAIL", str(e))
        return

    # 3. Incident Submission & Verification in Firestore
    print("\n[Step 4] Submitting isolated test incident into Firestore...")
    now_iso = datetime.now(timezone.utc).isoformat()
    test_incident_data = {
        "title": "E2E Test: Overflowing Storm Drain at 5th and Market",
        "description": "High water levels overflowing onto sidewalks after heavy rainfall. Pedestrian access obstructed.",
        "category": "Flooding and waterlogging",
        "location": "5th St & Market St, Sector 2",
        "latitude": 37.7812,
        "longitude": -122.4075,
        "status": "Reported",
        "reporter_id": TEST_REPORTER_UID,
        "reporter_name": "E2E Resident Alex",
        "created_at": now_iso,
        "is_demo": True
    }
    try:
        db.collection("incidents").document(TEST_INCIDENT_ID).set(test_incident_data)
        inc_snap = db.collection("incidents").document(TEST_INCIDENT_ID).get()
        if inc_snap.exists and inc_snap.to_dict()["title"] == test_incident_data["title"]:
            log_step("Incident Submission & Read-Back", "PASS", f"Created & verified incident {TEST_INCIDENT_ID} in Cloud Firestore")
        else:
            log_step("Incident Submission & Read-Back", "FAIL", "Incident document could not be read back from Firestore")
            return
    except Exception as e:
        log_step("Incident Submission & Read-Back", "FAIL", str(e))
        return

    # 4. Genuine Gemini Analysis via running FastAPI backend
    print("\n[Step 5] Triggering real Gemini Multimodal Analysis via backend API...")
    try:
        from scripts.test_gemini_analysis import make_sample_png_base64
        valid_png_base64 = "data:image/png;base64," + make_sample_png_base64()
        
        analyze_payload = json.dumps({
            "title": test_incident_data["title"],
            "description": test_incident_data["description"],
            "category": test_incident_data["category"],
            "location": test_incident_data["location"],
            "latitude": test_incident_data["latitude"],
            "longitude": test_incident_data["longitude"],
            "image_base64": valid_png_base64,
            "user_language": "en"
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BACKEND_URL}/api/incidents/analyze",
            data=analyze_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {citizen_id_token}"
            }
        )
        t0 = time.time()
        res = urllib.request.urlopen(req, timeout=35)
        duration = round(time.time() - t0, 2)
        analysis = json.loads(res.read().decode())
        
        assert "severity_level" in analysis, "Missing severity_level"
        assert "urgency_score" in analysis, "Missing urgency_score"
        assert "suggested_resources" in analysis, "Missing suggested_resources"
        assert len(analysis["suggested_resources"]) > 0, "Empty suggested_resources"
        
        log_step("Genuine Gemini Multimodal Analysis", "PASS", 
                 f"Analyzed in {duration}s | Category: '{analysis['category']}' | Severity: {analysis['severity_level']}/5 | Urgency: {analysis['urgency_score']}/100 | Resources: {analysis['suggested_resources'][:2]}")
    except Exception as e:
        log_step("Genuine Gemini Multimodal Analysis", "FAIL", str(e))

    # 5. Dashboard & Map Live Synchronization Query
    print("\n[Step 6] Testing live query synchronization for Dashboard & Map...")
    try:
        q = db.collection("incidents").order_by("created_at", direction=firestore.Query.DESCENDING).limit(10)
        docs = [d.to_dict() for d in q.stream()]
        matching = [d for d in docs if d.get("title") == test_incident_data["title"]]
        if matching:
            log_step("Dashboard & Map Live Synchronization", "PASS", f"Incident appeared in live Firestore index query (matched {len(matching)} record)")
        else:
            log_step("Dashboard & Map Live Synchronization", "FAIL", "Incident not returned in indexed query stream")
    except Exception as e:
        log_step("Dashboard & Map Live Synchronization", "FAIL", str(e))

    # 6. Coordinator Resource Assignment via API
    print("\n[Step 7] Testing Coordinator Resource Assignment (Transactional)...")
    try:
        # Seed test resource
        db.collection("resources").document(TEST_RESOURCE_ID).set({
            "name": "E2E High-Volume Pump Unit 9",
            "type": "Flooding & Sump Pump Mitigation",
            "service_area": "Downtown & Sector 2",
            "availability": "Available",
            "capacity": "600 GPM submersible",
            "updated_at": now_iso,
            "is_demo": True
        })

        assign_payload = json.dumps({
            "incident_id": TEST_INCIDENT_ID,
            "resource_id": TEST_RESOURCE_ID,
            "notes": "E2E Coordinator dispatching emergency pump"
        }).encode("utf-8")

        assign_req = urllib.request.Request(
            f"{BACKEND_URL}/api/incidents/assign-resource",
            data=assign_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {coord_id_token}"
            }
        )
        assign_res = urllib.request.urlopen(assign_req, timeout=10)
        assign_data = json.loads(assign_res.read().decode())

        # Verify Firestore updates
        inc_snap = db.collection("incidents").document(TEST_INCIDENT_ID).get()
        res_snap = db.collection("resources").document(TEST_RESOURCE_ID).get()

        inc_dict = inc_snap.to_dict()
        res_dict = res_snap.to_dict()

        assert inc_dict.get("status") == "Resource Dispatched", f"Incident status is {inc_dict.get('status')}"
        assert inc_dict.get("assigned_resource_id") == TEST_RESOURCE_ID, "Assigned resource ID mismatch"
        assert res_dict.get("availability") == "Busy", f"Resource availability is {res_dict.get('availability')}"
        assert res_dict.get("assigned_incident") == TEST_INCIDENT_ID, "Assigned incident mismatch"

        log_step("Coordinator Resource Assignment", "PASS", 
                 f"Atomic transaction completed | Incident: '{inc_dict['status']}' | Resource '{res_dict['name']}': '{res_dict['availability']}'")
    except Exception as e:
        log_step("Coordinator Resource Assignment", "FAIL", str(e))

    # 7. Responder Field Progress Update via API
    print("\n[Step 8] Testing Responder Field Progress Update...")
    try:
        update_payload = json.dumps({
            "incident_id": TEST_INCIDENT_ID,
            "status": "In Progress",
            "responder_progress_note": "Field crew arrived on scene. Deployed 600 GPM suction hose into catch basin."
        }).encode("utf-8")

        resp_req = urllib.request.Request(
            f"{BACKEND_URL}/api/incidents/update-status",
            data=update_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {resp_id_token}"
            }
        )
        resp_res = urllib.request.urlopen(resp_req, timeout=10)
        resp_data = json.loads(resp_res.read().decode())

        inc_snap = db.collection("incidents").document(TEST_INCIDENT_ID).get()
        inc_dict = inc_snap.to_dict()

        assert inc_dict.get("status") == "In Progress", f"Status is {inc_dict.get('status')}"
        assert "Deployed 600 GPM" in inc_dict.get("responder_notes", ""), "Responder note missing"

        log_step("Responder Progress Update", "PASS", f"Status transitioned to 'In Progress' with note: '{inc_dict['responder_notes'][:45]}...'")
    except Exception as e:
        log_step("Responder Progress Update", "FAIL", str(e))

    # 8. Incident Resolution & Transactional Resource Release
    print("\n[Step 9] Testing Coordinator Incident Resolution & Automatic Resource Release...")
    try:
        resolve_payload = json.dumps({
            "incident_id": TEST_INCIDENT_ID,
            "status": "Resolved",
            "resolution_notes": "Catch basin cleared of debris; street water completely drained."
        }).encode("utf-8")

        resolve_req = urllib.request.Request(
            f"{BACKEND_URL}/api/incidents/update-status",
            data=resolve_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {coord_id_token}"
            }
        )
        resolve_res = urllib.request.urlopen(resolve_req, timeout=10)
        resolve_data = json.loads(resolve_res.read().decode())

        inc_snap = db.collection("incidents").document(TEST_INCIDENT_ID).get()
        res_snap = db.collection("resources").document(TEST_RESOURCE_ID).get()

        inc_dict = inc_snap.to_dict()
        res_dict = res_snap.to_dict()

        assert inc_dict.get("status") == "Resolved", f"Incident status is {inc_dict.get('status')}"
        assert res_dict.get("availability") == "Available", f"Resource availability is {res_dict.get('availability')}"
        assert res_dict.get("assigned_incident") is None, f"Resource assigned_incident is {res_dict.get('assigned_incident')}"
        assert resolve_data.get("released_resource_id") == TEST_RESOURCE_ID, "Response did not confirm released resource ID"

        log_step("Incident Resolution & Resource Release", "PASS", 
                 f"Incident status -> 'Resolved' | Resource '{res_dict['name']}' released -> 'Available' (assigned_incident: null)")
    except Exception as e:
        log_step("Incident Resolution & Resource Release", "FAIL", str(e))

    # 9. Clean up test records
    print("\n[Step 10] Cleaning up isolated test documents from Firestore...")
    try:
        db.collection("incidents").document(TEST_INCIDENT_ID).delete()
        db.collection("resources").document(TEST_RESOURCE_ID).delete()
        db.collection("users").document("e2e-coord-101").delete()
        db.collection("users").document("e2e-resp-202").delete()
        db.collection("users").document(TEST_REPORTER_UID).delete()
        log_step("Cleaned Up Test Documents", "PASS", "Deleted isolated test incident, resource, and user records")
    except Exception as e:
        log_step("Cleaned Up Test Documents", "FAIL", str(e))

    print("\n" + "=" * 65)
    print("                    E2E SUMMARY REPORT")
    print("=" * 65)
    all_passed = True
    for step, info in RESULTS.items():
        status = info["status"]
        if status != "PASS":
            all_passed = False
        print(f"[{status}] {step}: {info['details']}")

    if all_passed:
        print("\n[VERIFIED PASS] All CommunityOS end-to-end workflows completed successfully against real cloud services!")
    else:
        print("\n[VERIFIED FAIL] Some workflows did not pass. Inspect details above.")

if __name__ == "__main__":
    run_e2e()
