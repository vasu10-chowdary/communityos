import os
import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager
from app.core.config import settings

INITIAL_RESOURCES = [
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
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
        "notes": None,
        "is_demo": 1
    }
]

INITIAL_INCIDENTS = [
    {
        "id": "inc-demo-101",
        "title": "Severe Stormwater Backflow on North Oak Ave",
        "description": "Culvert is heavily obstructed by storm debris and tree limbs after torrential rain. Water has risen 1.5 feet over the sidewalk and is entering residential driveways.",
        "category": "Flooding and waterlogging",
        "severity": "High",
        "severity_level": 4,
        "urgency_score": 84,
        "status": "In Review",
        "location": "420 North Oak Ave, Ward 4",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "reporter_id": "citizen-demo-1",
        "reporter_name": "Elena Rostova (Community Monitor)",
        "is_demo": 1,
        "latest_analysis": json.dumps({
            "category": "Flooding and waterlogging",
            "severity": "High",
            "severity_level": 4,
            "urgency_score": 84,
            "explanation": "Rapid accumulation of stagnant flood water posing acute risk to residential basements and electrical ground meters.",
            "potential_risks": ["Basement flooding in low-lying homes", "Electrical conduit immersion", "Traffic disruption"],
            "recommended_next_actions": ["Deploy vacuum pump trailer", "Establish temporary road diversion barricades", "Clear storm grate intake"],
            "suggested_resources": ["High-Flow Submersible Trash Pump Trailer #1", "Drainage Intake Crew"],
            "uncertainties": ["Rate of rain influx over next 3 hours"],
            "human_review_required": True,
            "model_identifier": "gemini-3.5-flash",
            "provider": "Google Gen AI (Official SDK)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    },
    {
        "id": "inc-demo-102",
        "title": "Major Oak Fallen Across Pine Boulevard",
        "description": "High winds knocked down a 40-foot mature oak tree. Both vehicular lanes are blocked, and overhead telecommunication lines appear damaged.",
        "category": "Fallen trees and blocked roads",
        "severity": "Critical",
        "severity_level": 5,
        "urgency_score": 92,
        "status": "Reported",
        "location": "Pine Blvd & 8th Street Intersection",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "reporter_id": "citizen-demo-2",
        "reporter_name": "David Chen",
        "is_demo": 1,
        "latest_analysis": json.dumps({
            "category": "Fallen trees and blocked roads",
            "severity": "Critical",
            "severity_level": 5,
            "urgency_score": 92,
            "explanation": "Critical thoroughfare blockage completely halting emergency vehicle passage.",
            "potential_risks": ["Delayed ambulance transit", "Downed communication cables"],
            "recommended_next_actions": ["Dispatch municipal arborist team with heavy wood chipper", "Establish traffic detour"],
            "suggested_resources": ["Rapid Municipal Debris & Tree Clearing Squad"],
            "uncertainties": ["Live electrical energization on adjacent utility lines"],
            "human_review_required": True,
            "model_identifier": "gemini-3.5-flash",
            "provider": "Google Gen AI (Official SDK)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    }
]

def get_db_path() -> str:
    path = settings.DATABASE_PATH
    # If relative, anchor relative to backend directory or workspace
    if not os.path.isabs(path):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base_dir, path)
    return path

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def transaction():
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Incidents Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT DEFAULT 'Medium',
                severity_level INTEGER DEFAULT 3,
                urgency_score INTEGER DEFAULT 50,
                status TEXT DEFAULT 'Reported',
                location TEXT,
                latitude REAL,
                longitude REAL,
                reporter_id TEXT,
                reporter_name TEXT,
                image_url TEXT,
                image_base64 TEXT,
                assigned_resource_id TEXT,
                assigned_resource_name TEXT,
                assigned_by TEXT,
                last_updated_by TEXT,
                responder_notes TEXT,
                resolution_notes TEXT,
                duplicate_of TEXT,
                is_demo INTEGER DEFAULT 0,
                latest_analysis TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);")

        # 2. Resources Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                type TEXT NOT NULL,
                capacity TEXT,
                availability TEXT DEFAULT 'Available',
                service_area TEXT,
                location TEXT,
                contact TEXT,
                latitude REAL,
                longitude REAL,
                assigned_incident TEXT,
                notes TEXT,
                is_demo INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_avail ON resources(availability);")

        # 3. Duplicate Links Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_links (
                id TEXT PRIMARY KEY,
                primary_id TEXT NOT NULL,
                duplicate_id TEXT NOT NULL,
                reason TEXT,
                merged_by TEXT,
                merged_at TEXT NOT NULL
            );
        """)

        # 4. Users Table (Audit & Profiles)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'citizen',
                name TEXT,
                email TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        conn.commit()

        # Auto-seed standard resources if table is empty
        cursor.execute("SELECT COUNT(*) FROM resources;")
        if cursor.fetchone()[0] == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            for r in INITIAL_RESOURCES:
                cursor.execute("""
                    INSERT INTO resources (
                        id, name, category, type, capacity, availability,
                        service_area, location, contact, latitude, longitude,
                        assigned_incident, notes, is_demo, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    r["id"], r["name"], r["category"], r["type"], r["capacity"],
                    r["availability"], r["service_area"], r["location"], r["contact"],
                    r["latitude"], r["longitude"], r["assigned_incident"], r["notes"],
                    r["is_demo"], now_iso, now_iso
                ))
            conn.commit()

        # Auto-seed demo incidents if table is empty
        cursor.execute("SELECT COUNT(*) FROM incidents;")
        if cursor.fetchone()[0] == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            for inc in INITIAL_INCIDENTS:
                cursor.execute("""
                    INSERT INTO incidents (
                        id, title, description, category, severity, severity_level,
                        urgency_score, status, location, latitude, longitude,
                        reporter_id, reporter_name, is_demo, latest_analysis,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    inc["id"], inc["title"], inc["description"], inc["category"],
                    inc["severity"], inc["severity_level"], inc["urgency_score"],
                    inc["status"], inc["location"], inc["latitude"], inc["longitude"],
                    inc["reporter_id"], inc["reporter_name"], inc["is_demo"],
                    inc["latest_analysis"], now_iso, now_iso
                ))
            conn.commit()

def dict_from_row(row: sqlite3.Row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if "latest_analysis" in d and d["latest_analysis"]:
        try:
            d["latest_analysis"] = json.loads(d["latest_analysis"])
        except Exception:
            pass
    if "is_demo" in d:
        d["is_demo"] = bool(d["is_demo"])
    return d
