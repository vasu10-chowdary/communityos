import base64
from typing import Optional, Tuple
from fastapi import HTTPException

ALLOWED_MIME_TYPES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"]  # WebP container begins with 'RIFF'
}

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_BASE64_LENGTH = 7 * 1024 * 1024     # ~7 MB base64 for 5MB binary

def validate_and_decode_image(image_base64: str, mime_type: Optional[str] = None) -> Tuple[bytes, str]:
    """
    Validates base64 image string:
    - Enforces length and size limits (max 5MB)
    - Enforces allowed MIME types (jpeg, png, webp)
    - Validates magic bytes matching the declared MIME type
    Returns (decoded_bytes, detected_mime_type)
    """
    if not image_base64 or not image_base64.strip():
        raise HTTPException(status_code=400, detail="Empty image data provided.")

    clean_b64 = image_base64.strip()

    # Detect MIME type from data URL if present e.g. "data:image/jpeg;base64,..."
    if clean_b64.startswith("data:"):
        parts = clean_b64.split(",", 1)
        if len(parts) == 2:
            header, clean_b64 = parts
            header_clean = header.split(";")[0].replace("data:", "").strip().lower()
            if header_clean in ALLOWED_MIME_TYPES:
                mime_type = header_clean
        else:
            raise HTTPException(status_code=400, detail="Malformed data URL format.")

    if len(clean_b64) > MAX_BASE64_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Image base64 payload exceeds the 5MB size limit ({len(clean_b64)} chars)."
        )

    try:
        decoded_bytes = base64.b64decode(clean_b64, validate=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image encoding: {str(e)}")

    if len(decoded_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Decoded image size ({len(decoded_bytes)} bytes) exceeds the maximum allowed 5MB."
        )

    # Detect/verify MIME type from magic bytes if not specified
    matched_mime = None
    for m_type, signatures in ALLOWED_MIME_TYPES.items():
        for sig in signatures:
            if decoded_bytes.startswith(sig):
                matched_mime = m_type
                # Additional check for WebP: bytes 8-12 must be WEBP
                if m_type == "image/webp" and len(decoded_bytes) >= 12:
                    if decoded_bytes[8:12] != b"WEBP":
                        matched_mime = None
                break
        if matched_mime:
            break

    if not matched_mime:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Allowed formats are JPEG, PNG, and WebP."
        )

    # If MIME type was declared, check that it matches magic bytes
    if mime_type and mime_type.lower() != matched_mime:
        raise HTTPException(
            status_code=400,
            detail=f"MIME type mismatch: declared '{mime_type}' but file signatures indicate '{matched_mime}'."
        )

    return decoded_bytes, matched_mime
