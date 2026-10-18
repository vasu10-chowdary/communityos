/**
 * CommunityOS Unified Demo Persistence & Heuristic Simulation Store
 *
 * Standalone client-side reactive store for competition demonstration.
 * Backed by browser localStorage with graceful SSR fallbacks.
 * Zero external backend or authentication runtime dependencies.
 */

import { Incident, Resource, AIAnalysis, IncidentStatus, IncidentCategory } from '@/types/incident';
import { SEED_INCIDENTS, SEED_RESOURCES } from '@/lib/seedData';

const INCIDENTS_STORAGE_KEY = 'communityos_demo_incidents_v2';
const RESOURCES_STORAGE_KEY = 'communityos_demo_resources_v2';
const STORE_EVENT = 'communityos_store_updated';

// In-memory cache for SSR & fast access
let memoryIncidents: Incident[] = [...SEED_INCIDENTS];
let memoryResources: Resource[] = [...SEED_RESOURCES];
let isHydrated = false;

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function notifySubscribers() {
  if (isBrowser()) {
    window.dispatchEvent(new CustomEvent(STORE_EVENT));
  }
}

/**
 * Initializes and syncs store from localStorage
 */
export function initStore(): void {
  if (!isBrowser() || isHydrated) return;

  try {
    const storedInc = localStorage.getItem(INCIDENTS_STORAGE_KEY);
    if (storedInc) {
      const parsed = JSON.parse(storedInc);
      if (Array.isArray(parsed) && parsed.length > 0) {
        memoryIncidents = parsed;
      } else {
        localStorage.setItem(INCIDENTS_STORAGE_KEY, JSON.stringify(SEED_INCIDENTS));
        memoryIncidents = [...SEED_INCIDENTS];
      }
    } else {
      localStorage.setItem(INCIDENTS_STORAGE_KEY, JSON.stringify(SEED_INCIDENTS));
      memoryIncidents = [...SEED_INCIDENTS];
    }

    const storedRes = localStorage.getItem(RESOURCES_STORAGE_KEY);
    if (storedRes) {
      const parsed = JSON.parse(storedRes);
      if (Array.isArray(parsed) && parsed.length > 0) {
        memoryResources = parsed;
      } else {
        localStorage.setItem(RESOURCES_STORAGE_KEY, JSON.stringify(SEED_RESOURCES));
        memoryResources = [...SEED_RESOURCES];
      }
    } else {
      localStorage.setItem(RESOURCES_STORAGE_KEY, JSON.stringify(SEED_RESOURCES));
      memoryResources = [...SEED_RESOURCES];
    }

    isHydrated = true;
  } catch (err) {
    console.warn('[DemoStore] LocalStorage access unavailable, using in-memory demo state:', err);
    memoryIncidents = [...SEED_INCIDENTS];
    memoryResources = [...SEED_RESOURCES];
    isHydrated = true;
  }
}

function persistStore(): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(INCIDENTS_STORAGE_KEY, JSON.stringify(memoryIncidents));
    localStorage.setItem(RESOURCES_STORAGE_KEY, JSON.stringify(memoryResources));
  } catch (err) {
    console.warn('[DemoStore] Failed to persist demo state to localStorage:', err);
  }
  notifySubscribers();
}

/**
 * Subscribe to store mutations
 */
export function subscribeToStore(callback: () => void): () => void {
  if (!isBrowser()) return () => {};
  window.addEventListener(STORE_EVENT, callback);
  return () => window.removeEventListener(STORE_EVENT, callback);
}

// ----------------- INCIDENT ACTIONS -----------------

export function getIncidents(): Incident[] {
  initStore();
  return [...memoryIncidents];
}

export function getIncidentById(id: string): Incident | null {
  initStore();
  const found = memoryIncidents.find(i => i.id === id);
  return found ? { ...found } : null;
}

export function createIncident(data: Partial<Incident>): Incident {
  initStore();
  const nowIso = new Date().toISOString();
  const newId = `inc-demo-${Date.now()}`;

  // Heuristic urgency calibration
  const urgency = data.category?.includes('Flooding') ? 82 :
                  data.category?.includes('Fallen') ? 88 :
                  data.category?.includes('Electrical') ? 95 :
                  data.category?.includes('Water') ? 65 : 55;

  const severity = urgency >= 85 ? 'Critical' : urgency >= 70 ? 'High' : urgency >= 40 ? 'Medium' : 'Low';
  const severity_level = urgency >= 85 ? 5 : urgency >= 70 ? 4 : urgency >= 40 ? 3 : 2;

  const newIncident: Incident = {
    id: newId,
    title: (data.title || 'Reported Incident').trim(),
    description: (data.description || '').trim(),
    category: (data.category || 'Other community assistance requests') as IncidentCategory,
    location: (data.location || 'Local Community Sector').trim(),
    latitude: typeof data.latitude === 'number' ? data.latitude : 37.7749,
    longitude: typeof data.longitude === 'number' ? data.longitude : -122.4194,
    status: (data.status || 'Reported') as IncidentStatus,
    severity,
    severity_level,
    image_url: data.image_url || undefined,
    image_base64: data.image_base64 || undefined,
    created_at: nowIso,
    updated_at: nowIso,
    reporter_id: data.reporter_id || 'evaluator-demo-reporter',
    reporter_name: data.reporter_name || 'Alex Morgan (Resident)',
    is_demo: true,
    latest_analysis: data.latest_analysis || {
      category: (data.category || 'General Hazard') as IncidentCategory,
      severity,
      severity_level,
      urgency_score: urgency,
      explanation: `Preliminary automated risk intake for "${data.title}": Visual and contextual markers indicate active community hazard at ${data.location || 'reported sector'}.`,
      visual_evidence_detected: data.image_base64 ? ['Image attachment verified', 'Hazard site documentation'] : ['Textual report confirmed'],
      potential_risks: ['Pedestrian and vehicle disruption', 'Potential secondary infrastructure damage'],
      recommended_next_actions: ['Triage with emergency operations coordinator', 'Evaluate equipment deployment suitability'],
      suggested_resources: ['Municipal Safety & Debris Response Crew'],
      uncertainties: ['Rate of condition escalation over next 2 hours'],
      human_review_required: true,
      model_identifier: 'gemini-3.5-flash (Demo Mode)',
      provider: 'Google Gen AI Simulation',
      timestamp: nowIso
    }
  };

  memoryIncidents = [newIncident, ...memoryIncidents];
  persistStore();
  return newIncident;
}

export function updateIncident(id: string, updates: Partial<Incident>): Incident | null {
  initStore();
  const idx = memoryIncidents.findIndex(i => i.id === id);
  if (idx === -1) return null;

  const updated: Incident = {
    ...memoryIncidents[idx],
    ...updates,
    updated_at: new Date().toISOString()
  };

  memoryIncidents[idx] = updated;
  persistStore();
  return updated;
}

export function updateIncidentStatus(
  incidentId: string,
  status: IncidentStatus,
  notes?: string
): { updatedIncident: Incident | null; releasedResourceId: string | null } {
  initStore();
  const idx = memoryIncidents.findIndex(i => i.id === incidentId);
  if (idx === -1) return { updatedIncident: null, releasedResourceId: null };

  const current = memoryIncidents[idx];
  let releasedResourceId: string | null = null;
  const nowIso = new Date().toISOString();

  // If incident is marked Resolved, atomically release assigned resource back to Available
  if (status === 'Resolved' && current.assigned_resource_id) {
    const resId = current.assigned_resource_id;
    const resIdx = memoryResources.findIndex(r => r.id === resId);
    if (resIdx !== -1) {
      memoryResources[resIdx] = {
        ...memoryResources[resIdx],
        availability: 'Available',
        assigned_incident: undefined,
        updated_at: nowIso
      };
      releasedResourceId = resId;
    }
  }

  const updated: Incident = {
    ...current,
    status,
    resolution_notes: status === 'Resolved' ? (notes || current.resolution_notes || 'Incident resolved and area secured.') : current.resolution_notes,
    responder_notes: status === 'In Progress' ? (notes || current.responder_notes) : current.responder_notes,
    updated_at: nowIso
  };

  memoryIncidents[idx] = updated;
  persistStore();
  return { updatedIncident: updated, releasedResourceId };
}

export function assignResource(
  incidentId: string,
  resourceId: string,
  notes?: string
): { success: boolean; error?: string; incident?: Incident; resource?: Resource } {
  initStore();
  const incIdx = memoryIncidents.findIndex(i => i.id === incidentId);
  if (incIdx === -1) return { success: false, error: 'Incident not found' };

  const resIdx = memoryResources.findIndex(r => r.id === resourceId);
  if (resIdx === -1) return { success: false, error: 'Resource not found' };

  const res = memoryResources[resIdx];
  // Concurrency check
  if (res.availability === 'Busy' || (res.assigned_incident && res.assigned_incident !== incidentId)) {
    return {
      success: false,
      error: `Resource Conflict: "${res.name}" is already assigned to incident #${res.assigned_incident}.`
    };
  }

  const nowIso = new Date().toISOString();

  const updatedRes: Resource = {
    ...res,
    availability: 'Busy',
    assigned_incident: incidentId,
    notes: notes || `Dispatched to incident #${incidentId}`,
    updated_at: nowIso
  };
  memoryResources[resIdx] = updatedRes;

  const updatedInc: Incident = {
    ...memoryIncidents[incIdx],
    status: 'Resource Dispatched',
    assigned_resource_id: resourceId,
    assigned_resource_name: res.name,
    updated_at: nowIso
  };
  memoryIncidents[incIdx] = updatedInc;

  persistStore();
  return { success: true, incident: updatedInc, resource: updatedRes };
}

export function mergeIncidents(primaryId: string, duplicateId: string, reason?: string): boolean {
  initStore();
  const dupIdx = memoryIncidents.findIndex(i => i.id === duplicateId);
  if (dupIdx === -1) return false;

  memoryIncidents[dupIdx] = {
    ...memoryIncidents[dupIdx],
    status: 'In Review',
    duplicate_of: primaryId,
    resolution_notes: `Merged into primary incident #${primaryId}. Reason: ${reason || 'Confirmed duplicate report.'}`,
    updated_at: new Date().toISOString()
  };

  persistStore();
  return true;
}

// ----------------- RESOURCE ACTIONS -----------------

export function getResources(): Resource[] {
  initStore();
  return [...memoryResources];
}

export function createResource(data: Partial<Resource>): Resource {
  initStore();
  const nowIso = new Date().toISOString();
  const newRes: Resource = {
    id: `res-demo-${Date.now()}`,
    name: (data.name || 'Emergency Unit').trim(),
    type: data.type || 'Municipal Emergency Logistics',
    service_area: data.service_area || 'Central District',
    availability: 'Available',
    capacity: data.capacity || 'Standard Operational Response Pack',
    latitude: typeof data.latitude === 'number' ? data.latitude : 37.7749,
    longitude: typeof data.longitude === 'number' ? data.longitude : -122.4194,
    updated_at: nowIso,
    is_demo: true
  };

  memoryResources = [newRes, ...memoryResources];
  persistStore();
  return newRes;
}

// ----------------- DEMO RESET -----------------

export function resetDemoStore(): void {
  if (isBrowser()) {
    try {
      localStorage.removeItem(INCIDENTS_STORAGE_KEY);
      localStorage.removeItem(RESOURCES_STORAGE_KEY);
    } catch (err) {
      console.warn('[DemoStore] Error clearing localStorage:', err);
    }
  }
  memoryIncidents = [...SEED_INCIDENTS];
  memoryResources = [...SEED_RESOURCES];
  isHydrated = true;
  persistStore();
}

// ----------------- HEURISTIC ENGINES -----------------

export interface DuplicateMatchResult {
  incident_id: string;
  title: string;
  confidence_score: number;
  reason: string;
  distance_meters?: number;
}

function calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3; // Earth radius in meters
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

/**
 * Fast client-side duplicate detection
 */
export function checkDuplicates(
  target: { id?: string; title: string; description: string; category: string; latitude?: number; longitude?: number }
): { is_potential_duplicate: boolean; matches: DuplicateMatchResult[]; explanation: string } {
  initStore();
  const matches: DuplicateMatchResult[] = [];
  const targetWords = new Set(`${target.title} ${target.description}`.toLowerCase().split(/\W+/).filter(w => w.length > 3));

  for (const existing of memoryIncidents) {
    if (target.id && existing.id === target.id) continue;

    let score = 0;
    const reasons: string[] = [];

    // Category match
    if (existing.category === target.category) {
      score += 0.35;
      reasons.push('Identical hazard category');
    }

    // Keyword overlap
    const existingWords = `${existing.title} ${existing.description}`.toLowerCase().split(/\W+/).filter(w => w.length > 3);
    let commonCount = 0;
    for (const w of existingWords) {
      if (targetWords.has(w)) commonCount++;
    }
    const overlapRatio = commonCount / Math.max(targetWords.size, 1);
    if (overlapRatio > 0.25) {
      score += Math.min(overlapRatio * 0.45, 0.45);
      reasons.push(`High lexical overlap (${commonCount} shared keywords)`);
    }

    // Geospatial proximity
    let distMeters: number | undefined;
    if (typeof target.latitude === 'number' && typeof target.longitude === 'number' &&
        typeof existing.latitude === 'number' && typeof existing.longitude === 'number') {
      distMeters = calculateDistanceMeters(target.latitude, target.longitude, existing.latitude, existing.longitude);
      if (distMeters < 350) {
        score += 0.35;
        reasons.push(`Within 350m proximity (${distMeters}m away)`);
      } else if (distMeters < 1000) {
        score += 0.15;
        reasons.push(`Within 1km neighborhood (${distMeters}m away)`);
      }
    }

    const confidence_score = Math.min(Math.round(score * 100) / 100, 0.98);
    if (confidence_score >= 0.50) {
      matches.push({
        incident_id: existing.id,
        title: existing.title,
        confidence_score,
        reason: reasons.join('; '),
        distance_meters: distMeters
      });
    }
  }

  matches.sort((a, b) => b.confidence_score - a.confidence_score);

  return {
    is_potential_duplicate: matches.length > 0,
    matches,
    explanation: matches.length > 0
      ? `Found ${matches.length} potential matching reports based on category, text overlap, and coordinates.`
      : 'No near-duplicate reports identified in active queue.'
  };
}

export interface ResourceRecommendationResult {
  resource_id: string;
  name: string;
  type: string;
  suitability_score: number;
  match_rationale: string;
  distance_km?: number;
  availability: string;
}

/**
 * Client-side Resource Matcher
 */
export function recommendResources(incident: Incident): ResourceRecommendationResult[] {
  initStore();
  const category = incident.category.toLowerCase();
  const recommendations: ResourceRecommendationResult[] = [];

  for (const res of memoryResources) {
    const resText = `${res.name} ${res.type} ${res.capacity || ''}`.toLowerCase();
    let score = 0.50;
    const reasons: string[] = [];

    if (category.includes('flood') || category.includes('drain')) {
      if (resText.includes('pump') || resText.includes('vacuum') || resText.includes('drain')) {
        score += 0.45;
        reasons.push('High-capacity dewatering and sump mitigation capability');
      } else if (resText.includes('sandbag') || resText.includes('volunteer')) {
        score += 0.25;
        reasons.push('Perimeter sandbagging and flood diversion');
      }
    } else if (category.includes('tree') || category.includes('road')) {
      if (resText.includes('arborist') || resText.includes('tree') || resText.includes('chipper') || resText.includes('debris')) {
        score += 0.45;
        reasons.push('Heavy arborist cutting and arterial clearing crew');
      }
    } else if (category.includes('water')) {
      if (resText.includes('tanker') || resText.includes('potable') || resText.includes('drinking')) {
        score += 0.48;
        reasons.push('Potable drinking water logistics and neighborhood supply');
      }
    } else if (category.includes('electric') || category.includes('infrastructure')) {
      if (resText.includes('hazard') || resText.includes('barrier') || resText.includes('first aid')) {
        score += 0.35;
        reasons.push('Safety perimeter isolation and first response');
      }
    }

    if (res.availability === 'Available') {
      score += 0.05;
      reasons.push('Unit currently on standby and ready for immediate deployment');
    } else {
      score -= 0.15;
      reasons.push(`Unit currently Busy on incident #${res.assigned_incident}`);
    }

    let distKm: number | undefined;
    if (typeof incident.latitude === 'number' && typeof incident.longitude === 'number' &&
        typeof res.latitude === 'number' && typeof res.longitude === 'number') {
      const distM = calculateDistanceMeters(incident.latitude, incident.longitude, res.latitude, res.longitude);
      distKm = Math.round((distM / 1000) * 10) / 10;
      if (distKm < 3) {
        score += 0.05;
        reasons.push(`Estimated transit distance ${distKm} km`);
      }
    }

    const suitability_score = Math.min(Math.max(Math.round(score * 100) / 100, 0.40), 0.99);

    recommendations.push({
      resource_id: res.id,
      name: res.name,
      type: res.type,
      suitability_score,
      match_rationale: reasons.join(' â€¢ '),
      distance_km: distKm,
      availability: res.availability
    });
  }

  recommendations.sort((a, b) => b.suitability_score - a.suitability_score);
  return recommendations;
}

/**
 * Calibrated Gemini AI Multimodal Analysis Simulation
 */
export async function simulateGeminiAnalysis(incident: Partial<Incident>): Promise<AIAnalysis> {
  // Simulate 1.2s model processing latency
  await new Promise(resolve => setTimeout(resolve, 1200));

  const title = (incident.title || '').toLowerCase();
  const desc = (incident.description || '').toLowerCase();
  const combined = `${title} ${desc}`;
  const nowIso = new Date().toISOString();

  let category: IncidentCategory = 'Other community assistance requests';
  let severity: 'Low' | 'Medium' | 'High' | 'Critical' = 'Medium';
  let severity_level = 3;
  let urgency = 65;
  let risks: string[] = ['Public accessibility disruption'];
  let actions: string[] = ['Dispatch community assessment squad', 'Post safety warning notices'];
  let suggestedRes: string[] = ['Community CERT Volunteer Brigade'];
  let explanation = '';
  const visualEvidence: string[] = [];

  if (incident.image_base64 || incident.image_url) {
    visualEvidence.push('High-contrast photographic terrain captured');
    visualEvidence.push('Physical obstruction and surface condition validated');
  } else {
    visualEvidence.push('Textual citizen field report without visual attachment');
  }

  if (combined.includes('flood') || combined.includes('water') || combined.includes('culvert') || combined.includes('submerged')) {
    category = 'Flooding and waterlogging';
    severity = combined.includes('residential') || combined.includes('basement') || combined.includes('deep') ? 'High' : 'Medium';
    severity_level = severity === 'High' ? 4 : 3;
    urgency = severity === 'High' ? 84 : 70;
    visualEvidence.push('Water pooling over road surface', 'Storm intake blockage');
    risks = [
      'Basement inundation in adjacent residential structures',
      'Structural erosion of road embankment',
      'Potential electrical sub-station water seepage'
    ];
    actions = [
      'Deploy high-flow submersible trash pump trailer',
      'Clear debris grate at primary culvert intake',
      'Establish traffic detour cones around standing water'
    ];
    suggestedRes = ['High-Flow Submersible Trash Pump Trailer #1', 'Sanitation Catch Basin & Drain Intake Crew'];
    explanation = `Automated vision and contextual intake detects significant stormwater accumulation (~1.5 feet) obstructing catch basin. Proximity to residential foundations creates elevated risk of water intrusion requiring rapid dewatering.`;
  } else if (combined.includes('tree') || combined.includes('limb') || combined.includes('road') || combined.includes('branch')) {
    category = 'Fallen trees and blocked roads';
    severity = combined.includes('wire') || combined.includes('power') || combined.includes('arterial') ? 'Critical' : 'High';
    severity_level = severity === 'Critical' ? 5 : 4;
    urgency = severity === 'Critical' ? 92 : 78;
    visualEvidence.push('Trunk blocking transit lanes', 'Sagging or compromised overhead wires');
    risks = [
      'Complete road transit obstruction delaying emergency ambulances',
      'Potential energized wire contact hazard',
      'Secondary traffic collisions in low-visibility conditions'
    ];
    actions = [
      'Cordon off area 50 feet around tree trunk',
      'Coordinate with municipal power utility for electrical line de-energization',
      'Dispatch heavy arborist chainsaw crew with wood chipper'
    ];
    suggestedRes = ['Rapid Municipal Debris & Tree Clearing Squad', 'Emergency Traffic Barricade Kit'];
    explanation = `Hazard triage confirms severe physical impediment across public roadway with possible utility entanglement. High urgency prioritization assigned due to potential arterial route blockage and electrical hazard.`;
  } else if (combined.includes('electric') || combined.includes('wire') || combined.includes('spark') || combined.includes('power')) {
    category = 'Electrical hazards';
    severity = 'Critical';
    severity_level = 5;
    urgency = 96;
    visualEvidence.push('Downed power conductor', 'Exposed utility cabinet');
    risks = ['Immediate electrocution threat', 'Potential fire ignition in dry debris'];
    actions = ['Evacuate perimeter 100ft', 'Urgent alert to electrical grid command', 'Deploy fire patrol escort'];
    suggestedRes = ['Emergency Paramedic Quick Response Unit', 'CERT Volunteer Brigade'];
    explanation = `Critical electrical safety hazard identified. Immediate automated recommendation to isolate perimeter and contact utility emergency dispatch before physical clearing.`;
  } else {
    explanation = `Multimodal evaluation of community report identifies localized hazard. Priority score calibrated based on reported traffic impact and community vulnerability.`;
  }

  const analysis: AIAnalysis = {
    category,
    severity,
    severity_level,
    urgency_score: urgency,
    explanation,
    visual_evidence_detected: visualEvidence,
    potential_risks: risks,
    uncertainties: ['Weather pattern changes over the next 4 hours'],
    recommended_next_actions: actions,
    suggested_resources: suggestedRes,
    human_review_required: true,
    model_identifier: 'gemini-3.5-flash (Demo Mode)',
    provider: 'Google Gen AI Simulation',
    timestamp: nowIso
  };

  // If incident has an ID in store, save analysis to it
  if (incident.id) {
    updateIncident(incident.id, {
      category,
      severity,
      severity_level,
      latest_analysis: analysis
    });
  }

  return analysis;
}
