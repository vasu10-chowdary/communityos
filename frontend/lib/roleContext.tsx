'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole } from '@/types/incident';
import { auth, db, signInDemoUser, isFirebaseConfigured } from '@/lib/firebase';
import { onAuthStateChanged, User } from 'firebase/auth';
import { doc, getDoc, setDoc } from 'firebase/firestore';

interface RoleContextType {
  role: UserRole;
  setRole: (role: UserRole) => Promise<void>;
  userId: string;
  userName: string;
  user: User | null;
  isDemoData: boolean;
  setIsDemoData: (val: boolean) => void;
  authReady: boolean;
}

const RoleContext = createContext<RoleContextType>({
  role: 'coordinator',
  setRole: async () => {},
  userId: 'evaluator-coord-1',
  userName: 'Sarah Jenkins (Emergency Coordinator)',
  user: null,
  isDemoData: true,
  setIsDemoData: () => {},
  authReady: false
});

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<UserRole>('coordinator');
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [isDemoData, setIsDemoData] = useState(!isFirebaseConfigured());

  // Role details mapping
  const getUserDetails = (currentRole: UserRole, currentUid?: string) => {
    switch (currentRole) {
      case 'citizen':
        return { 
          id: currentUid || 'citizen-demo-1', 
          name: 'Alex Rivera (Resident / Reporter)' 
        };
      case 'responder':
        return { 
          id: currentUid || 'responder-unit-1', 
          name: 'Officer Torres (Rapid Field Responder)' 
        };
      case 'coordinator':
      default:
        return { 
          id: currentUid || 'evaluator-coord-1', 
          name: 'Commander Jenkins (Operations Coordinator)' 
        };
    }
  };

  useEffect(() => {
    // Listen to Firebase Auth state
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        // Try fetching role from Firestore users/{uid}
        try {
          const userDocRef = doc(db, 'users', currentUser.uid);
          const snap = await getDoc(userDocRef);
          if (snap.exists()) {
            const data = snap.data();
            if (data?.role && ['citizen', 'coordinator', 'responder'].includes(data.role)) {
              setRoleState(data.role as UserRole);
            }
          } else {
            // Evaluator default role is coordinator
            await setDoc(userDocRef, {
              role: 'coordinator',
              name: 'Commander Jenkins (Operations Coordinator)',
              created_at: new Date().toISOString()
            }, { merge: true });
            setRoleState('coordinator');
          }
        } catch (e) {
          console.info("Firestore user document lookup in local fallback mode:", e);
        }
      } else {
        // Sign in anonymously for seamless evaluator demo
        signInDemoUser();
      }
      setAuthReady(true);
    });

    return () => unsubscribe();
  }, []);

  const setRole = async (newRole: UserRole) => {
    setRoleState(newRole);
    if (user) {
      try {
        const userDocRef = doc(db, 'users', user.uid);
        await setDoc(userDocRef, {
          role: newRole,
          updated_at: new Date().toISOString()
        }, { merge: true });
        console.info(`Synced role '${newRole}' to Firestore users/${user.uid}`);
      } catch (err) {
        console.info("Firestore role sync skipped (local/demo mode):", err);
      }
    }
  };

  const { id: userId, name: userName } = getUserDetails(role, user?.uid);

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
