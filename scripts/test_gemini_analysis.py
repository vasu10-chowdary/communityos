#!/usr/bin/env python3
"""
scripts/test_gemini_analysis.py
Comprehensive live test suite for CommunityOS Gemini AI Integration:
1. Live text-only incident analysis request against Gemini API.
2. Live multimodal (image + text) incident analysis request.
3. Response parsing, schema validation, and score bounds checks.
4. Error handling test: invalid key returns failure (no fake success).
5. Error handling test: missing key returns HTTP 503 (no fake success).

NEVER exposes or prints API keys.
"""

import os
import sys
import asyncio
import base64
from pathlib import Path
from dotenv import load_dotenv

backend_env = Path(__file__).resolve().parent.parent / "backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env)

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException
from app.core.config import settings
from app.schemas.incident import IncidentAnalysisRequest, IncidentAnalysisResponse
from app.services.gemini_service import analyze_incident_with_gemini


import zlib
import struct

def make_sample_png_base64() -> str:
    """Creates a valid 64x64 PNG in base64 suitable for vision models."""
    width, height = 64, 64
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter type None
        for x in range(width):
            # Forest green / blue split
            raw_data.extend([40, 120, 180] if y > 32 else [34, 139, 34])

    idat_data = zlib.compress(bytes(raw_data))
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data))
    idat = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc

    iend_crc = struct.pack(">I", zlib.crc32(b"IEND"))
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc

    png_bytes = signature + ihdr + idat + iend
    return base64.b64encode(png_bytes).decode("ascii")


async def run_live_gemini_tests():
    print("=" * 65)
    print("       COMMUNITYOS LIVE GEMINI API VERIFICATION")
    print("=" * 65)

    real_key = os.getenv("GEMINI_API_KEY", "")
    if not real_key:
        print("[FAIL] GEMINI_API_KEY is not configured in backend/.env!")
        sys.exit(1)

    print(f"[*] Confirmed GEMINI_API_KEY configured (length: {len(real_key)}, model: {settings.GEMINI_MODEL})")

    # ---------------- TEST 1: REALISTIC TEXT-ONLY ANALYSIS ----------------
    print("\n[Test 1] Executing genuine text-only incident analysis...")
    text_request = IncidentAnalysisRequest(
        title="Severe stormwater drain overflow flooding residential basements",
        description="Water is overflowing rapidly from storm grates along Maple St. Floodwater has reached 18 inches, entering garages and threatening electrical utility boxes on ground level.",
        category="Flooding and waterlogging",
        location="450 Maple Street, Ward 4"
    )

    t0 = asyncio.get_event_loop().time()
    try:
        response_text = await analyze_incident_with_gemini(text_request)
        elapsed = asyncio.get_event_loop().time() - t0
        print(f"  [OK] Gemini API responded in {elapsed:.2f}s")
        print(f"  - Category: {response_text.category}")
        print(f"  - Severity Level: {response_text.severity_level}/5 ({response_text.severity})")
        print(f"  - Urgency Score: {response_text.urgency_score}/100")
        print(f"  - Explanation: {response_text.explanation[:90]}...")
        print(f"  - Potential Risks ({len(response_text.potential_risks)}): {response_text.potential_risks[:2]}")
        print(f"  - Recommended Actions ({len(response_text.recommended_next_actions)}): {response_text.recommended_next_actions[:2]}")
        print(f"  - Suggested Resources: {response_text.suggested_resources[:2]}")

        # Assertions on schema integrity
        assert 1 <= response_text.severity_level <= 5, "severity_level out of bounds"
        assert 1 <= response_text.urgency_score <= 100, "urgency_score out of bounds"
        assert len(response_text.explanation) > 10, "explanation too short"
        assert len(response_text.potential_risks) >= 1, "potential_risks empty"
        assert len(response_text.recommended_next_actions) >= 1, "recommended_next_actions empty"
        print("  [OK] Text-only schema and bounds verification passed.")
    except Exception as e:
        print(f"  [FAIL] Text-only incident analysis failed: {e}")
        sys.exit(1)

    # ---------------- TEST 2: MULTIMODAL (IMAGE + TEXT) ANALYSIS ----------------
    print("\n[Test 2] Executing genuine multimodal (image + text) incident analysis...")
    sample_png = make_sample_png_base64()
    multimodal_request = IncidentAnalysisRequest(
        title="Mature Oak Fallen Across Pine Boulevard",
        description="High winds knocked down a 40-foot mature oak tree. Both vehicular lanes are blocked, and overhead telecommunication lines appear damaged.",
        category="Fallen trees and blocked roads",
        location="Pine Blvd & 8th Street",
        image_base64=sample_png,
        image_mime_type="image/png"
    )

    t0 = asyncio.get_event_loop().time()
    try:
        response_mm = await analyze_incident_with_gemini(multimodal_request)
        elapsed = asyncio.get_event_loop().time() - t0
        print(f"  [OK] Gemini Multimodal API responded in {elapsed:.2f}s")
        print(f"  - Category: {response_mm.category}")
        print(f"  - Severity Level: {response_mm.severity_level}/5 ({response_mm.severity})")
        print(f"  - Urgency Score: {response_mm.urgency_score}/100")
        print(f"  - Explanation: {response_mm.explanation[:90]}...")
        print(f"  - Visual Evidence Detected: {response_mm.visual_evidence_detected}")
        print(f"  - Suggested Resources: {response_mm.suggested_resources[:2]}")
        print("  [OK] Multimodal incident analysis passed.")
    except Exception as e:
        print(f"  [FAIL] Multimodal incident analysis failed: {e}")
        sys.exit(1)

    # ---------------- TEST 3: INVALID API KEY HANDLING ----------------
    print("\n[Test 3] Verifying invalid API key behavior (must reject, never fake success)...")
    settings.GEMINI_API_KEY = "INVALID_MOCK_GEMINI_KEY_99999"
    try:
        await analyze_incident_with_gemini(text_request)
        print("  [FAIL] Expected failure with invalid key, but got success!")
        sys.exit(1)
    except HTTPException as http_err:
        print(f"  [OK] Rejected invalid key as expected with HTTP {http_err.status_code}")
    except Exception as exc:
        print(f"  [OK] Rejected invalid key as expected with exception: {type(exc).__name__}")

    # ---------------- TEST 4: MISSING API KEY HANDLING ----------------
    print("\n[Test 4] Verifying missing API key behavior (must raise HTTP 503, never fake success)...")
    settings.GEMINI_API_KEY = ""
    try:
        await analyze_incident_with_gemini(text_request)
        print("  [FAIL] Expected HTTP 503 with missing key, but got success!")
        sys.exit(1)
    except HTTPException as http_err:
        assert http_err.status_code == 503, f"Expected 503, got {http_err.status_code}"
        assert http_err.detail.get("error") == "GEMINI_NOT_CONFIGURED"
        print(f"  [OK] Correctly raised HTTP 503 ({http_err.detail.get('error')})")

    # Restore key
    settings.GEMINI_API_KEY = real_key

    print("\n" + "=" * 65)
    print("  [SUCCESS] All Live Gemini API and Error Handling checks passed!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_live_gemini_tests())
