import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.core.config import settings

db = None
auth_service = None
init_error: Optional[str] = None

def init_firebase():
    global db, auth_service, init_error
    init_error = None
    
    if not firebase_admin._apps:
        try:
            if settings.FIREBASE_SERVICE_ACCOUNT_KEY and os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_KEY):
                cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
                firebase_admin.initialize_app(cred, {'projectId': settings.FIREBASE_PROJECT_ID})
            else:
                # In Google Cloud Run or with Google Application Default Credentials
                firebase_admin.initialize_app(options={'projectId': settings.FIREBASE_PROJECT_ID})
        except Exception as e:
            init_error = str(e)
            print(f"[Firebase Init Warning] Could not initialize Firebase Admin SDK: {e}")
            if settings.is_production():
                print(f"[CRITICAL] Production Firebase initialization failed: {e}")

    try:
        db = firestore.client()
        auth_service = auth
    except Exception as e:
        if not init_error:
            init_error = str(e)
        print(f"[Firestore Warning] Firestore client initialization skipped/failed: {e}")
        db = None

def get_db():
    global db
    if db is None and settings.is_production():
        # In production, do not silently fallback! Fail loudly.
        raise RuntimeError(f"Cloud Firestore is not initialized in production: {init_error or 'Unknown initialization error'}")
    return db

def get_init_error():
    return init_error
