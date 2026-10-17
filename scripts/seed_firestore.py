"""
Seed and Reset Script for CommunityOS Evaluator Experience
Seeds realistic municipal and community emergency reports into Cloud Firestore,
and provides a safe reset mechanism for records tagged with is_demo=True.
"""

import os
import sys
import argparse
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore

DEMO_INCIDENTS = [
    {
        "id": "inc-demo-101",
        "title": "Severe Stormwater Backflow on North Oak Ave",
        "description": "Culvert is heavily obstructed by storm debris and tree limbs after torrential rain. Water has risen 1.5 feet over the sidewalk and is entering residential driveways.",
        "category": "Flooding and waterlogging",
        "severity": "High",
        "status": "In Review",
        "location": "420 North Oak Ave, Ward 4",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": "evaluator-demo-user",
        "reporter_name": "Elena Rostova (Community Monitor)",
        "is_demo": True,
        "latest_analysis": {
            "category": "Flooding and waterlogging",
            "severity": "High",
            "urgency_score": 84,
            "explanation": "Rapid accumulation of stagnant flood water posing acute risk to residential basements and electrical ground meters.",
            "potential_risks": ["Basement flooding in low-lying homes", "Electrical conduit immersion", "Traffic disruption"],
            "recommended_next_actions": ["Deploy vacuum pump trailer", "Establish temporary road diversion barricades", "Clear storm grate intake"],
            "suggested_resources": ["Stormwater Suction Pump Unit A", "Civic Safety Barrier Kit"],
            "uncertainties": ["Rate of rain influx over next 3 hours"],
            "human_review_required": True,
            "model_identifier": "gemini-2.5-flash",
            "provider": "Google Gen AI",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    },
    {
        "id": "inc-demo-102",
        "title": "Major Oak Fallen Across Pine Boulevard",
        "description": "High winds knocked down a 40-foot mature oak tree. Both vehicular lanes are blocked, and overhead telecommunication lines appear damaged.",
        "category": "Fallen trees and blocked roads",
        "severity": "Critical",
        "status": "Resource Dispatched",
        "location": "Pine Blvd & 8th Street Intersection",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": "evaluator-demo-user",
        "reporter_name": "David Chen",
        "is_demo": True,
        "assigned_resource_id": "res-demo-201",
        "assigned_resource_name": "Arborist ArborCare Crew #1"
    },
    {
        "id": "inc-demo-103",
        "title": "Municipal Water Pipe Fracture & Pressure Drop",
        "description": "Sub-surface pipe fracture near neighborhood park has flooded lawn and left over 180 residences with near-zero tap water pressure.",
        "category": "Water shortages",
        "severity": "High",
        "status": "Reported",
        "location": "Cedar Park Greenbelt, Zone B",
        "latitude": 37.7690,
        "longitude": -122.4467,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": "evaluator-demo-user",
        "reporter_name": "Marcus Bell",
        "is_demo": True
    },
    {
        "id": "inc-demo-104",
        "title": "Clearing of Blocked Catch Basin at Market St",
        "description": "Leaves, construction runoff and sediment completely choking stormwater intake outside the central marketplace.",
        "category": "Blocked drainage",
        "severity": "Low",
        "status": "Resolved",
        "location": "Market St & 5th Avenue",
        "latitude": 37.7810,
        "longitude": -122.4080,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": "evaluator-demo-user",
        "reporter_name": "Community Sanitation Group",
        "is_demo": True
    }
]

DEMO_RESOURCES = [
    {
        "id": "res-demo-201",
        "name": "Arborist ArborCare Crew #1",
        "type": "Heavy Tree & Debris Removal",
        "service_area": "Metro Central & North",
        "availability": "Busy",
        "capacity": "2 Chainsaws, 1 Wood Chipper, 4 Operators",
        "assigned_incident": "inc-demo-102",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": True
    },
    {
        "id": "res-demo-202",
        "name": "Municipal Drainage & High-Flow Vacuum Unit",
        "type": "Flooding & Sump Pump Mitigation",
        "service_area": "District 3 & Ward 4",
        "availability": "Available",
        "capacity": "500 GPM Submersible Pump, 120ft Hose",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": True
    },
    {
        "id": "res-demo-203",
        "name": "Civic Water Tanker Distribution #4",
        "type": "Emergency Potable Water Logistics",
        "service_area": "Zone B & Hillside",
        "availability": "Available",
        "capacity": "3,000 Gallons Potable Drinking Water",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": True
    }
]

def init_firestore(project_id="communityos-demo", key_path=None):
    if not firebase_admin._apps:
        if key_path and os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {"projectId": project_id})
        else:
            firebase_admin.initialize_app(options={"projectId": project_id})
    return firestore.client()

def seed_database(db):
    print("🚀 Seeding demonstration records into Firestore...")
    for inc in DEMO_INCIDENTS:
        doc_id = inc["id"]
        db.collection("incidents").document(doc_id).set(inc)
        print(f"  [+] Incident added: {inc['title']} ({doc_id})")

    for res in DEMO_RESOURCES:
        doc_id = res["id"]
        db.collection("resources").document(doc_id).set(res)
        print(f"  [+] Resource added: {res['name']} ({doc_id})")

    print("✅ Seed completed successfully. Evaluator demo data ready.")

def reset_database(db, confirm=False):
    if not confirm:
        print("❌ Reset aborted. You must supply --confirm to delete records tagged with is_demo=True.")
        return
    
    print("🧹 Purging DEMO-tagged records from Firestore...")
    # Safe query: only delete where is_demo == True
    incidents = db.collection("incidents").where("is_demo", "==", True).stream()
    count_inc = 0
    for doc in incidents:
        doc.reference.delete()
        count_inc += 1
    
    resources = db.collection("resources").where("is_demo", "==", True).stream()
    count_res = 0
    for doc in resources:
        doc.reference.delete()
        count_res += 1

    print(f"✅ Reset complete. Purged {count_inc} demo incidents and {count_res} demo resources.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CommunityOS Firestore Seed & Reset CLI")
    parser.add_argument("--action", choices=["seed", "reset"], default="seed")
    parser.add_argument("--confirm", action="store_true", help="Confirm deletion during reset")
    parser.add_argument("--project", default="communityos-demo", help="Firebase project ID")
    parser.add_argument("--key", default="", help="Path to service account key json")

    args = parser.parse_args()

    try:
        db = init_firestore(project_id=args.project, key_path=args.key if args.key else None)
        if args.action == "seed":
            seed_database(db)
        elif args.action == "reset":
            reset_database(db, confirm=args.confirm)
    except Exception as e:
        print(f"⚠️ Notice: Local execution without live GCP service credentials encountered: {e}")
        print("ℹ️ Note: Seed dataset is bundled directly into the frontend repository for offline evaluation.")
