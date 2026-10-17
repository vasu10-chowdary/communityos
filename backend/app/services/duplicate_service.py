import math
from typing import List, Dict, Any
from app.schemas.incident import DuplicateCheckRequest, DuplicateCheckResponse, DuplicateMatch

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def token_similarity(text1: str, text2: str) -> float:
    tokens1 = set(text1.lower().replace(",", " ").replace(".", " ").split())
    tokens2 = set(text2.lower().replace(",", " ").replace(".", " ").split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / float(len(union))

def detect_duplicates(req: DuplicateCheckRequest) -> DuplicateCheckResponse:
    matches: List[DuplicateMatch] = []
    
    for inc in req.existing_incidents:
        inc_id = inc.get("id", "")
        title = inc.get("title", "")
        desc = inc.get("description", "")
        category = inc.get("category", "")
        lat = inc.get("latitude")
        lon = inc.get("longitude")

        # 1. Category comparison
        category_match = (category.lower() == req.category.lower())
        
        # 2. Text similarity
        text_sim = token_similarity(f"{req.title} {req.description}", f"{title} {desc}")

        # 3. Geo proximity
        distance = None
        geo_score = 0.0
        if req.latitude is not None and req.longitude is not None and lat is not None and lon is not None:
            distance = haversine_distance_meters(req.latitude, req.longitude, lat, lon)
            if distance <= 100:
                geo_score = 1.0  # Within 100m
            elif distance <= 350:
                geo_score = 0.7  # Within 350m
            elif distance <= 800:
                geo_score = 0.4
            else:
                geo_score = 0.0
        
        # Weighted confidence score
        confidence = 0.0
        reasons = []
        
        if category_match:
            confidence += 0.25
            reasons.append("Same incident category")
        
        if text_sim > 0.2:
            confidence += min(0.45, text_sim * 0.7)
            reasons.append(f"Significant keyword overlap ({int(text_sim*100)}% lexical similarity)")
            
        if distance is not None:
            if distance <= 350:
                confidence += (geo_score * 0.35)
                reasons.append(f"Immediate geographic proximity ({int(distance)}m away)")
            elif distance > 2000:
                confidence -= 0.2  # Far away decreases duplicate likelihood
        
        confidence = min(max(confidence, 0.0), 0.98)
        
        # If threshold met (>= 0.40), register as potential match
        if confidence >= 0.40:
            matches.append(DuplicateMatch(
                incident_id=inc_id,
                title=title,
                confidence_score=round(confidence, 2),
                reason="; ".join(reasons) if reasons else "Partial overlap in reporting context",
                distance_meters=round(distance, 1) if distance is not None else None
            ))

    matches.sort(key=lambda m: m.confidence_score, reverse=True)
    is_duplicate = len(matches) > 0
    explanation = (
        f"Found {len(matches)} potential matching reports based on category, text overlap, and coordinates."
        if is_duplicate else "No significant duplicate clusters identified within target proximity."
    )

    return DuplicateCheckResponse(
        is_potential_duplicate=is_duplicate,
        matches=matches,
        explanation=explanation
    )
