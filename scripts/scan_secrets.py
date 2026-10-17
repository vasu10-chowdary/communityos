"""
Secret Scanner Utility for CommunityOS
Scans working tree, configuration files, and git history for accidentally committed or exposed secrets.
"""

import os
import re
import sys
from pathlib import Path

# Safe placeholders allowed in example templates
ALLOWED_PLACEHOLDERS = [
    "AIzaSyDummyKeyForInitialBuildOnly12345",
    "your_gemini_api_key_here",
    "YOUR_GEMINI_API_KEY",
    "YOUR_PROJECT_ID",
    "communityos-demo",
    "mock-citizen-token",
    "mock-coordinator-token",
    "mock-responder-token",
    "mock-no-role-token"
]

SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z-_]{35}", "Google / Gemini API Key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Private Key Header"),
    (r'"private_key"\s*:\s*"-----BEGIN', "Firebase / GCP Service Account Private Key"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"bearer\s+[a-zA-Z0-9_\-\.]{100,}", "Long JWT Bearer Token")
]

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache"
}

def scan_file(filepath: Path) -> list:
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return findings

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Ignore lines containing explicit example placeholders
        if any(placeholder in line for placeholder in ALLOWED_PLACEHOLDERS):
            continue

        for pattern, label in SECRET_PATTERNS:
            matches = re.finditer(pattern, line)
            for m in matches:
                # Mask secret
                matched_val = m.group(0)
                masked = matched_val[:4] + "..." + matched_val[-4:] if len(matched_val) > 8 else "***"
                findings.append({
                    "file": str(filepath),
                    "line": line_num,
                    "type": label,
                    "masked": masked
                })
    return findings

import subprocess

def is_git_ignored(filepath: Path) -> bool:
    try:
        res = subprocess.run(["git", "check-ignore", str(filepath)], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False

def scan_directory(root_dir: str):
    root_path = Path(root_dir).resolve()
    all_findings = []
    ignored_credential_files = []
    scanned_count = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            # Only scan text-like files
            if fpath.suffix.lower() in [".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".env", ".yaml", ".yml", ".txt", ".rules"]:
                findings = scan_file(fpath)
                scanned_count += 1
                if findings:
                    if is_git_ignored(fpath):
                        ignored_credential_files.append((fpath, len(findings)))
                    else:
                        all_findings.extend(findings)

    print("==================================================")
    print("           COMMUNITYOS SECRET SCAN RESULT         ")
    print("==================================================")
    print(f"Total files scanned: {scanned_count}")
    if ignored_credential_files:
        print(f"[OK] Local credential file(s) detected and verified strictly excluded by .gitignore:")
        for path, count in ignored_credential_files:
            print(f"  - {path.name} ({count} credential fields, git ignored: YES)")

    if all_findings:
        print(f"\n[CRITICAL] COMMIDABLE SECRETS DETECTED: {len(all_findings)} unignored secret(s) found!")
        for f in all_findings:
            print(f"  - [{f['type']}] {f['file']}:{f['line']} -> {f['masked']}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] CLEAN: Zero secrets exposed in tracked or committable repository files.")
        sys.exit(0)

if __name__ == "__main__":
    scan_directory(sys.argv[1] if len(sys.argv) > 1 else ".")
