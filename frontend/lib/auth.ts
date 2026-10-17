/**
 * CommunityOS JWT Client Authentication & Token Management
 *
 * Provides cryptographically signed HMAC-SHA256 JWT access tokens from
 * the FastAPI backend with role-based access control (RBAC).
 */

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'communityos_jwt_token';
const ROLE_STORAGE_KEY = 'communityos_active_role';

let inMemoryToken: string | null = null;

export interface TokenPayload {
  access_token: string;
  token_type: string;
  role: string;
  uid: string;
  name: string;
  email?: string;
  is_demo_auth: boolean;
  expires_in: number;
}

export function getStoredToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== 'undefined') {
    inMemoryToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    return inMemoryToken;
  }
  return null;
}

export function setStoredToken(token: string | null): void {
  inMemoryToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }
}

export function getStoredRole(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(ROLE_STORAGE_KEY) || 'coordinator';
  }
  return 'coordinator';
}

export function setStoredRole(role: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(ROLE_STORAGE_KEY, role);
  }
}

export async function requestAuthToken(
  role: string = 'coordinator',
  name?: string,
  uid?: string,
  pin?: string
): Promise<TokenPayload> {
  const url = `${BACKEND_BASE_URL}/api/auth/token`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, name, uid, pin }),
  });

  if (!response.ok) {
    let errorMsg = `Failed to obtain access token: HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {
      // Non-JSON
    }
    throw new Error(errorMsg);
  }

  const tokenData: TokenPayload = await response.json();
  setStoredToken(tokenData.access_token);
  setStoredRole(tokenData.role);
  return tokenData;
}

export async function getAuthToken(): Promise<string | null> {
  const existing = getStoredToken();
  if (existing) return existing;

  // If no token exists, request a default one for the active role
  try {
    const role = getStoredRole();
    const tokenData = await requestAuthToken(role);
    return tokenData.access_token;
  } catch (err) {
    console.warn("Could not auto-fetch access token:", err);
    return null;
  }
}
