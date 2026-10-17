'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Filter, 
  Plus, 
  MapPin, 
  Sparkles, 
  Layers,
  ChevronRight,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import { Incident, Resource, IncidentStatus, IncidentCategory } from '@/types/incident';
import { SEED_INCIDENTS, SEED_RESOURCES } from '@/lib/seedData';
import { db, signInDemoUser, isFirebaseConfigured, isProductionEnvironment } from '@/lib/firebase';
import { collection, onSnapshot, query, orderBy } from 'firebase/firestore';
import { useUserRole } from '@/lib/roleContext';

export default function DashboardPage() {
  const { isDemoData, setIsDemoData } = useUserRole();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [firestoreError, setFirestoreError] = useState<string | null>(null);

  useEffect(() => {
    // Attempt Firebase demo sign-in
    signInDemoUser();

    const isProd = isProductionEnvironment();
    const hasConfig = isFirebaseConfigured();

    if (isProd && !hasConfig) {
      setFirestoreError("CRITICAL: Cloud Firestore is not configured in this production environment. Please configure NEXT_PUBLIC_FIREBASE_* environment variables.");
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
          setIsDemoData(false);
        } else if (!isProd) {
          // Empty remote database in development: load seed data
          setIncidents(SEED_INCIDENTS);
          setResources(SEED_RESOURCES);
          setIsDemoData(true);
        } else {
          setIncidents([]);
          setIsDemoData(false);
        }
      }, (err) => {
        setLoading(false);
        if (isProd) {
          setFirestoreError(`Firestore Connection Error: ${err.message}. Live Firestore access is strictly enforced in production.`);
        } else {
          console.info("Firestore live listener in development fallback mode with seeded data:", err.message);
          setIncidents(SEED_INCIDENTS);
          setResources(SEED_RESOURCES);
          setIsDemoData(true);
        }
      });
      return () => unsubscribe();
    } catch (e: any) {
      setLoading(false);
      if (isProd) {
        setFirestoreError(`Firestore Initialization Failed: ${e.message}`);
      } else {
        console.info("Firestore initialization development fallback:", e);
        setIncidents(SEED_INCIDENTS);
        setResources(SEED_RESOURCES);
        setIsDemoData(true);
      }
    }
  }, [setIsDemoData]);

  // Filter calculations
  const filteredIncidents = incidents.filter(item => {
    const matchStatus = statusFilter === 'ALL' || item.status === statusFilter;
    const matchCategory = categoryFilter === 'ALL' || item.category === categoryFilter;
    return matchStatus && matchCategory;
  });

  const totalCount = incidents.length;
  const activeCount = incidents.filter(i => i.status !== 'Resolved').length;
  const criticalCount = incidents.filter(i => i.severity === 'Critical' && i.status !== 'Resolved').length;
  const unassignedCount = incidents.filter(i => !i.assigned_resource_id && i.status !== 'Resolved').length;
  const resolvedCount = incidents.filter(i => i.status === 'Resolved').length;
  const availableResources = resources.filter(r => r.availability === 'Available').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header and Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight">
            Community Operations Command
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Real-time incident ingestion, Gemini risk assessment, and resource coordination.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/report"
            className="inline-flex items-center space-x-2 bg-civic-teal hover:bg-teal-600 text-white font-medium px-4 py-2.5 rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Incident Report</span>
          </Link>
          <Link
            href="/map"
            className="inline-flex items-center space-x-2 bg-navy-800 hover:bg-navy-700 text-white font-medium px-4 py-2.5 rounded-lg shadow-sm transition"
          >
            <MapPin className="w-4 h-4 text-civic-amber" />
            <span>Incident Map</span>
          </Link>
        </div>
      </div>

      {firestoreError && (
        <div className="p-4 bg-red-100 border border-red-300 rounded-xl text-red-900 text-sm flex items-start space-x-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold">Production Database Error</h4>
            <p>{firestoreError}</p>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase text-slate-500">Total Incidents</div>
          <div className="text-2xl font-bold text-navy-900 mt-1">{totalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Tracked records</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase text-civic-amber">Active Incidents</div>
          <div className="text-2xl font-bold text-slate-800 mt-1">{activeCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Requiring action</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-red-200 shadow-sm bg-red-50/20">
          <div className="text-xs font-semibold uppercase text-civic-red">Critical Severity</div>
          <div className="text-2xl font-bold text-civic-red mt-1">{criticalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Urgent triage</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase text-slate-500">Unassigned</div>
          <div className="text-2xl font-bold text-slate-700 mt-1">{unassignedCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Needs resource</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase text-civic-green">Resolved</div>
          <div className="text-2xl font-bold text-civic-green mt-1">{resolvedCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Completed</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase text-civic-teal">Ready Units</div>
          <div className="text-2xl font-bold text-civic-teal mt-1">{availableResources}</div>
          <div className="text-[11px] text-slate-400 mt-1">Of {resources.length} resources</div>
        </div>
      </div>

      {/* Main Incident Feed & Filter Controls */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-50/50">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-slate-500" />
            <h2 className="font-semibold text-slate-900">Community Incident Queue</h2>
            <span className="text-xs bg-slate-200 px-2 py-0.5 rounded-full text-slate-700 font-medium">
              {filteredIncidents.length} shown
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-civic-teal"
            >
              <option value="ALL">All Statuses</option>
              <option value="Reported">Reported</option>
              <option value="In Review">In Review</option>
              <option value="Resource Dispatched">Resource Dispatched</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="text-xs bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-civic-teal"
            >
              <option value="ALL">All Categories</option>
              <option value="Flooding and waterlogging">Flooding & waterlogging</option>
              <option value="Blocked drainage">Blocked drainage</option>
              <option value="Water shortages">Water shortages</option>
              <option value="Fallen trees and blocked roads">Fallen trees & roads</option>
              <option value="Damaged infrastructure">Damaged infrastructure</option>
              <option value="Electrical hazards">Electrical hazards</option>
              <option value="Other community assistance requests">Other assistance</option>
            </select>
          </div>
        </div>

        {/* Incidents Table / List */}
        <div className="divide-y divide-slate-200">
          {filteredIncidents.length === 0 ? (
            <div className="text-center py-12 px-4">
              <ShieldAlert className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 font-medium text-sm">No incidents match current filter criteria.</p>
              <p className="text-slate-400 text-xs mt-1">Try resetting the status or category dropdowns.</p>
            </div>
          ) : (
            filteredIncidents.map((incident) => {
              const isCritical = incident.severity === 'Critical';
              const isHigh = incident.severity === 'High';
              const isResolved = incident.status === 'Resolved';

              return (
                <div key={incident.id} className="p-4 sm:p-5 hover:bg-slate-50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1.5 max-w-3xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                        isCritical ? 'bg-red-50 text-civic-red border-red-200' :
                        isHigh ? 'bg-amber-50 text-civic-amber border-amber-200' :
                        isResolved ? 'bg-emerald-50 text-civic-green border-emerald-200' :
                        'bg-slate-100 text-slate-600 border-slate-200'
                      }`}>
                        {incident.severity || 'Pending AI Assessment'}
                      </span>

                      <span className="text-xs bg-navy-100/60 text-navy-800 px-2 py-0.5 rounded-md font-medium">
                        {incident.category}
                      </span>

                      <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                        isResolved ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-700'
                      }`}>
                        Status: {incident.status}
                      </span>

                      {incident.is_demo && (
                        <span className="text-[10px] bg-indigo-50 text-indigo-600 border border-indigo-200 px-1.5 py-0.2 rounded font-mono">
                          DEMO RECORD
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-semibold text-slate-900">
                      {incident.title}
                    </h3>

                    <p className="text-xs sm:text-sm text-slate-600 line-clamp-2">
                      {incident.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                      <div className="flex items-center space-x-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        <span>{incident.location}</span>
                      </div>

                      {incident.latest_analysis && (
                        <div className="flex items-center space-x-1 text-teal-700 font-medium">
                          <Sparkles className="w-3.5 h-3.5 text-civic-teal" />
                          <span>Urgency Heuristic: {incident.latest_analysis.urgency_score}/100</span>
                        </div>
                      )}

                      {incident.assigned_resource_name && (
                        <div className="text-indigo-600 font-medium">
                          Assigned: {incident.assigned_resource_name}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2">
                    <Link
                      href={`/incident/${incident.id}`}
                      className="inline-flex items-center space-x-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-medium px-3.5 py-2 rounded-lg transition"
                    >
                      <span>Review & Triage</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
