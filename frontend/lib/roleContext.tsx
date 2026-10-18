'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole } from '@/types/incident';
import { resetDemoStore } from '@/lib/demoStore';

interface RoleContextType {
  role: UserRole;
  setRole: (role: UserRole) => Promise<void>;
  userId: string;
  userName: string;
  user: { uid: string; role: string; displayName: string; email?: string } | null;
  isDemoData: boolean;
  setIsDemoData: (val: boolean) => void;
  authReady: boolean;
  resetDemo: () => void;
}

const RoleContext = createContext<RoleContextType>({
  role: 'coordinator',
  setRole: async () => {},
  userId: 'coord-ops-lead',
  userName: 'Marcus Vance (Operations Coordinator)',
  user: null,
  isDemoData: true,
  setIsDemoData: () => {},
  authReady: true,
  resetDemo: () => {}
});

const ROLE_STORAGE_KEY = 'communityos_active_role_demo';

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<UserRole>('coordinator');
  const [authReady, setAuthReady] = useState(false);
  const [isDemoData, setIsDemoData] = useState(true);

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

  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(ROLE_STORAGE_KEY) as UserRole;
        if (saved && ['coordinator', 'citizen', 'responder'].includes(saved)) {
          setRoleState(saved);
        }
      } catch {
        // Safe localStorage fallback
      }
    }
    setAuthReady(true);
  }, []);

  const setRole = async (newRole: UserRole) => {
    setRoleState(newRole);
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(ROLE_STORAGE_KEY, newRole);
      } catch {
        // Safe localStorage fallback
      }
    }
  };

  const resetDemo = () => {
    resetDemoStore();
    setRole('coordinator');
  };

  const persona = getPersonaDetails(role);
  const user = {
    uid: persona.uid,
    role,
    displayName: persona.name,
    email: `${role}@communityos.demo`
  };

  return (
    <RoleContext.Provider value={{
      role,
      setRole,
      userId: persona.uid,
      userName: persona.name,
      user,
      isDemoData,
      setIsDemoData,
      authReady,
      resetDemo
    }}>
      {children}
    </RoleContext.Provider>
  );
};

export const useUserRole = () => useContext(RoleContext);
