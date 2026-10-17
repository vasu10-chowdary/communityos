'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  MapPin, 
  Layers, 
  ExternalLink, 
  Sparkles, 
  Filter,
  AlertCircle,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { Incident } from '@/types/incident';
import { SEED_INCIDENTS } from '@/lib/seedData';
import { db, isFirebaseConfigured, isProductionEnvironment } from '@/lib/firebase';
import { collection, onSnapshot, query, orderBy } from 'firebase/firestore';
import { useUserRole } from '@/lib/roleContext';

export default function IncidentMapPage() {
  const { isDemoData, setIsDemoData } = useUserRole();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const isProd = isProductionEnvironment();
    const hasConfig = isFirebaseConfigured();

    if (isProd && !hasConfig) {
      setErrorMsg("Cloud Firestore is not configured in production. Configure NEXT_PUBLIC_FIREBASE_* variables.");
      setLoading(false);
      return;
    }

    try {
      const q = query(collection(db, "incidents"), orderBy("created_at", "desc"));
      const unsubscribe = onSnapshot(q, (snapshot) => {
        setLoading(false);
        const remoteList: Incident[] = [];
        snapshot.forEach((doc) => {
          remoteList.push({ id: doc.id, ...doc.data() } as Incident);
        });

        if (remoteList.length > 0) {
          setIncidents(remoteList);
          setSelectedIncident(prev => prev ? remoteList.find(i => i.id === prev.id) || remoteList[0] : remoteList[0]);
          setIsDemoData(false);
        } else if (!isProd) {
          setIncidents(SEED_INCIDENTS);
          setSelectedIncident(SEED_INCIDENTS[0]);
          setIsDemoData(true);
        } else {
          setIncidents([]);
          setSelectedIncident(null);
          setIsDemoData(false);
        }
      }, (err) => {
        setLoading(false);
        if (isProd) {
          setErrorMsg(`Firestore Error: ${err.message}`);
        } else {
          console.info("Firestore map listener fallback:", err.message);
          setIncidents(SEED_INCIDENTS);
          setSelectedIncident(SEED_INCIDENTS[0]);
          setIsDemoData(true);
        }
      });
      return () => unsubscribe();
    } catch (e: any) {
      setLoading(false);
      if (isProd) {
        setErrorMsg(`Initialization error: ${e.message}`);
      } else {
        setIncidents(SEED_INCIDENTS);
        setSelectedIncident(SEED_INCIDENTS[0]);
        setIsDemoData(true);
      }
    }
  }, [setIsDemoData]);

  const filteredIncidents = incidents.filter(i => {
    if (filterSeverity === 'ALL') return true;
    return i.severity === filterSeverity;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight flex items-center space-x-2">
            <MapPin className="w-8 h-8 text-civic-teal" />
            <span>Interactive Incident Map</span>
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Geographic dispatch visualizer highlighting hazards, response locations, and urgency heuristics.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-civic-teal"
          >
            <option value="ALL">All Severities</option>
            <option value="Critical">Critical Only</option>
            <option value="High">High Only</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-100 border border-red-300 rounded-xl text-red-900 text-sm flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center space-y-2">
          <Loader2 className="w-8 h-8 animate-spin text-civic-teal" />
          <span className="text-sm">Synchronizing incident nodes with Cloud Firestore...</span>
        </div>
      ) : (
        /* Main Map View & Inspection Split */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map Canvas / GIS Representation */}
          <div className="lg:col-span-2 bg-slate-900 rounded-xl overflow-hidden shadow-sm border border-slate-700 min-h-[480px] flex flex-col relative">
            <div className="bg-navy-900/90 text-white px-4 py-2 text-xs flex justify-between items-center border-b border-navy-700 z-10">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>{isDemoData ? "Demonstration Geolocation Nodes (Demo Mode)" : "Live Spatial Incident Grid"}</span>
              </span>
              <span className="text-[10px] text-slate-400">Total Nodes: {filteredIncidents.length}</span>
            </div>

            {/* Interactive GIS Representation */}
            <div className="flex-1 bg-gradient-to-br from-slate-900 via-navy-900 to-slate-800 p-6 flex flex-col justify-center items-center relative">
              <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#00A896_1px,transparent_1px)] [background-size:16px_16px]"></div>
              
              {filteredIncidents.length === 0 ? (
                <div className="text-slate-400 text-xs text-center z-10">
                  No active incidents match the selected severity filter.
                </div>
              ) : (
                <div className="w-full max-w-lg space-y-3 z-10 max-h-[420px] overflow-y-auto pr-1">
                  <div className="text-center text-xs text-slate-400 mb-2">
                    Click any geographical incident node below to inspect risk intelligence:
                  </div>

                  {filteredIncidents.map((inc) => {
                    const isSelected = selectedIncident?.id === inc.id;
                    const isCritical = inc.severity === 'Critical';

                    return (
                      <button
                        key={inc.id}
                        onClick={() => setSelectedIncident(inc)}
                        className={`w-full text-left p-3.5 rounded-lg border transition flex items-center justify-between ${
                          isSelected 
                            ? 'bg-civic-teal/20 border-civic-teal text-white shadow-lg' 
                            : 'bg-navy-800/80 hover:bg-navy-800 border-navy-700 text-slate-200'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className={`w-3.5 h-3.5 rounded-full flex-shrink-0 ${
                            isCritical ? 'bg-red-500 animate-pulse' : 'bg-civic-amber'
                          }`} />
                          <div>
                            <div className="text-xs font-bold">{inc.title}</div>
                            <div className="text-[11px] text-slate-400">{inc.location}</div>
                          </div>
                        </div>

                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-navy-900 text-slate-300">
                          {inc.latitude ? `${inc.latitude.toFixed(4)}, ${inc.longitude?.toFixed(4)}` : 'Coordinates N/A'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Selected Incident Drawer */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4 flex flex-col justify-between">
            {selectedIncident ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                    selectedIncident.severity === 'Critical' ? 'bg-red-50 text-civic-red border-red-200' :
                    selectedIncident.severity === 'High' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                    'bg-slate-50 text-slate-700 border-slate-200'
                  }`}>
                    {selectedIncident.severity || 'Unassessed'}
                  </span>

                  <span className="text-xs text-slate-500 font-mono">
                    {selectedIncident.status}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-slate-900">{selectedIncident.title}</h2>
                <p className="text-xs text-slate-600 leading-relaxed">{selectedIncident.description}</p>

                <div className="pt-2 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
                  <div><strong>Address:</strong> {selectedIncident.location}</div>
                  <div><strong>Category:</strong> {selectedIncident.category}</div>
                  {selectedIncident.latest_analysis && (
                    <div className="text-teal-700 font-medium flex items-center space-x-1 pt-1">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Urgency Heuristic: {selectedIncident.latest_analysis.urgency_score} / 100</span>
                    </div>
                  )}
                </div>

                <div className="pt-4">
                  <Link
                    href={`/incident/${selectedIncident.id}`}
                    className="w-full inline-flex items-center justify-center space-x-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold py-2.5 rounded-lg transition"
                  >
                    <span>Open Full Triage View</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                Select an incident marker to view geographical details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
