/**
 * CommunityOS Standalone API Client
 *
 * Provides transparent fallback to demoStore for competition demo.
 * Zero external backend or network dependencies required.
 */

import { getIncidents, getResources } from '@/lib/demoStore';

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

export async function apiFetch<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // If a live remote backend URL is explicitly provided, attempt network request
  if (BACKEND_BASE_URL && !BACKEND_BASE_URL.includes('localhost')) {
    try {
      const url = `${BACKEND_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (networkErr) {
      console.info('[apiFetch] Remote backend unreachable, falling back to local demo store:', networkErr);
    }
  }

  // Seamless standalone demo resolution
  if (endpoint.includes('/resources/pool')) {
    return getResources() as unknown as T;
  }

  if (endpoint.includes('/metrics/summary')) {
    const inc = getIncidents();
    const res = getResources();
    const resolved = inc.filter(i => i.status === 'Resolved').length;
    const inProgress = inc.filter(i => i.status === 'In Progress').length;
    const reported = inc.filter(i => i.status === 'Reported').length;
    const dispatched = inc.filter(i => i.status === 'Resource Dispatched').length;
    const avgUrgency = Math.round(inc.reduce((acc, curr) => acc + (curr.latest_analysis?.urgency_score || 50), 0) / (inc.length || 1));

    return {
      total_incidents: inc.length,
      resolved_incidents: resolved,
      in_progress_incidents: inProgress,
      reported_incidents: reported,
      dispatched_incidents: dispatched,
      average_urgency: avgUrgency,
      category_distribution: inc.reduce((acc: Record<string, number>, curr) => {
        acc[curr.category] = (acc[curr.category] || 0) + 1;
        return acc;
      }, {}),
      total_resources: res.length,
      available_resources: res.filter(r => r.availability === 'Available').length,
      busy_resources: res.filter(r => r.availability === 'Busy').length
    } as unknown as T;
  }

  if (endpoint.includes('/incidents')) {
    return getIncidents() as unknown as T;
  }

  return {} as unknown as T;
}
