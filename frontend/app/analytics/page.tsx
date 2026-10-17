'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  ShieldAlert, 
  Activity,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { Incident, Resource } from '@/types/incident';
import { SEED_INCIDENTS, SEED_RESOURCES } from '@/lib/seedData';
import { apiFetch } from '@/lib/api';
import { useUserRole } from '@/lib/roleContext';

export default function AnalyticsPage() {
  const { isDemoData, setIsDemoData } = useUserRole();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [incList, resList] = await Promise.all([
        apiFetch<Incident[]>('/api/incidents'),
        apiFetch<Resource[]>('/api/incidents/resources/pool')
      ]);

      if (incList && incList.length > 0) {
        setIncidents(incList);
        setIsDemoData(incList.every(i => i.is_demo));
      } else {
        setIncidents(SEED_INCIDENTS);
        setIsDemoData(true);
      }

      if (resList && resList.length > 0) {
        setResources(resList);
      } else {
        setResources(SEED_RESOURCES);
      }
    } catch (err: any) {
      console.info("Using seed fallback on analytics:", err.message);
      setIncidents(SEED_INCIDENTS);
      setResources(SEED_RESOURCES);
      setIsDemoData(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalyticsData();
  }, [setIsDemoData]);

  // Dynamic calculations from live data
  const categoryCounts: Record<string, number> = {};
  incidents.forEach(i => {
    categoryCounts[i.category] = (categoryCounts[i.category] || 0) + 1;
  });

  const statusCounts: Record<string, number> = {};
  incidents.forEach(i => {
    statusCounts[i.status] = (statusCounts[i.status] || 0) + 1;
  });

  const totalIncidents = incidents.length;
  const resolvedCount = incidents.filter(i => i.status === 'Resolved').length;
  const resolutionRate = totalIncidents > 0 ? Math.round((resolvedCount / totalIncidents) * 100) : 0;

  const assessedIncidents = incidents.filter(i => i.latest_analysis?.urgency_score);
  const avgUrgency = assessedIncidents.length > 0
    ? Math.round(assessedIncidents.reduce((acc, curr) => acc + (curr.latest_analysis?.urgency_score || 0), 0) / assessedIncidents.length)
    : 75;

  const totalResources = resources.length;
  const availableResources = resources.filter(r => r.availability === 'Available').length;
  const resourceReadiness = totalResources > 0 ? Math.round((availableResources / totalResources) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight flex items-center space-x-2">
            <BarChart3 className="w-8 h-8 text-civic-teal" />
            <span>Incident Intelligence Analytics</span>
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Real-time hazard distribution, category patterns, and response lifecycle performance.
          </p>
        </div>

        {isDemoData && (
          <span className="text-xs bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1.5 rounded-lg font-medium">
            Demo Analytics Active (Offline Fallback)
          </span>
        )}
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
          <span className="text-sm">Aggregating real-time incident analytics from Cloud Firestore...</span>
        </div>
      ) : (
        <>
          {/* High-level performance cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="w-12 h-12 bg-teal-50 text-civic-teal rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6" />
              </div>
              <div>
                <div className="text-xs uppercase font-semibold text-slate-500">Average Urgency Score</div>
                <div className="text-2xl font-bold text-navy-900 mt-0.5">{avgUrgency} / 100</div>
                <div className="text-[11px] text-slate-400">Synthesized via Google Gemini</div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="w-12 h-12 bg-emerald-50 text-civic-green rounded-lg flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <div className="text-xs uppercase font-semibold text-slate-500">Resolution Rate</div>
                <div className="text-2xl font-bold text-slate-900 mt-0.5">{resolutionRate}%</div>
                <div className="text-[11px] text-slate-400">{resolvedCount} of {totalIncidents} incidents resolved</div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="w-12 h-12 bg-amber-50 text-civic-amber rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <div className="text-xs uppercase font-semibold text-slate-500">Resource Readiness</div>
                <div className="text-2xl font-bold text-slate-900 mt-0.5">{resourceReadiness}%</div>
                <div className="text-[11px] text-slate-400">{availableResources} of {totalResources} units ready</div>
              </div>
            </div>
          </div>

          {/* Breakdowns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="font-bold text-slate-900 text-base">Incidents by Hazard Category</h2>
              {Object.keys(categoryCounts).length === 0 ? (
                <div className="text-xs text-slate-400 text-center py-4">No incident reports recorded yet.</div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(categoryCounts).map(([cat, count]) => (
                    <div key={cat} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium text-slate-700">
                        <span>{cat}</span>
                        <span className="font-bold">{count}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-civic-teal h-full rounded-full" 
                          style={{ width: `${totalIncidents > 0 ? (count / totalIncidents) * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="font-bold text-slate-900 text-base">Status Lifecycle Distribution</h2>
              {Object.keys(statusCounts).length === 0 ? (
                <div className="text-xs text-slate-400 text-center py-4">No status activity recorded yet.</div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(statusCounts).map(([status, count]) => (
                    <div key={status} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium text-slate-700">
                        <span>{status}</span>
                        <span className="font-bold">{count}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-navy-700 h-full rounded-full" 
                          style={{ width: `${totalIncidents > 0 ? (count / totalIncidents) * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
