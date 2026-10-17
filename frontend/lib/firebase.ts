/**
 * CommunityOS Persistence & Auth Adapter
 *
 * Provides backwards-compatible adapters for legacy Firebase call sites,
 * forwarding to the FastAPI SQLite + JWT authentication backend.
 */

import { getAuthToken as getJwtAuthToken } from '@/lib/auth';

export const isFirebaseConfigured = (): boolean => true;

export const getFirebaseConfigError = (): string | null => null;

export const isProductionEnvironment = (): boolean => {
  return process.env.NEXT_PUBLIC_ENVIRONMENT === 'production';
};

export const signInDemoUser = async (): Promise<any> => {
  return { uid: 'demo-evaluator-uid' };
};

export const getAuthToken = async (): Promise<string | null> => {
  return await getJwtAuthToken();
};

// Safe fallback shims for any remaining direct Firestore/Auth calls
export const auth = {
  currentUser: null
};

export const db = {};
