import subprocess
import re
import os
import sys

def setup_env():
    print("[*] Retrieving Firebase Web App SDK configuration...")
    try:
        # Run firebase apps:sdkconfig
        res = subprocess.run(
            ["npx", "firebase-tools", "apps:sdkconfig", "WEB", "1:551008027193:web:d037e391bf9e43e20a83e8", "--project", "communityos-a36f0"],
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode != 0:
            print(f"[FAIL] Could not retrieve SDK config: {res.stderr}")
            sys.exit(1)

        raw = res.stdout

        # Parse config fields from JS or JSON output using regex
        api_key_m = re.search(r'["\']?apiKey["\']?\s*:\s*["\']([^"\']+)["\']', raw)
        auth_domain_m = re.search(r'["\']?authDomain["\']?\s*:\s*["\']([^"\']+)["\']', raw)
        project_id_m = re.search(r'["\']?projectId["\']?\s*:\s*["\']([^"\']+)["\']', raw)
        storage_bucket_m = re.search(r'["\']?storageBucket["\']?\s*:\s*["\']([^"\']+)["\']', raw)
        sender_id_m = re.search(r'["\']?messagingSenderId["\']?\s*:\s*["\']([^"\']+)["\']', raw)
        app_id_m = re.search(r'["\']?appId["\']?\s*:\s*["\']([^"\']+)["\']', raw)

        if not (api_key_m and project_id_m and app_id_m):
            print("[FAIL] Could not parse required Firebase configuration keys from output.")
            sys.exit(1)

        api_key = api_key_m.group(1).strip()
        auth_domain = auth_domain_m.group(1).strip() if auth_domain_m else f"{project_id_m.group(1)}.firebaseapp.com"
        project_id = project_id_m.group(1).strip()
        storage_bucket = storage_bucket_m.group(1).strip() if storage_bucket_m else f"{project_id}.appspot.com"
        sender_id = sender_id_m.group(1).strip() if sender_id_m else "551008027193"
        app_id = app_id_m.group(1).strip()

        env_lines = [
            "# CommunityOS Local Frontend Environment Configuration",
            "# Auto-generated from Firebase Web App (communityos-a36f0)",
            "NEXT_PUBLIC_ENVIRONMENT=development",
            f"NEXT_PUBLIC_FIREBASE_API_KEY={api_key}",
            f"NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN={auth_domain}",
            f"NEXT_PUBLIC_FIREBASE_PROJECT_ID={project_id}",
            f"NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET={storage_bucket}",
            f"NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID={sender_id}",
            f"NEXT_PUBLIC_FIREBASE_APP_ID={app_id}",
            "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000\n"
        ]

        dest = os.path.join("frontend", ".env.local")
        with open(dest, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines))

        print(f"[SUCCESS] Configured {dest} with real Firebase parameters.")
        print("  - Project: " + project_id)
        print("  - App ID: " + app_id)
        print("  - Auth Domain: " + auth_domain)
        print("  - API Key: [CONFIGURED SAFELY WITHOUT LOGGING]")

    except Exception as e:
        print(f"[ERROR] Failed to configure frontend environment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_env()
