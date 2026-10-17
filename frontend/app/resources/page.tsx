'use client';

import React, { useState, useEffect } from 'react';
import { 
  Truck, 
  CheckCircle2, 
  AlertCircle, 
  Plus, 
  Clock, 
  MapPin, 
  Shield,
  Loader2,
  AlertTriangle,
  Lock
} from 'lucide-react';
import { Resource } from '@/types/incident';
import { SEED_RESOURCES } from '@/lib/seedData';
import { apiFetch } from '@/lib/api';
import { useUserRole } from '@/lib/roleContext';

export default function ResourcesPage() {
  const { role, isDemoData, setIsDemoData } = useUserRole();
  const [resources, setResources] = useState<Resource[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [type, setType] = useState('Heavy Machinery & Debris Clearance');
  const [serviceArea, setServiceArea] = useState('');
  const [capacity, setCapacity] = useState('');
  const [saving, setSaving] = useState(false);

  const loadResources = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const list = await apiFetch<Resource[]>('/api/incidents/resources/pool');
      if (list && list.length > 0) {
        setResources(list);
        setIsDemoData(list.every(r => r.is_demo));
      } else {
        setResources(SEED_RESOURCES);
        setIsDemoData(true);
      }
    } catch (err: any) {
      console.info("Using seed fallback on resources:", err.message);
      setResources(SEED_RESOURCES);
      setIsDemoData(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResources();
  }, [setIsDemoData]);

  const handleAddResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    if (role !== 'coordinator') {
      alert('Role Permission Error: Only Coordinators can register emergency resources.');
      return;
    }

    setSaving(true);
    try {
      const created = await apiFetch('/api/incidents/resources/pool', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          type,
          service_area: serviceArea.trim() || 'Central District',
          capacity: capacity.trim() || 'Standard Response Pack',
        })
      });
      setActionSuccess(`Registered ${created.name || name} successfully.`);
      setShowAddModal(false);
      setName('');
      setCapacity('');
      setServiceArea('');
      await loadResources();
    } catch (err: any) {
      alert(`Failed to add resource: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const isCoordinator = role === 'coordinator';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight flex items-center space-x-2">
            <Truck className="w-8 h-8 text-civic-teal" />
            <span>Community Resource Coordination</span>
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Track available civic assets, pump trailers, chainsaw crews, and volunteer units.
          </p>
        </div>

        {isCoordinator ? (
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center space-x-2 bg-civic-teal hover:bg-teal-600 text-white font-medium px-4 py-2.5 rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>Register New Resource</span>
          </button>
        ) : (
          <div className="inline-flex items-center space-x-1.5 bg-slate-100 text-slate-500 text-xs px-3 py-2 rounded-lg border border-slate-200">
            <Lock className="w-3.5 h-3.5 text-slate-400" />
            <span>Coordinator role required to add resources (Current: {role})</span>
          </div>
        )}
      </div>

      {actionSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-red-100 border border-red-300 rounded-xl text-red-900 text-sm flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center space-y-2">
          <Loader2 className="w-8 h-8 animate-spin text-civic-teal" />
          <span className="text-sm">Loading resource inventory from Cloud Firestore...</span>
        </div>
      ) : resources.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500">
          No resource records found in the database.
        </div>
      ) : (
        /* Grid of Resources */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resources.map((res) => {
            const isAvailable = res.availability === 'Available';
            const isBusy = res.availability === 'Busy';

            return (
              <div key={res.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                      isAvailable ? 'bg-emerald-50 text-civic-green border-emerald-200' :
                      isBusy ? 'bg-amber-50 text-civic-amber border-amber-200' :
                      'bg-slate-100 text-slate-700 border-slate-200'
                    }`}>
                      {res.availability}
                    </span>

                    {res.is_demo && (
                      <span className="text-[10px] bg-indigo-50 text-indigo-600 border border-indigo-200 px-1.5 py-0.5 rounded font-mono">
                        DEMO UNIT
                      </span>
                    )}
                  </div>

                  <h3 className="font-bold text-slate-900 text-base">{res.name}</h3>
                  <div className="text-xs text-slate-600 font-medium">{res.type}</div>

                  <div className="pt-2 border-t border-slate-100 space-y-1.5 text-xs text-slate-500">
                    <div className="flex items-center space-x-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>Coverage: {res.service_area}</span>
                    </div>
                    <div>
                      <strong>Capacity:</strong> {res.capacity}
                    </div>
                    {res.assigned_incident && (
                      <div className="text-amber-800 font-medium">
                        Assigned to: Incident #{res.assigned_incident}
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-2 flex items-center justify-between">
                  <span>Updated: {res.updated_at ? new Date(res.updated_at).toLocaleTimeString() : 'N/A'}</span>
                  <span className="font-mono text-[10px]">ID: {res.id}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Resource Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-navy-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h2 className="text-lg font-bold text-slate-900">Add Community Resource</h2>
            <form onSubmit={handleAddResource} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Resource / Unit Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Ward 4 High-Capacity Sump Pump"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-civic-teal focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Category Type</label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-1 focus:ring-civic-teal focus:outline-none"
                >
                  <option value="Flooding & Sump Pump Mitigation">Flooding & Sump Pump Mitigation</option>
                  <option value="Heavy Tree & Debris Removal">Heavy Tree & Debris Removal</option>
                  <option value="Emergency Potable Water Logistics">Emergency Potable Water Logistics</option>
                  <option value="First Response & Sandbagging">First Response & Sandbagging</option>
                  <option value="Infrastructure Inspection Crew">Infrastructure Inspection Crew</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Service Area</label>
                <input
                  type="text"
                  placeholder="e.g., Downtown & Eastside Districts"
                  value={serviceArea}
                  onChange={(e) => setServiceArea(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-civic-teal focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Capacity / Equipment Specs</label>
                <input
                  type="text"
                  placeholder="e.g., 400 GPM pump, 2 operators"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-civic-teal focus:outline-none"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-civic-teal hover:bg-teal-600 rounded-lg shadow-sm disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Resource'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
