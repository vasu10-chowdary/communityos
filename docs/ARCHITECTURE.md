# CommunityOS Architecture & System Design

## 1. Overview
CommunityOS is a full-stack, AI-powered civic emergency intelligence and resource coordination platform designed for rapid response during municipal disruptions, weather emergencies, water shortages, fallen obstructions, and localized hazards.

## 2. Mandatory Tech Stack Integration

```
+---------------------------------------------------------------------------------+
|                                 CLIENT TIER                                     |
|  Next.js 15 (App Router) + TypeScript + Tailwind CSS + Lucide + OpenStreetMap  |
|  - Firebase Anonymous Authentication & Evaluator Access                         |
|  - Real-time Firestore Subscriptions & Reactive Operations Dashboard            |
+----------------------------------------+----------------------------------------+
                                         |
                       POST /api/incidents/analyze
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                                BACKEND TIER                                     |
|  FastAPI + Pydantic + Uvicorn Containerized on Google Cloud Run                 |
|  - Input Validation & Schema Enforcement                                        |
|  - Secret-safe environment handling                                             |
|  - Official Google Gen AI SDK (`google-genai`)                                  |
+----------------------------------------+----------------------------------------+
                                         |
                         Client SDK / REST / RPC
                                         |
                                         v
+----------------------------------------+----------------------------------------+
|                            AI & CLOUD SERVICES                                  |
|  - Google Gemini 2.5 Flash: Structural Urgency & Risk Reasoning                 |
|  - Cloud Firestore: Incidents, Audit Records, Resources, Atomic Transitions     |
|  - Firebase Auth: Evaluator tokens, anonymous sessions                          |
+---------------------------------------------------------------------------------+
```

### Components:
1. **Frontend**: Next.js App Router, responsive civic palette (Navy, Civic Teal, Amber, Crimson, Emerald), dynamic client routing, and offline seed hydration.
2. **Backend**: FastAPI on Google Cloud Run running Python 3.11/3.14 with strict schema validation.
3. **AI Intelligence**: Google Gen AI SDK (`google-genai`) generating validated JSON with urgency heuristics, potential risks, next steps, and resource recommendations.
4. **Data & Security**: Cloud Firestore with atomic transactions, security rules restricting deletes to demo records, and immutable audit logs.
