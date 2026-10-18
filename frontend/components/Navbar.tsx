'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  LayoutDashboard,
  FilePlus2,
  MapPin,
  Truck,
  BarChart3,
  UserCheck,
  Info,
  AlertTriangle,
  RotateCcw,
  Menu,
  X
} from 'lucide-react';
import { useUserRole } from '@/lib/roleContext';
import { UserRole } from '@/types/incident';

export default function Navbar() {
  const { role, setRole, userName, isDemoData, resetDemo } = useUserRole();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleReset = () => {
    if (confirm('Reset demo environment? This will restore original seed incidents and units.')) {
      resetDemo();
    }
  };

  return (
    <header className="bg-navy-900 border-b border-navy-800 text-white sticky top-0 z-50 shadow-md">
      {/* Status / Demo Data Banner */}
      {isDemoData && (
        <div className="bg-amber-500 text-navy-900 px-4 py-1 text-center text-xs font-bold flex items-center justify-center space-x-2 shadow-inner">
          <AlertTriangle className="w-4 h-4 text-navy-900 flex-shrink-0" />
          <span>DEMO SANDBOX ACTIVE â€” Pre-seeded civic emergency data loaded. Actions persist in browser state.</span>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2 text-xl font-bold tracking-tight">
              <span className="p-2 bg-civic-teal rounded-lg text-white">
                <ShieldAlert className="w-5 h-5" />
              </span>
              <span>Community<span className="text-civic-teal">OS</span></span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-1 lg:space-x-3">
            <Link href="/dashboard" className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800 hover:text-white transition">
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </Link>
            <Link href="/report" className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800 hover:text-white transition">
              <FilePlus2 className="w-4 h-4 text-civic-teal" />
              <span>Report Hazard</span>
            </Link>
            <Link href="/map" className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800 hover:text-white transition">
              <MapPin className="w-4 h-4" />
              <span>Incident Map</span>
            </Link>
            <Link href="/resources" className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800 hover:text-white transition">
              <Truck className="w-4 h-4" />
              <span>Resources</span>
            </Link>
            <Link href="/analytics" className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800 hover:text-white transition">
              <BarChart3 className="w-4 h-4" />
              <span>Analytics</span>
            </Link>
          </nav>

          {/* Persona Switcher & Reset Button */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1.5 bg-navy-800 border border-navy-700 rounded-lg px-2.5 py-1 text-xs">
              <UserCheck className="w-3.5 h-3.5 text-civic-teal" />
              <span className="text-slate-400 hidden lg:inline">Persona:</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="bg-transparent text-white font-semibold focus:outline-none cursor-pointer"
                aria-label="Select Demo Role"
              >
                <option value="coordinator" className="bg-navy-900 text-white">Coordinator (Full Dispatch)</option>
                <option value="citizen" className="bg-navy-900 text-white">Citizen (Report & Track)</option>
                <option value="responder" className="bg-navy-900 text-white">Responder (Field Team)</option>
              </select>
            </div>

            <button
              onClick={handleReset}
              title="Reset Demo Data"
              className="p-1.5 bg-navy-800 hover:bg-navy-700 border border-navy-700 rounded-lg text-slate-300 hover:text-white transition"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 rounded-lg bg-navy-800 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile navigation drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-navy-900 border-t border-navy-800 px-4 pt-2 pb-4 space-y-1">
          <Link
            href="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800"
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Dashboard</span>
          </Link>
          <Link
            href="/report"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800"
          >
            <FilePlus2 className="w-4 h-4 text-civic-teal" />
            <span>Report Hazard</span>
          </Link>
          <Link
            href="/map"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800"
          >
            <MapPin className="w-4 h-4" />
            <span>Incident Map</span>
          </Link>
          <Link
            href="/resources"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800"
          >
            <Truck className="w-4 h-4" />
            <span>Resources</span>
          </Link>
          <Link
            href="/analytics"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-slate-200 hover:bg-navy-800"
          >
            <BarChart3 className="w-4 h-4" />
            <span>Analytics</span>
          </Link>
        </div>
      )}

      {/* Notice Banner */}
      <div className="bg-navy-800/60 border-t border-navy-700/50 px-4 py-1 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
        <Info className="w-3.5 h-3.5 text-civic-amber flex-shrink-0" />
        <span>Demonstration Deck â€” Authenticated as <strong>{userName}</strong>. Evaluator access enabled.</span>
      </div>
    </header>
  );
}
