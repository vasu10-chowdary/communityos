import Link from 'next/link';
import { 
  ShieldAlert, 
  Sparkles, 
  ArrowRight, 
  Activity, 
  Layers, 
  Cpu, 
  Database, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-navy-900 via-navy-800 to-slate-900 text-white py-20 px-4 sm:px-6 lg:px-8 border-b border-navy-700">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center space-x-2 bg-navy-700/60 border border-navy-600 px-4 py-1.5 rounded-full text-xs font-semibold text-civic-teal tracking-wide uppercase">
            <Sparkles className="w-4 h-4 text-civic-teal" />
            <span>AI-Driven Civic Emergency Coordination Prototype</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight">
            Rapid Community Response <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-civic-teal">
              Powered by Google Gemini
            </span>
          </h1>

          <p className="max-w-3xl mx-auto text-lg sm:text-xl text-slate-300 font-normal leading-relaxed">
            Report local disruptions, analyze cascading risks in real-time with Google GenAI, prioritize municipal hazards, and dispatch community resources through a single unified command deck.
          </p>

          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-4">
            <Link 
              href="/dashboard" 
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-civic-teal hover:bg-teal-600 text-white font-medium px-6 py-3.5 rounded-lg shadow-lg hover:shadow-xl transition transform active:scale-95"
            >
              <span>Open Operations Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link 
              href="/report" 
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-navy-800 hover:bg-navy-700 text-slate-200 border border-slate-700 font-medium px-6 py-3.5 rounded-lg transition"
            >
              <AlertTriangle className="w-4 h-4 text-civic-amber" />
              <span>Submit Incident Report</span>
            </Link>
          </div>

          {/* Quick Evaluator Access Info */}
          <div className="pt-6 max-w-2xl mx-auto bg-navy-800/80 border border-navy-700 rounded-lg p-3 text-xs text-slate-300 flex items-center justify-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-civic-green flex-shrink-0" />
            <span>Competition Demo: Instant client-side execution with persistent local storage. Zero configuration required.</span>
          </div>
        </div>
      </section>

      {/* Core Workflow Pillars */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <div className="text-center space-y-3 mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            The Community Incident Lifecycle
          </h2>
          <p className="text-slate-600 max-w-2xl mx-auto text-sm sm:text-base">
            From local resident observation to structured resolution tracking with transparent AI triage heuristics.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="w-12 h-12 bg-teal-50 text-civic-teal rounded-lg flex items-center justify-center">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">1. Citizen Field Reporting</h3>
            <p className="text-slate-600 text-sm leading-relaxed">
              Capture vital details: category, description, physical landmarks, and geographical coordinates for fast triaging.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="w-12 h-12 bg-amber-50 text-civic-amber rounded-lg flex items-center justify-center">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">2. Gemini Risk Triage</h3>
            <p className="text-slate-600 text-sm leading-relaxed">
              FastAPI backend triggers Google Gen AI to generate urgency scores, detect secondary hazards, and recommend tactical resources.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">3. Resource Coordination</h3>
            <p className="text-slate-600 text-sm leading-relaxed">
              Assign available municipal and volunteer units with atomic consistency, preventing double-booking and tracking updates.
            </p>
          </div>
        </div>
      </section>

      {/* Tech Integration Badges & Competition Disclaimer */}
      <section className="bg-slate-100 py-12 px-4 border-t border-slate-200 mt-auto">
        <div className="max-w-7xl mx-auto space-y-6">
          <h3 className="text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
            Core Architecture & Capabilities
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <div className="font-semibold text-sm text-slate-900">Next.js 15 App Router</div>
              <div className="text-xs text-slate-500 mt-1">Responsive Civic Interface</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <div className="font-semibold text-sm text-slate-900">Google Gemini Gen AI</div>
              <div className="text-xs text-slate-500 mt-1">Multimodal Risk Triage Engine</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <div className="font-semibold text-sm text-slate-900">Reactive State Store</div>
              <div className="text-xs text-slate-500 mt-1">Browser-Persisted Incident DB</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <div className="font-semibold text-sm text-slate-900">Role-Based Access</div>
              <div className="text-xs text-slate-500 mt-1">Citizen, Coordinator, Responder</div>
            </div>
          </div>

          <div className="text-center text-xs text-slate-500 pt-2 border-t border-slate-200/60 max-w-2xl mx-auto">
            <strong>DEMO PROTOTYPE DISCLAIMER:</strong> CommunityOS is an engineering competition prototype. Emergency hazard reports generated here are processed in browser memory/localStorage and are NOT connected to municipal 911 or live dispatchers.
          </div>
        </div>
      </section>
    </div>
  );
}
