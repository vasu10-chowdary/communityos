import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged, User } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "";
const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "";

const isConfigured = Boolean(
  apiKey && 
  !apiKey.includes("DummyKey") && 
  !apiKey.includes("YourFirebaseWebApiKey") &&
  projectId && 
  !projectId.includes("your-project-id") &&
  projectId !== "communityos-demo"
);

const firebaseConfig = {
  apiKey: apiKey || "AIzaSyDummyKeyForInitialBuildOnly12345",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "communityos-demo.firebaseapp.com",
  projectId: projectId || "communityos-demo",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "communityos-demo.appspot.com",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "1234567890",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:1234567890:web:abcdef123456"
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
export const auth = getAuth(app);
export const db = getFirestore(app);

export const isFirebaseConfigured = (): boolean => isConfigured;

export const getFirebaseConfigError = (): string | null => {
  if (!isConfigured) {
    return "Firebase client credentials are not configured. Populate NEXT_PUBLIC_FIREBASE_* variables in frontend/.env.local with credentials from Firebase Console.";
  }
  return null;
};

export const isProductionEnvironment = (): boolean => {
  return process.env.NEXT_PUBLIC_ENVIRONMENT === 'production';
};

export const signInDemoUser = async (): Promise<User | null> => {
  if (!isConfigured) {
    return null;
  }
  try {
    const cred = await signInAnonymously(auth);
    return cred.user;
  } catch (err: any) {
    console.warn("Firebase Anonymous Auth warning:", err.message || err);
    return null;
  }
};

export const getAuthToken = async (): Promise<string | null> => {
  if (auth.currentUser) {
    try {
      return await auth.currentUser.getIdToken();
    } catch (err: any) {
      console.warn("Failed to get Firebase ID token:", err.message || err);
      return null;
    }
  }
  return null;
};
