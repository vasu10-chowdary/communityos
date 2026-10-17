from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class IncidentAnalysisRequest(BaseModel):
    incident_id: Optional[str] = Field(None, description="Optional incident ID to associate and persist analysis with")
    title: str = Field(..., min_length=3, max_length=150, description="Brief summary of the incident")
    description: str = Field(..., min_length=10, max_length=4000, description="Full description of the issue")
    category: Optional[str] = Field("Other", description="User-reported category")
    location: Optional[str] = Field(None, description="Reported address or neighborhood")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    # Multimodal support
    image_base64: Optional[str] = Field(None, description="Optional base64 encoded incident photo")
    image_mime_type: Optional[str] = Field(None, description="MIME type e.g. image/jpeg, image/png, image/webp")
    user_language: Optional[str] = Field("en", description="Reporting language hint")

class IncidentAnalysisResponse(BaseModel):
    category: str
    severity_level: int = Field(..., ge=1, le=5, description="Calibrated numeric severity from 1 to 5")
    severity: str = Field(..., description="Low, Medium, High, or Critical")
    urgency_score: int = Field(..., ge=1, le=100, description="Prioritization heuristic score from 1-100")
    explanation: str = Field(..., description="Evidence-based reasoning citing visual/textual observations")
    visual_evidence_detected: Optional[List[str]] = Field(default=[], description="Visual cues identified in the photograph")
    potential_risks: List[str]
    uncertainties: List[str]
    recommended_next_actions: List[str]
    suggested_resources: List[str]
    human_review_required: bool
    model_identifier: str
    provider: str = "Google Gen AI"
    timestamp: str

class DuplicateCheckRequest(BaseModel):
    title: str
    description: str
    category: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    existing_incidents: List[Dict[str, Any]] = []

class DuplicateMatch(BaseModel):
    incident_id: str
    title: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str
    distance_meters: Optional[float] = None

class DuplicateCheckResponse(BaseModel):
    is_potential_duplicate: bool
    matches: List[DuplicateMatch] = []
    explanation: str

class ResourceRecommendationRequest(BaseModel):
    incident_id: str
    category: str
    severity_level: int = Field(..., ge=1, le=5)
    urgency_score: int = Field(..., ge=1, le=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_area: Optional[str] = None
    available_resources: List[Dict[str, Any]] = []

class RecommendedResource(BaseModel):
    resource_id: str
    name: str
    type: str
    suitability_score: float = Field(..., ge=0.0, le=1.0)
    match_rationale: str
    distance_km: Optional[float] = None
    availability: str

class ResourceRecommendationResponse(BaseModel):
    recommendations: List[RecommendedResource] = []

class ResourceAssignmentRequest(BaseModel):
    incident_id: str
    resource_id: str
    notes: Optional[str] = None

class IncidentMergeRequest(BaseModel):
    primary_incident_id: str
    duplicate_incident_id: str
    merge_reason: str

class IncidentStatusUpdateRequest(BaseModel):
    incident_id: Optional[str] = None
    status: str = Field(..., description="Reported, In Review, Resource Dispatched, In Progress, Resolved")
    resolution_notes: Optional[str] = None
    responder_progress_note: Optional[str] = None

class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10, max_length=4000)
    category: str = Field(default="Other community assistance requests")
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    latest_analysis: Optional[Dict[str, Any]] = None
    is_demo: Optional[bool] = False

class ResourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    type: str = Field(..., min_length=3, max_length=120)
    category: Optional[str] = "general"
    capacity: Optional[str] = None
    service_area: Optional[str] = None
    location: Optional[str] = None
    contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
