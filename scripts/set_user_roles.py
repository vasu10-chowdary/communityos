#!/usr/bin/env python3
"""
scripts/set_user_roles.py
Provision and configure user roles for CommunityOS:
- citizen
- coordinator
- responder

Sets custom claims via Firebase Auth Admin SDK (set_custom_user_claims) AND
synchronizes the role to the Firestore `users/{uid}` document for strict RBAC.

Supports:
  python scripts/set_user_roles.py --uid <UID> --role <citizen|coordinator|responder>
  python scripts/set_user_roles.py --email <EMAIL> --role <citizen|coordinator|responder>
  python scripts/set_user_roles.py --seed-demo (creates/provisions 3 standard demo persona accounts)
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
from firebase_admin import credentials, auth, firestore

ALLOWED_ROLES = ["citizen", "coordinator", "responder"]

DEMO_ACCOUNTS = [
    {
        "uid": "demo-citizen-uid",
        "email": "citizen@communityos.demo",
        "display_name": "Elena Citizen",
        "role": "citizen",
        "password": "DemoPassword123!",
    },
    {
        "uid": "demo-coordinator-uid",
        "email": "coordinator@communityos.demo",
        "display_name": "Marcus Coordinator",
        "role": "coordinator",
        "password": "DemoPassword123!",
    },
    {
        "uid": "demo-responder-uid",
        "email": "responder@communityos.demo",
        "display_name": "Sarah Responder",
        "role": "responder",
        "password": "DemoPassword123!",
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


def set_user_role(uid: str, role: str, email: str = None, display_name: str = None):
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role: '{role}'. Allowed roles are: {ALLOWED_ROLES}")

    # 1. Set custom claims in Firebase Auth token
    auth.set_custom_user_claims(uid, {"role": role})
    print(f"  [+] Auth custom claim set: uid='{uid}' -> {{'role': '{role}'}}")

    # 2. Synchronize role in Firestore `users/{uid}` document
    db = firestore.client()
    user_doc_ref = db.collection("users").document(uid)
    user_payload = {
        "uid": uid,
        "role": role,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if email:
        user_payload["email"] = email
    if display_name:
        user_payload["displayName"] = display_name

    user_doc_ref.set(user_payload, merge=True)
    print(f"  [+] Firestore document updated: users/{uid} -> role='{role}'")

    # 3. Verify custom claims
    user = auth.get_user(uid)
    print(f"  [✓] Verified user '{user.email or uid}': claims={user.custom_claims}")


def seed_demo_accounts():
    print("\n=======================================================")
    print("  COMMUNITYOS DEMO ACCOUNT PROVISIONER")
    print("=======================================================")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    for acc in DEMO_ACCOUNTS:
        uid = acc["uid"]
        email = acc["email"]
        role = acc["role"]
        display_name = acc["display_name"]
        password = acc["password"]

        print(f"\n[*] Provisioning {role.upper()} account: {email}")
        try:
            # Check if user already exists
            user = auth.get_user_by_email(email)
            print(f"    Existing user found with uid: {user.uid}")
            uid = user.uid
        except auth.UserNotFoundError:
            try:
                # Create user
                user = auth.create_user(
                    uid=uid,
                    email=email,
                    display_name=display_name,
                    password=password,
                )
                print(f"    Created new user: uid={user.uid}")
            except Exception as create_err:
                print(f"    User creation by UID failed ({create_err}), creating by email...")
                user = auth.create_user(
                    email=email,
                    display_name=display_name,
                    password=password,
                )
                uid = user.uid

        set_user_role(uid=uid, role=role, email=email, display_name=display_name)

    print("\n[OK] All demo persona accounts successfully provisioned and verified.")


def main():
    parser = argparse.ArgumentParser(description="Manage CommunityOS User Roles & Claims")
    parser.add_argument("--uid", default=None, help="Firebase user UID")
    parser.add_argument("--email", default=None, help="Firebase user email")
    parser.add_argument("--role", choices=ALLOWED_ROLES, default=None, help="Target role (citizen, coordinator, responder)")
    parser.add_argument("--seed-demo", action="store_true", help="Provision all 3 demo accounts (citizen, coordinator, responder)")
    parser.add_argument("--project", default=None, help="Firebase project ID")
    parser.add_argument("--key", default=None, help="Path to service account credentials JSON")
    args = parser.parse_args()

    init_firebase(project_id=args.project, service_account_path=args.key)

    if args.seed_demo:
        seed_demo_accounts()
        return

    if not args.role:
        print("[ERROR] Please specify --role <citizen|coordinator|responder> or use --seed-demo", file=sys.stderr)
        sys.exit(1)

    target_uid = args.uid
    target_email = args.email

    if not target_uid and target_email:
        try:
            user = auth.get_user_by_email(target_email)
            target_uid = user.uid
        except auth.UserNotFoundError:
            print(f"[ERROR] User with email '{target_email}' not found.", file=sys.stderr)
            sys.exit(1)

    if not target_uid:
        print("[ERROR] Must specify either --uid <UID> or --email <EMAIL>.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Assigning role '{args.role}' to UID: {target_uid}")
    set_user_role(uid=target_uid, role=args.role, email=target_email)
    print("[OK] Role assignment complete.")


if __name__ == "__main__":
    main()
