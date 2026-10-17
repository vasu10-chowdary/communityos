'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Sparkles, 
  AlertTriangle, 
  ShieldCheck, 
  Truck, 
  CheckCircle2, 
  MapPin, 
  Clock, 
  RefreshCw,
  Copy,
  GitMerge,
  Eye,
  Camera,
  UserCheck,
  Send
} from 'lucide-react';
import { Incident, Resource, AIAnalysis, IncidentStatus } from '@/types/incident';
import { SEED_INCIDENTS, SEED_RESOURCES } from '@/lib/seedData';
import { db, isProductionEnvironment } from '@/lib/firebase';
import { doc, getDoc, updateDoc, collection, getDocs, query, limit } from 'firebase/firestore';
import { useUserRole } from '@/lib/roleContext';
import { apiFetch } from '@/lib/api';

interface DuplicateCandidate {
  incident_id: string;
  title: string;
  confidence_score: number;
  reason: string;
  distance_meters?: number;
}

interface ResourceMatch {
  resource_id: string;
  name: string;
  type: string;
  suitability_score: number;
  match_rationale: string;
  distance_km?: number;
  availability: string;
}

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const incidentId = params?.id as string;
  const { role, userId, userName } = useUserRole();

  const [incident, setIncident] = useState<Incident | null>(null);
  const [resources, setResources] = useState<Resource[]>(SEED_RESOURCES);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Duplicate detection state
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateCandidate[]>([]);
  const [checkingDuplicates, setCheckingDuplicates] = useState(false);
  const [duplicateError, setDuplicateError] = useState<string | null>(null);
  const [duplicateScanned, setDuplicateScanned] = useState(false);
  const [scannedCount, setScannedCount] = useState<number>(0);
  const [mergeStatus, setMergeStatus] = useState<string | null>(null);

  // Resource Recommendation state
  const [recommendedResources, setRecommendedResources] = useState<ResourceMatch[]>([]);
  const [recommending, setRecommending] = useState(false);
  const [responderNote, setResponderNote] = useState('');

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  useEffect(() => {
    const found = SEED_INCIDENTS.find(i => i.id === incidentId);
    if (found) {
      setIncident(found);
    }

    const fetchDoc = async () => {
      try {
        const docRef = doc(db, 'incidents', incidentId);
        const docSnap = await getDoc(docRef);
        if (docSnap.exists()) {
          setIncident({ id: docSnap.id, ...docSnap.data() } as Incident);
        }

        // Also fetch live resources for dispatch if available in Firestore
        const resSnap = await getDocs(collection(db, 'resources'));
        if (!resSnap.empty) {
          const liveList: Resource[] = [];
          resSnap.forEach((r) => {
            liveList.push({ id: r.id, ...r.data() } as Resource);
          });
          if (liveList.length > 0) {
            setResources(liveList);
          }
        }
      } catch (e) {
        console.info("Using incident state:", e);
      }
    };
    if (incidentId) fetchDoc();
  }, [incidentId]);

  // Check for duplicates using live Firestore incidents
  const handleCheckDuplicates = async () => {
    if (!incident) return;
    setCheckingDuplicates(true);
    setDuplicateError(null);
    setActionSuccess(null);
    setDuplicateMatches([]);

    try {
      let existingIncidents: Array<{
        id: string;
        title: string;
        description: string;
        category: string;
        latitude?: number;
        longitude?: number;
      }> = [];

      try {
        const incidentsQuery = query(collection(db, 'incidents'), limit(50));
        const snap = await getDocs(incidentsQuery);
        snap.forEach((docSnap) => {
          if (docSnap.id !== incident.id) {
            const d = docSnap.data();
            existingIncidents.push({
              id: docSnap.id,
              title: d.title || '',
              description: d.description || '',
              category: d.category || '',
              latitude: typeof d.latitude === 'number' ? d.latitude : undefined,
              longitude: typeof d.longitude === 'number' ? d.longitude : undefined,
            });
          }
        });
      } catch (firestoreErr: any) {
        console.info("Firestore live incident query for duplicate check:", firestoreErr);
        if (isProductionEnvironment()) {
          throw new Error(`Failed to query live incidents from Firestore: ${firestoreErr.message}`);
        }
      }

      // Development fallback if Firestore returned no other incidents and not in production
      if (existingIncidents.length === 0 && !isProductionEnvironment()) {
        existingIncidents = SEED_INCIDENTS.filter(i => i.id !== incident.id).map(i => ({
          id: i.id,
          title: i.title,
          description: i.description,
          category: i.category,
          latitude: i.latitude,
          longitude: i.longitude,
        }));
      }

      setScannedCount(existingIncidents.length);

      if (existingIncidents.length === 0) {
        setDuplicateMatches([]);
        setDuplicateScanned(true);
        setActionSuccess('No other reports currently in queue to compare against.');
        return;
      }

      const data = await apiFetch('/api/incidents/check-duplicates', {
        method: 'POST',
        body: JSON.stringify({
          title: incident.title,
          description: incident.description,
          category: incident.category,
          latitude: incident.latitude,
          longitude: incident.longitude,
          existing_incidents: existingIncidents
        })
      });

      setDuplicateMatches(data.matches || []);
      setDuplicateScanned(true);
      if (!data.matches || data.matches.length === 0) {
        setActionSuccess(`Scanned ${existingIncidents.length} report(s). No near-duplicate clusters identified.`);
      }
    } catch (e: any) {
      console.warn("Duplicate check error:", e);
      setDuplicateError(e.message || 'Error checking for duplicates.');
    } finally {
      setCheckingDuplicates(false);
    }
  };

  // Merge duplicate
  const handleConfirmMerge = async (primaryId: string) => {
    if (role !== 'coordinator') {
      alert('RBAC Warning: Only Coordinators can merge duplicate incidents.');
      return;
    }
    try {
      await apiFetch('/api/incidents/merge', {
        method: 'POST',
        body: JSON.stringify({
          primary_incident_id: primaryId,
          duplicate_incident_id: incident?.id,
          merge_reason: 'Confirmed report duplicate by incident coordinator.'
        })
      });
      setMergeStatus(`Linked as duplicate of #${primaryId}. Preserved in history.`);
      setActionSuccess(`Report #${incident?.id} safely linked to primary #${primaryId}.`);
    } catch (e: any) {
      console.warn("Merge error:", e);
      alert(`Merge failed: ${e.message}`);
    }
  };

  // Multimodal Gemini AI Analysis
  const handleTriggerGeminiAnalysis = async () => {
    if (!incident) return;
    setAnalyzing(true);
    setAnalysisError(null);
    setActionSuccess(null);

    try {
      // Only send base64 if it is a valid data URI or base64 binary string (never arbitrary external http/https URLs)
      let validImageBase64: string | undefined = undefined;
      const rawImage = incident.image_base64 || incident.image_url;
      if (rawImage) {
        if (rawImage.startsWith('data:image/')) {
          validImageBase64 = rawImage;
        } else if (!rawImage.startsWith('http://') && !rawImage.startsWith('https://')) {
          validImageBase64 = rawImage;
        }
      }

      const analysisData = await apiFetch<AIAnalysis>('/api/incidents/analyze', {
        method: 'POST',
        body: JSON.stringify({
          title: incident.title,
          description: incident.description,
          category: incident.category,
          location: incident.location,
          latitude: incident.latitude,
          longitude: incident.longitude,
          image_base64: validImageBase64,
          user_language: 'en'
        })
      });
      
      const updatedIncident: Incident = {
        ...incident,
        severity_level: analysisData.severity_level,
        severity: analysisData.severity,
        latest_analysis: analysisData,
        updated_at: new Date().toISOString()
      };

      setIncident(updatedIncident);
      setActionSuccess('Multimodal Gemini AI evaluation completed successfully!');

      // Automatically fetch resource recommendations based on new analysis
      handleRecommendResources(analysisData.severity_level, analysisData.urgency_score);

      try {
        await updateDoc(doc(db, 'incidents', incident.id), {
          severity_level: analysisData.severity_level,
          severity: analysisData.severity,
          latest_analysis: analysisData,
          updated_at: updatedIncident.updated_at
        });
      } catch (err) {
        console.info("Firestore update skipped:", err);
      }
    } catch (err: any) {
      setAnalysisError(err.message || 'Error communicating with FastAPI incident analysis endpoint.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Recommend matching resources
  const handleRecommendResources = async (sevLvl = 3, urgency = 75) => {
    if (!incident) return;
    setRecommending(true);
    try {
      const data = await apiFetch('/api/incidents/recommend-resources', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incident.id,
          category: incident.category,
          severity_level: sevLvl,
          urgency_score: urgency,
          latitude: incident.latitude,
          longitude: incident.longitude,
          available_resources: resources
        })
      });
      setRecommendedResources(data.recommendations || []);
    } catch (e: any) {
      console.warn("Resource matching error:", e);
    } finally {
      setRecommending(false);
    }
  };

  // Safe Assignment (Coordinator only)
  const handleAssignResource = async (resourceId: string, resourceName: string) => {
    if (role !== 'coordinator') {
      alert('Role Permission Error: Only Coordinators can approve and dispatch emergency units.');
      return;
    }

    try {
      await apiFetch('/api/incidents/assign-resource', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incident?.id,
          resource_id: resourceId,
          notes: `Dispatched by Coordinator ${userName}`
        })
      });

      const updated = {
        ...incident!,
        status: 'Resource Dispatched' as IncidentStatus,
        assigned_resource_id: resourceId,
        assigned_resource_name: resourceName,
        updated_at: new Date().toISOString()
      };
      setIncident(updated);
      setResources(prev => prev.map(r => r.id === resourceId ? { ...r, availability: 'Busy', assigned_incident: incident?.id } : r));
      setActionSuccess(`Coordinator approved deployment of ${resourceName}!`);
    } catch (err: any) {
      alert(`Assignment Error: ${err.message}`);
    }
  };

  // Responder Progress Note
  const handleSaveResponderNote = async () => {
    if (role !== 'responder' && role !== 'coordinator') {
      alert('Only Responders and Coordinators can submit field progress updates.');
      return;
    }
    try {
      await apiFetch('/api/incidents/update-status', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incident?.id,
          status: 'In Progress',
          responder_progress_note: responderNote
        })
      });
      const updated = {
        ...incident!,
        status: 'In Progress' as IncidentStatus,
        responder_notes: responderNote,
        updated_at: new Date().toISOString()
      };
      setIncident(updated);
      setActionSuccess('Responder progress note recorded!');
    } catch (err: any) {
      alert(`Update Error: ${err.message}`);
    }
  };

  // Status Lifecycle Update
  const handleUpdateStatus = async (newStatus: IncidentStatus) => {
    if (newStatus === 'Resolved' && role !== 'coordinator') {
      alert('RBAC Violation: Only Coordinators can officially resolve an incident.');
      return;
    }

    try {
      await apiFetch('/api/incidents/update-status', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incident?.id,
          status: newStatus
        })
      });

      const updated = {
        ...incident!,
        status: newStatus,
        updated_at: new Date().toISOString()
      };
      if (newStatus === 'Resolved' && incident?.assigned_resource_id) {
        setResources(prev => prev.map(r => r.id === incident.assigned_resource_id ? { ...r, availability: 'Available', assigned_incident: undefined } : r));
      }
      setIncident(updated);
      setActionSuccess(`Incident status updated to "${newStatus}".`);
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  if (!incident) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-800">Incident Not Found</h2>
        <Link href="/dashboard" className="text-civic-teal font-medium text-sm">Return to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard" className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-navy-900 transition">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Operations Command</span>
        </Link>
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-400">ID: {incident.id}</span>
          <span className="px-2 py-0.5 rounded bg-navy-800 text-white font-mono uppercase">{role} View</span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {analysisError && (
        <div className="p-4 bg-amber-50 border border-amber-300 text-amber-900 rounded-lg text-sm space-y-1">
          <div className="flex items-center space-x-2 font-semibold text-amber-950">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>AI Service Response Notice</span>
          </div>
          <p className="text-xs text-amber-800">{analysisError}</p>
        </div>
      )}

      {/* Main Incident Details */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wide border ${
              incident.severity === 'Critical' || incident.severity_level === 5 ? 'bg-red-50 text-civic-red border-red-200' :
              incident.severity === 'High' || incident.severity_level === 4 ? 'bg-amber-50 text-civic-amber border-amber-200' :
              incident.status === 'Resolved' ? 'bg-emerald-50 text-civic-green border-emerald-200' :
              'bg-slate-100 text-slate-700 border-slate-200'
            }`}>
              {incident.severity ? `${incident.severity} (Lvl ${incident.severity_level || 3}/5)` : 'Awaiting AI Triage'}
            </span>

            <span className="text-xs bg-navy-100 text-navy-800 px-2.5 py-1 rounded-md font-medium">
              {incident.category}
            </span>

            <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md font-medium">
              Status: {incident.status}
            </span>

            {mergeStatus && (
              <span className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded font-medium flex items-center space-x-1">
                <GitMerge className="w-3 h-3" />
                <span>{mergeStatus}</span>
              </span>
            )}
          </div>

          {/* Role-gated lifecycle controls */}
          <div className="flex items-center space-x-2">
            {role === 'coordinator' && (
              <>
                <button
                  onClick={() => handleUpdateStatus('In Review')}
                  className="px-2.5 py-1 text-xs font-medium rounded border border-slate-300 hover:bg-slate-50 text-slate-700"
                >
                  Mark In Review
                </button>
                <button
                  onClick={() => handleUpdateStatus('Resolved')}
                  className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  Approve Resolution
                </button>
              </>
            )}

            {role === 'responder' && (
              <button
                onClick={() => handleUpdateStatus('In Progress')}
                className="px-2.5 py-1 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-700 text-white"
              >
                Mark In Progress
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-3">
            <h1 className="text-2xl font-bold text-slate-900">{incident.title}</h1>
            <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap">{incident.description}</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-slate-500 pt-2 border-t border-slate-100">
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-slate-400" />
                <span><strong>Location:</strong> {incident.location}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-slate-400" />
                <span><strong>Reported:</strong> {new Date(incident.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Multimodal Photo Preview */}
          {incident.image_url && (
            <div className="border border-slate-200 rounded-lg p-2 bg-slate-50">
              <div className="text-xs font-semibold text-slate-600 mb-1.5 flex items-center space-x-1">
                <Camera className="w-3.5 h-3.5 text-civic-teal" />
                <span>Multimodal Evidence Photo</span>
              </div>
              <img
                src={incident.image_url}
                alt="Incident photographic evidence"
                className="w-full h-44 object-cover rounded-md border border-slate-200"
              />
              <p className="text-[10px] text-slate-400 mt-1 italic">
                * Evaluated by Gemini for water height & structural damage. No GPS invented from image alone.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Multimodal Gemini AI Risk Intelligence */}
      <div className="bg-gradient-to-br from-navy-900 to-navy-800 text-white rounded-xl shadow-md p-6 space-y-6 border border-navy-700">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-navy-700 pb-4">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-6 h-6 text-civic-teal" />
            <div>
              <h2 className="text-lg font-bold">Google Gemini Multimodal Risk Engine</h2>
              <p className="text-xs text-slate-300">Server-side visual & textual heuristic risk triaging</p>
            </div>
          </div>

          <button
            onClick={handleTriggerGeminiAnalysis}
            disabled={analyzing}
            className="inline-flex items-center space-x-2 bg-civic-teal hover:bg-teal-600 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
            <span>{analyzing ? 'Consulting Gemini...' : 'Analyze with Gemini'}</span>
          </button>
        </div>

        {incident.latest_analysis ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="bg-navy-800/80 p-3 rounded-lg border border-navy-700">
                <div className="text-xs text-slate-400 font-medium">Severity (1–5)</div>
                <div className="text-xl font-bold text-civic-amber mt-1">Level {incident.latest_analysis.severity_level || 4} / 5</div>
              </div>
              <div className="bg-navy-800/80 p-3 rounded-lg border border-navy-700">
                <div className="text-xs text-slate-400 font-medium">Urgency Heuristic</div>
                <div className="text-xl font-bold text-civic-teal mt-1">{incident.latest_analysis.urgency_score} / 100</div>
              </div>
              <div className="bg-navy-800/80 p-3 rounded-lg border border-navy-700">
                <div className="text-xs text-slate-400 font-medium">Model Identifier</div>
                <div className="text-xs font-mono text-slate-200 mt-1">{incident.latest_analysis.model_identifier}</div>
              </div>
              <div className="bg-navy-800/80 p-3 rounded-lg border border-navy-700">
                <div className="text-xs text-slate-400 font-medium">Human Sign-off</div>
                <div className="text-xs text-amber-300 mt-1 font-semibold">Required by Coordinator</div>
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Evidence-Based Explanation</h3>
              <p className="text-xs sm:text-sm text-slate-200 leading-relaxed bg-navy-800/40 p-3 rounded-lg border border-navy-700/50">
                {incident.latest_analysis.explanation}
              </p>
            </div>

            {incident.latest_analysis.visual_evidence_detected && incident.latest_analysis.visual_evidence_detected.length > 0 && (
              <div className="bg-navy-800/50 p-3 rounded-lg border border-navy-700/60">
                <h4 className="text-xs font-semibold text-teal-300 uppercase tracking-wide flex items-center space-x-1.5 mb-1.5">
                  <Eye className="w-3.5 h-3.5" />
                  <span>Visual Evidence Extracted from Photograph</span>
                </h4>
                <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4">
                  {incident.latest_analysis.visual_evidence_detected.map((cue, idx) => (
                    <li key={idx}>{cue}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-navy-800/50 p-4 rounded-lg border border-navy-700/60 space-y-2">
                <h3 className="text-xs font-semibold text-red-300 uppercase tracking-wide flex items-center space-x-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Identified Cascading Risks</span>
                </h3>
                <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4">
                  {incident.latest_analysis.potential_risks.map((risk, idx) => (
                    <li key={idx}>{risk}</li>
                  ))}
                </ul>
              </div>

              <div className="bg-navy-800/50 p-4 rounded-lg border border-navy-700/60 space-y-2">
                <h3 className="text-xs font-semibold text-teal-300 uppercase tracking-wide flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Recommended Tactical Actions</span>
                </h3>
                <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4">
                  {incident.latest_analysis.recommended_next_actions.map((act, idx) => (
                    <li key={idx}>{act}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-slate-400 text-xs">
            No Gemini evaluation generated yet. Click &ldquo;Analyze with Gemini&rdquo; to execute multimodal inference.
          </div>
        )}
      </div>

      {/* Duplicate Incident Detection & Review Panel */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Copy className="w-5 h-5 text-civic-teal" />
            <h2 className="text-base font-bold text-slate-900">Duplicate Incident Detection</h2>
          </div>

          <button
            onClick={handleCheckDuplicates}
            disabled={checkingDuplicates}
            className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-medium transition"
          >
            {checkingDuplicates ? 'Scanning Queue...' : 'Scan for Near Duplicates'}
          </button>
        </div>

        {/* Duplicate Detection UI */}
        {duplicateError && (
          <div className="p-3.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-red-600" />
            <span>Duplicate scan error: {duplicateError}</span>
          </div>
        )}

        {checkingDuplicates && (
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-center space-x-2">
            <RefreshCw className="w-4 h-4 text-civic-teal animate-spin flex-shrink-0" />
            <span>Querying live Firestore incidents and evaluating proximity...</span>
          </div>
        )}

        {!checkingDuplicates && duplicateMatches.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-slate-600">
              The following existing incidents share high text overlap and geographic proximity. Original records are preserved upon linking.
            </p>
            {duplicateMatches.map((dup) => (
              <div key={dup.incident_id} className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900">{dup.title}</span>
                    <span className="text-[10px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-semibold">
                      {Math.round(dup.confidence_score * 100)}% match confidence
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{dup.reason}</p>
                </div>

                {role === 'coordinator' ? (
                  <button
                    onClick={() => handleConfirmMerge(dup.incident_id)}
                    className="inline-flex items-center space-x-1 bg-navy-800 hover:bg-navy-900 text-white text-xs px-3 py-1.5 rounded-md self-start sm:self-center"
                  >
                    <GitMerge className="w-3.5 h-3.5" />
                    <span>Link as Duplicate</span>
                  </button>
                ) : (
                  <span className="text-xs text-slate-400 italic">Coordinator review needed to link</span>
                )}
              </div>
            ))}
          </div>
        )}

        {!checkingDuplicates && !duplicateError && duplicateScanned && duplicateMatches.length === 0 && (
          <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>No near-duplicate reports identified among {scannedCount} active incident(s) in queue.</span>
          </div>
        )}

        {!checkingDuplicates && !duplicateError && !duplicateScanned && (
          <p className="text-xs text-slate-500">
            Click &ldquo;Scan for Near Duplicates&rdquo; to evaluate lexical and geographic proximity against active Firestore reports.
          </p>
        )}
      </div>

      {/* Smart Resource Recommendation & Dispatch Deck */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Truck className="w-5 h-5 text-civic-teal" />
            <h2 className="text-base font-bold text-slate-900">Resource Matching & Dispatch Approval</h2>
          </div>

          <button
            onClick={() => handleRecommendResources(incident.severity_level || 3, incident.latest_analysis?.urgency_score || 70)}
            disabled={recommending}
            className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-medium transition"
          >
            {recommending ? 'Calculating...' : 'Recalculate Matches'}
          </button>
        </div>

        {incident.assigned_resource_name ? (
          <div className="p-4 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-900 flex items-center justify-between">
            <div>
              <strong>Currently Dispatched Resource:</strong> {incident.assigned_resource_name}
            </div>
            <span className="text-xs bg-teal-200/80 px-2.5 py-0.5 rounded font-semibold">Active In Field</span>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-slate-600">
              Ranked recommendation of available pumps, arborist crews, water tankers, and medical squads based on incident hazard type and proximity.
            </p>

            <div className="space-y-2">
              {(recommendedResources.length > 0 ? recommendedResources : resources.map(r => ({
                resource_id: r.id,
                name: r.name,
                type: r.type,
                suitability_score: r.availability === 'Available' ? 0.75 : 0.20,
                match_rationale: r.availability === 'Available' ? 'Available in municipal pool' : 'Currently deployed',
                availability: r.availability
              }))).map((item) => (
                <div key={item.resource_id} className="p-3.5 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 transition">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-slate-900">{item.name}</span>
                      <span className="text-xs text-slate-500">({item.type})</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        item.availability === 'Available' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {item.availability}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      <strong>Match Rationale:</strong> {item.match_rationale}
                    </div>
                  </div>

                  {role === 'coordinator' ? (
                    <button
                      onClick={() => handleAssignResource(item.resource_id, item.name)}
                      disabled={item.availability === 'Busy'}
                      className="px-3.5 py-1.5 bg-civic-teal hover:bg-teal-600 disabled:opacity-40 text-white text-xs font-semibold rounded-lg shadow-sm transition whitespace-nowrap"
                    >
                      Approve & Dispatch
                    </button>
                  ) : (
                    <span className="text-xs text-slate-400 italic">Coordinator approval required</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Responder Progress Section */}
        {(role === 'responder' || role === 'coordinator') && (
          <div className="pt-4 border-t border-slate-100 space-y-3">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Responder Field Progress Log</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={responderNote}
                onChange={(e) => setResponderNote(e.target.value)}
                placeholder="e.g., Pump deployed; water level receded by 8 inches..."
                className="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-civic-teal focus:outline-none"
              />
              <button
                onClick={handleSaveResponderNote}
                className="px-3 py-2 bg-navy-800 hover:bg-navy-900 text-white text-xs font-semibold rounded-lg flex items-center space-x-1"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Log Note</span>
              </button>
            </div>
            {incident.responder_notes && (
              <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200">
                <strong>Latest Field Note:</strong> {incident.responder_notes}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
