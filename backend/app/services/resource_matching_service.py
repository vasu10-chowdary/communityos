from typing import List, Dict, Any
from app.schemas.incident import (
    ResourceRecommendationRequest, 
    ResourceRecommendationResponse, 
    RecommendedResource
)
from app.services.duplicate_service import haversine_distance_meters

# Category to matching capability mapping
CAPABILITY_MAP = {
    "Flooding and waterlogging": ["Flooding & Sump Pump Mitigation", "Pump", "Sandbagging"],
    "Blocked drainage": ["Flooding & Sump Pump Mitigation", "Sanitation", "Suction", "Vacuum"],
    "Water shortages": ["Emergency Potable Water Logistics", "Water Tanker", "Water"],
    "Fallen trees and blocked roads": ["Heavy Tree & Debris Removal", "Arborist", "Chainsaw"],
    "Damaged infrastructure": ["Infrastructure Inspection Crew", "Heavy Machinery", "Structural"],
    "Electrical hazards": ["Electrical Safety Squad", "Utility Grid Support", "Emergency Generator"],
    "Other community assistance requests": ["First Response & Sandbagging", "Volunteer", "Medical"]
}

def match_resources(req: ResourceRecommendationRequest) -> ResourceRecommendationResponse:
    results: List[RecommendedResource] = []
    needed_types = CAPABILITY_MAP.get(req.category, ["First Response & Sandbagging"])

    for res in req.available_resources:
        res_id = res.get("id", "")
        name = res.get("name", "")
        res_type = res.get("type", "")
        availability = res.get("availability", "Available")
        service_area = res.get("service_area", "")
        lat = res.get("latitude")
        lon = res.get("longitude")

        # Base score
        score = 0.0
        reasons = []

        # 1. Type match
        is_type_match = any(need.lower() in res_type.lower() or need.lower() in name.lower() for need in needed_types)
        if is_type_match:
            score += 0.50
            reasons.append(f"Specialized equipment matching {req.category}")
        else:
            score += 0.15
            reasons.append("General civic assistance capability")

        # 2. Availability bonus / penalty
        if availability == "Available":
            score += 0.25
            reasons.append("Unit immediately ready for deployment")
        elif availability == "Busy":
            score -= 0.40
            reasons.append("Currently deployed elsewhere")
        else:
            score -= 0.20
            reasons.append("Unit in maintenance")

        # 3. Urgency / severity factor
        if req.severity_level >= 4:
            score += 0.15
            reasons.append("Prioritized for high-severity incident")

        # 4. Proximity / Service Area
        distance_km = None
        if req.latitude is not None and req.longitude is not None and lat is not None and lon is not None:
            dist_m = haversine_distance_meters(req.latitude, req.longitude, lat, lon)
            distance_km = round(dist_m / 1000.0, 2)
            if distance_km <= 5.0:
                score += 0.10
                reasons.append(f"Near incident site ({distance_km}km)")
        elif req.service_area and req.service_area.lower() in service_area.lower():
            score += 0.10
            reasons.append(f"Matches assigned service area ({service_area})")

        score = min(max(score, 0.05), 0.99)

        results.append(RecommendedResource(
            resource_id=res_id,
            name=name,
            type=res_type,
            suitability_score=round(score, 2),
            match_rationale="; ".join(reasons),
            distance_km=distance_km,
            availability=availability
        ))

    # Sort descending by suitability score
    results.sort(key=lambda r: r.suitability_score, reverse=True)
    return ResourceRecommendationResponse(recommendations=results)
