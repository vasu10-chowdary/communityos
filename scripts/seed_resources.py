#!/usr/bin/env python3
"""
scripts/seed_resources.py
Seed script for CommunityOS Cloud Firestore `resources` collection.
Seeds civic and emergency response assets:
pumps, cleanup teams, volunteers, medical assistance, and water tankers.

Supports live Cloud Firestore or local Firestore emulator via FIRESTORE_EMULATOR_HOST.
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Attempt to load backend .env if present
env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)

import firebase_admin
from firebase_admin import credentials, firestore

CIVIC_RESOURCES = [
    {
        "id": "res-pump-01",
        "name": "High-Flow Submersible Trash Pump Trailer #1",
        "category": "pumps",
        "type": "Flooding & Dewatering Equipment",
        "capacity": "1,200 GPM, 3-inch discharge, 250ft hose",
        "availability": "Available",
        "service_area": "Ward 4, Downtown, Waterfront",
        "location": "Central Public Works Depot, Bay 3",
        "contact": "pw-dispatch@city.gov / 555-0141",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-pump-02",
        "name": "Emergency Storm Sump Pump Unit #2",
        "category": "pumps",
        "type": "Basement & Underpass Extraction",
        "capacity": "600 GPM Portable Submersible",
        "availability": "Available",
        "service_area": "North Hills & West Valley",
        "location": "North Substation Yard",
        "contact": "storm-ops@city.gov / 555-0142",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-cleanup-01",
        "name": "Rapid Municipal Debris & Tree Clearing Squad",
        "category": "cleanup teams",
        "type": "Heavy Obstruction & Arborist Crew",
        "capacity": "2 Commercial Chainsaws, 1 Heavy Wood Chipper, 5 Techs",
        "availability": "Available",
        "service_area": "Citywide Primary Arterials",
        "location": "Forestry Maintenance Yard",
        "contact": "tree-crew@city.gov / 555-0178",
        "latitude": 37.7690,
        "longitude": -122.4467,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-cleanup-02",
        "name": "Sanitation Catch Basin & Drain Intake Crew",
        "category": "cleanup teams",
        "type": "Drainage Maintenance & Jetting",
        "capacity": "High-Pressure Hydro-Jet Truck & Mechanical Grate Lifter",
        "availability": "Available",
        "service_area": "Commercial Corridor & Central Transit Loop",
        "location": "Sanitation District 1 Facility",
        "contact": "sanitation-dispatch@city.gov / 555-0182",
        "latitude": 37.7810,
        "longitude": -122.4080,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-volunteer-01",
        "name": "Community CERT Volunteer Brigade West",
        "category": "volunteers",
        "type": "Trained Citizen Emergency Response",
        "capacity": "18 Trained CERT Volunteers, Sandbagging & Traffic Escort",
        "availability": "Available",
        "service_area": "Sunset, Richmond, Westside",
        "location": "West Community Center Command Post",
        "contact": "cert-west@volunteers.org / 555-0199",
        "latitude": 37.7550,
        "longitude": -122.4820,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-medical-01",
        "name": "Emergency Mobile Paramedic Quick Response Unit",
        "category": "medical assistance",
        "type": "Field Triage & First Aid Response",
        "capacity": "2 Paramedics, Advanced Life Support Kit, Oxygen, Defibrillator",
        "availability": "Available",
        "service_area": "Citywide High-Priority Incidents",
        "location": "Station 9 Emergency Bay",
        "contact": "ems-lead@health.gov / 555-0112",
        "latitude": 37.7705,
        "longitude": -122.4200,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "res-tanker-01",
        "name": "Civic Potable Water Tanker 3,500 Gal #1",
        "category": "water tankers",
        "type": "Emergency Clean Water Distribution",
        "capacity": "3,500 Gallons Certified Drinking Water, 8 Tap Dispensers",
        "availability": "Available",
        "service_area": "Neighborhood Outage Zones",
        "location": "Water Utility Reservoir Station 4",
        "contact": "potable-ops@waterdept.gov / 555-0133",
        "latitude": 37.7600,
        "longitude": -122.4350,
        "assigned_incident": None,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
]


def init_firebase(project_id=None, service_account_path=None):
    if not firebase_admin._apps:
        project_id = project_id or os.getenv("FIREBASE_PROJECT_ID")
        service_account_path = service_account_path or os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

        if os.getenv("FIRESTORE_EMULATOR_HOST") and not os.getenv("GCLOUD_PROJECT"):
            os.environ["GCLOUD_PROJECT"] = project_id or "demo-communityos"

        if service_account_path and not os.path.isabs(service_account_path):
            candidate_paths = [
                Path(service_account_path),
                Path(__file__).resolve().parent.parent / service_account_path,
                Path(__file__).resolve().parent.parent / "backend" / service_account_path,
            ]
            for cp in candidate_paths:
                if cp.exists():
                    service_account_path = str(cp)
                    break

        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
            print(f"[*] Initialized Firebase Admin SDK with service account: {service_account_path}")
        elif project_id:
            firebase_admin.initialize_app(options={"projectId": project_id})
            print(f"[*] Initialized Firebase Admin SDK with project: {project_id}")
        else:
            firebase_admin.initialize_app()
            print("[*] Initialized Firebase Admin SDK with default credentials")

    return firestore.client()


def seed_resources(db):
    print(f"\n=======================================================")
    print(f"  COMMUNITYOS FIRESTORE RESOURCE SEEDER")
    print(f"=======================================================")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Target Collection: resources")
    print(f"Total Resources to seed: {len(CIVIC_RESOURCES)}\n")

    seeded_count = 0
    for res in CIVIC_RESOURCES:
        doc_ref = db.collection("resources").document(res["id"])
        doc_ref.set(res, merge=True)
        print(f"  [+] Seeded [{res['category'].upper()}] {res['name']} ({res['id']}) - {res['availability']}")
        seeded_count += 1

    print(f"\n[OK] Successfully seeded {seeded_count} emergency resources into Firestore.")


def main():
    parser = argparse.ArgumentParser(description="Seed Civic Resources into Firestore")
    parser.add_argument("--project", default=None, help="Firebase project ID")
    parser.add_argument("--key", default=None, help="Path to service account credentials JSON")
    args = parser.parse_args()

    try:
        db = init_firebase(project_id=args.project, service_account_path=args.key)
        seed_resources(db)
    except Exception as exc:
        print(f"\n[ERROR] Seeding failed: {exc}", file=sys.stderr)
        if "Could not automatically determine credentials" in str(exc) or "DefaultCredentialsError" in str(exc):
            print("\nHint: To seed real Firestore, supply credentials via:", file=sys.stderr)
            print("  python scripts/seed_resources.py --project <PROJECT_ID> --key <SERVICE_ACCOUNT.json>", file=sys.stderr)
            print("Or set FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT_KEY in backend/.env", file=sys.stderr)
            print("To run against local emulator, set FIRESTORE_EMULATOR_HOST=127.0.0.1:8080", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
