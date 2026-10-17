# CommunityOS Deployment Guide

This guide provides the exact production deployment steps for **Google Cloud Run**, **Firebase Hosting / Vercel**, and **Google Gen AI**.

## 1. Prerequisites
- Google Cloud Project with Billing Enabled
- Google Cloud CLI (`gcloud`) installed
- Gemini API Key from Google AI Studio (`https://aistudio.google.com/`)
- Firebase CLI (`firebase-tools`)

---

## 2. Backend Deployment to Google Cloud Run

### Step 2.1: Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2.2: Enable Cloud Run & Artifact Registry APIs
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### Step 2.3: Build & Deploy Container to Cloud Run
From the `backend/` directory:
```bash
cd backend
gcloud run deploy communityos-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="YOUR_GEMINI_API_KEY",ENVIRONMENT="production",PORT="8080"
```
*Take note of the service URL emitted by Cloud Run (e.g. `https://communityos-backend-xyz-uc.a.run.app`).*

---

## 3. Firebase Firestore & Security Rules Setup

### Step 3.1: Initialize Firebase
```bash
firebase login
firebase use YOUR_PROJECT_ID
```

### Step 3.2: Deploy Security Rules and Indexes
From the project root:
```bash
firebase deploy --only firestore:rules,firestore:indexes
```

---

## 4. Frontend Deployment (Vercel / Firebase Hosting)

### Deploying via Vercel:
1. Connect your GitHub repository to Vercel.
2. Set Root Directory to `frontend`.
3. Configure Environment Variables:
   - `NEXT_PUBLIC_BACKEND_URL`: URL of your Google Cloud Run service (e.g. `https://communityos-backend-xyz-uc.a.run.app`)
   - `NEXT_PUBLIC_FIREBASE_API_KEY`: Your Firebase Web API key
   - `NEXT_PUBLIC_FIREBASE_PROJECT_ID`: Your Firebase Project ID
   - `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`: `YOUR_PROJECT_ID.firebaseapp.com`
4. Click **Deploy**.

---

## 5. Verifying the Deployment
1. Hit Cloud Run health check:
   ```bash
   curl -X GET https://YOUR_CLOUD_RUN_URL/health
   ```
2. Confirm returned JSON:
   ```json
   {
     "status": "healthy",
     "service": "CommunityOS API",
     "environment": "production",
     "gemini_configured": true
   }
   ```
3. Open your frontend web application and test the end-to-end incident lifecycle.
