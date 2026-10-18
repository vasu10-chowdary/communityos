/**
 * CommunityOS Standalone Demo Auth Client
 *
 * Provides mock token resolution without external network requests.
 */

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
  return 'demo-session-token-communityos';
}

export function setStoredToken(token: string | null): void {
  // Safe no-op for demo
}

export function getStoredRole(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('communityos_active_role_demo') || 'coordinator';
  }
  return 'coordinator';
}

export function setStoredRole(role: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('communityos_active_role_demo', role);
  }
}

export async function requestAuthToken(
  role: string = 'coordinator',
  name?: string,
  uid?: string
): Promise<TokenPayload> {
  return {
    access_token: 'demo-session-token-communityos',
    token_type: 'bearer',
    role,
    uid: uid || `demo-${role}`,
    name: name || `${role} user`,
    email: `${role}@communityos.demo`,
    is_demo_auth: true,
    expires_in: 86400
  };
}

export async function getAuthToken(): Promise<string | null> {
  return 'demo-session-token-communityos';
}
