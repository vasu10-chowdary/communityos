export type IncidentCategory =
  | 'Flooding and waterlogging'
  | 'Blocked drainage'
  | 'Water shortages'
  | 'Fallen trees and blocked roads'
  | 'Damaged infrastructure'
  | 'Electrical hazards'
  | 'Other community assistance requests';

export type IncidentSeverity = 'Low' | 'Medium' | 'High' | 'Critical';

export type IncidentStatus =
  | 'Reported'
  | 'In Review'
  | 'Resource Dispatched'
  | 'In Progress'
  | 'Resolved';

export type UserRole = 'citizen' | 'coordinator' | 'responder';

export interface AIAnalysis {
  category: IncidentCategory;
  severity_level?: number; // 1-5 scale
  severity: IncidentSeverity;
  urgency_score: number;
  explanation: string;
  visual_evidence_detected?: string[];
  potential_risks: string[];
  recommended_next_actions: string[];
  suggested_resources: string[];
  uncertainties: string[];
  human_review_required: boolean;
  model_identifier: string;
  provider: string;
  timestamp: string;
}

export interface DuplicateLink {
  primary_id: string;
  duplicate_id: string;
  confidence: number;
  reason: string;
  merged_at: string;
  merged_by: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  category: IncidentCategory;
  severity_level?: number;
  severity?: IncidentSeverity;
  status: IncidentStatus;
  location: string;
  latitude?: number;
  longitude?: number;
  image_url?: string | null; // Multimodal photograph
  image_base64?: string | null;
  created_at: string;
  updated_at?: string;
  reporter_id: string;
  reporter_name?: string;
  is_demo?: boolean;
  assigned_resource_id?: string;
  assigned_resource_name?: string;
  latest_analysis?: AIAnalysis;
  responder_notes?: string;
  resolution_notes?: string;
  duplicate_of?: string; // Linked duplicate ID
  merged_reports?: string[];
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  service_area: string;
  availability: 'Available' | 'Busy' | 'Maintenance';
  capacity: string;
  assigned_incident?: string;
  updated_at: string;
  is_demo?: boolean;
  latitude?: number;
  longitude?: number;
  notes?: string;
}
