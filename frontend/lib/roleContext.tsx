'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { UserRole } from '@/types/incident';
import { requestAuthToken, getStoredRole, setStoredRole } from '@/lib/auth';

interface RoleContextType {
  role: UserRole;
  setRole: (role: UserRole) => Promise<void>;
  userId: string;
  userName: string;
  user: { uid: string; role: string; displayName: string; email?: string } | null;
  isDemoData: boolean;
  setIsDemoData: (val: boolean) => void;
  authReady: boolean;
}

const RoleContext = createContext<RoleContextType>({
  role: 'coordinator',
  setRole: async () => {},
  userId: 'coord-ops-lead',
  userName: 'Marcus Vance (Operations Coordinator)',
  user: null,
  isDemoData: false,
  setIsDemoData: () => {},
  authReady: false
});

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<UserRole>('coordinator');
  const [user, setUser] = useState<{ uid: string; role: string; displayName: string; email?: string } | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [isDemoData, setIsDemoData] = useState(false);

  const getPersonaDetails = (currentRole: UserRole) => {
    switch (currentRole) {
      case 'citizen':
        return {
          uid: 'citizen-demo-1',
          name: 'Alex Morgan (Community Resident)'
        };
      case 'responder':
        return {
          uid: 'resp-unit-alpha',
          name: 'Sarah Jenkins (Field Unit Alpha)'
        };
      case 'coordinator':
      default:
        return {
          uid: 'coord-ops-lead',
          name: 'Marcus Vance (Operations Coordinator)'
        };
    }
  };

  const syncAuth = useCallback(async (targetRole: UserRole) => {
    try {
      const persona = getPersonaDetails(targetRole);
      const tokenPayload = await requestAuthToken(targetRole, persona.name, persona.uid);
      setRoleState(tokenPayload.role as UserRole);
      setUser({
        uid: tokenPayload.uid,
        role: tokenPayload.role,
        displayName: tokenPayload.name,
        email: tokenPayload.email
      });
      setStoredRole(tokenPayload.role);
    } catch (err) {
      console.warn("Could not sync JWT token with backend:", err);
      const persona = getPersonaDetails(targetRole);
      setRoleState(targetRole);
      setUser({
        uid: persona.uid,
        role: targetRole,
        displayName: persona.name
      });
    } finally {
      setAuthReady(true);
    }
  }, []);

  useEffect(() => {
    const savedRole = (getStoredRole() as UserRole) || 'coordinator';
    syncAuth(savedRole);
  }, [syncAuth]);

  const setRole = async (newRole: UserRole) => {
    await syncAuth(newRole);
  };

  const persona = getPersonaDetails(role);
  const userId = user?.uid || persona.uid;
  const userName = user?.displayName || persona.name;

  return (
    <RoleContext.Provider value={{
      role,
      setRole,
      userId,
      userName,
      user,
      isDemoData,
      setIsDemoData,
      authReady
    }}>
      {children}
    </RoleContext.Provider>
  );
};

export const useUserRole = () => useContext(RoleContext);
