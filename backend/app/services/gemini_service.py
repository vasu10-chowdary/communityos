import json
import asyncio
from datetime import datetime, timezone
from google import genai
from google.genai import types
from google.genai.errors import APIError
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from app.core.validation import validate_and_decode_image
from app.schemas.incident import IncidentAnalysisRequest, IncidentAnalysisResponse

SYSTEM_INSTRUCTION = """
You are an expert Multimodal AI Emergency Risk & Heuristic Prioritization Engine for CommunityOS (a community emergency intelligence platform).
Your role:
1. Objectively evaluate community hazard reports using text descriptions and optional attached photograph evidence.
2. Support multilingual user inputs (e.g., Spanish, French, Hindi, Tagalog, etc.) and analyze their actual meaning while providing analysis in English with respect to regional context.
3. If an image is provided:
   - Identify concrete visual evidence (water level, fallen branches, wire exposure, structural cracks, submerged vehicles).
   - Explicitly note visual evidence cues in `visual_evidence_detected`.
   - IMPORTANT: Never claim or guess a precise GPS coordinate or street address from an image alone; rely strictly on reported coordinates/landmarks.
   - If image does not show a hazard or is blurry, note it under `uncertainties`.
4. Output strict JSON with:
   - category (Standardized: "Flooding and waterlogging", "Blocked drainage", "Water shortages", "Fallen trees and blocked roads", "Damaged infrastructure", "Electrical hazards", "Other community assistance requests")
   - severity_level (Integer 1 to 5: 1=Minor inconvenience, 2=Moderate, 3=Substantial disruption, 4=Severe hazard, 5=Life/Safety Critical)
   - severity ("Low" for 1-2, "Medium" for 3, "High" for 4, "Critical" for 5)
   - urgency_score (Integer 1 to 100)
   - explanation (Evidence-based explanation citing reported observations)
   - visual_evidence_detected (Array of visual observations if image present, otherwise empty array)
   - potential_risks (Array of cascading risks)
   - uncertainties (Array of unknowns, e.g. unknown electrical energization, weather forecast)
   - recommended_next_actions (Array of immediate actions)
   - suggested_resources (Array of needed unit types: pumps, tree removal crews, water tankers, medical triage, etc.)
   - human_review_required (Boolean, default true)
"""

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)

# Retry helper for transient network or server errors (1 retry)
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, APIError)),
    reraise=True
)
def _generate_content_sync(client, model: str, contents: list):
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

async def analyze_incident_with_gemini(data: IncidentAnalysisRequest) -> IncidentAnalysisResponse:
    contents_payload = []

    # If image attached, validate size, MIME type, magic bytes, and decode first
    if data.image_base64:
        image_bytes, detected_mime = validate_and_decode_image(
            image_base64=data.image_base64,
            mime_type=data.image_mime_type
        )
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=detected_mime,
        )
        contents_payload.append(image_part)

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "GEMINI_NOT_CONFIGURED",
                "message": "GEMINI_API_KEY is not configured on the server. Please set it in backend/.env or Cloud Run environment variables.",
                "setup_guide": "Add your GEMINI_API_KEY into backend/.env or Cloud Run environment variables to enable real AI triage."
            }
        )

    client = get_gemini_client()

    prompt_text = f"""
    Analyze the following community incident report:
    Title: {data.title}
    Description: {data.description}
    User Language Hint: {data.user_language}
    Reported Category: {data.category or 'Not specified'}
    Location: {data.location or 'Not provided'}
    Coordinates: {data.latitude}, {data.longitude}
    Has Attached Photograph: {'Yes' if data.image_base64 else 'No (Text-only intake)'}

    Strict JSON Schema:
    {{
      "category": "Flooding and waterlogging" | "Blocked drainage" | "Water shortages" | "Fallen trees and blocked roads" | "Damaged infrastructure" | "Electrical hazards" | "Other community assistance requests",
      "severity_level": <int 1 to 5>,
      "severity": "Low" | "Medium" | "High" | "Critical",
      "urgency_score": <int 1 to 100>,
      "explanation": "<evidence-based reasoning citing visual or textual cues>",
      "visual_evidence_detected": ["<cues seen in photo>"],
      "potential_risks": ["<risk 1>", "<risk 2>"],
      "uncertainties": ["<uncertainty 1>"],
      "recommended_next_actions": ["<action 1>", "<action 2>"],
      "suggested_resources": ["<resource type 1>", "<resource type 2>"],
      "human_review_required": true
    }}
    """
    contents_payload.append(prompt_text)

    # Execute with timeout and retry
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_generate_content_sync, client, settings.GEMINI_MODEL, contents_payload),
            timeout=settings.GEMINI_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Gemini API analysis timed out after {settings.GEMINI_TIMEOUT_SECONDS} seconds."
        )
    except APIError as api_err:
        err_msg = str(api_err).lower()
        if "quota" in err_msg or "resource_exhausted" in err_msg or "429" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota or rate limit exceeded. Please try again shortly."
            )
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API upstream error: {str(api_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API analysis encountered an unexpected error: {str(e)}"
        )

    if not response or not response.text:
        raise HTTPException(status_code=502, detail="Empty response received from Gemini API.")

    try:
        parsed = json.loads(response.text)
    except Exception as parse_err:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse Gemini structured JSON response: {str(parse_err)}"
        )

    # Normalize severity level (1-5)
    sev_lvl = int(parsed.get("severity_level", 3))
    if sev_lvl < 1: sev_lvl = 1
    if sev_lvl > 5: sev_lvl = 5

    severity_str = parsed.get("severity")
    if not severity_str:
        if sev_lvl <= 2: severity_str = "Low"
        elif sev_lvl == 3: severity_str = "Medium"
        elif sev_lvl == 4: severity_str = "High"
        else: severity_str = "Critical"

    return IncidentAnalysisResponse(
        category=parsed.get("category", data.category or "Other community assistance requests"),
        severity_level=sev_lvl,
        severity=severity_str,
        urgency_score=int(parsed.get("urgency_score", 50)),
        explanation=parsed.get("explanation", "Assessment synthesized from reported details."),
        visual_evidence_detected=parsed.get("visual_evidence_detected", []),
        potential_risks=parsed.get("potential_risks", []),
        uncertainties=parsed.get("uncertainties", []),
        recommended_next_actions=parsed.get("recommended_next_actions", []),
        suggested_resources=parsed.get("suggested_resources", []),
        human_review_required=bool(parsed.get("human_review_required", True)),
        model_identifier=settings.GEMINI_MODEL,
        provider="Google Gen AI (Official SDK)",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
