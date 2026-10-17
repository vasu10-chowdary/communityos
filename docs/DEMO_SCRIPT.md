# CommunityOS — Evaluator Video Demonstration Script (3m 30s)

**Target Duration**: 3 minutes, 30 seconds  
**Presenter**: Software Architect & Lead Engineer  
**Objective**: Demonstrate the end-to-end incident lifecycle using Firebase, Cloud Firestore, Cloud Run, and Google Gemini Gen AI.

---

### [0:00 - 0:30] Introduction & Architecture Overview
- **Visual**: Show CommunityOS Landing Page (`/`), displaying the civic interface, role indicators, and tech badges.
- **Narrator**:
  > *"Welcome to CommunityOS — an AI-powered community emergency intelligence and resource coordination platform built for the H2S Challenge. During urban disruptions such as severe storms, water shortages, or fallen obstructions, rapid communication and objective prioritization are critical. CommunityOS brings together four foundational cloud technologies: Firebase Authentication for frictionless evaluator sign-in, Cloud Firestore for real-time state and atomic resource allocation, containerized FastAPI on Google Cloud Run, and Google Gemini Gen AI for multimodal risk triage."*

---

### [0:30 - 1:00] Multimodal Field Intake (Citizen Persona)
- **Visual**: In the top navbar persona switcher, select **Citizen (Report & Track)**. Click **Report Hazard** (`/report`).
- **Action**: Click the shortcut **Load Evaluator Waterlogging Demo**.
  - Title: *"Torrential Rain Inundating 4th Street Culvert"*
  - Category: *"Flooding and waterlogging"*
  - Description: *"High water level covering the asphalt road by ~18 inches. Storm drain intake is choked with branches and plastic refuse."*
  - Attached Photo: Upload evidence photograph showing culvert blockage.
  - Location: *"418 North Oak Ave, Ward 4"*, with exact coordinates.
  - Click **Publish Incident**.
- **Narrator**:
  > *"As a citizen, we submit a multimodal report with text description, precise coordinates, and an on-site photo. The backend validates the image format (JPEG/PNG/WebP under 5MB) and securely logs the report to Firestore under the citizen's authenticated UID."*

---

### [1:00 - 1:45] Server-Side Gemini Multimodal Risk Triage
- **Visual**: Switch navbar persona to **Coordinator (Full Dispatch)**. Navigate to the incident detail view (`/incident/[id]`).
- **Action**: Click **Analyze with Gemini**.
- **Narrator**:
  > *"As incident coordinator, we trigger Gemini analysis. Our Google Cloud Run FastAPI backend initiates structured inference using the official Google Gen AI SDK (`google-genai`) with Gemini 2.5 Flash, passing both the image bytes and report details."*
- **Visual**: Assessment panel updates with structured results:
  - Severity Level: **Level 4 / 5 (High)**
  - Urgency Heuristic: **88 / 100**
  - Visual Evidence Extracted: *Submerged curb line, turbid muddy runoff, tree limb obstruction around intake.*
  - Cascading Risks: *Basement flooding in adjacent low-lying homes, electrical ground conduit exposure.*
  - Recommended Actions: *Deploy vacuum pump trailer, establish street barricades, clear intake grate.*
- **Narrator**:
  > *"Notice how Gemini returns validated structured JSON: a calibrated 1-to-5 severity level, explicit visual cues detected in the photo, cascading hazards, and tactical next steps. Importantly, Gemini does not hallucinate GPS coordinates from the photo alone, relying on verified landmark data."*

---

### [1:45 - 2:20] Duplicate Incident Review
- **Visual**: Scroll to **Duplicate Incident Detection** panel. Click **Scan for Near Duplicates**.
- **Action**: The system displays a matching report:
  - Match: *"Severe Stormwater Backflow on North Oak Ave"* (Confidence: 60%, 15m away, same category).
  - Coordinator clicks **Link as Duplicate**.
- **Narrator**:
  > *"CommunityOS protects dispatch teams from redundant deployments. Our backend computes Haversine geographic proximity and token similarity. When a near duplicate is detected, the coordinator reviews the match and links the reports together, preserving both original citizen narratives in the audit history."*

---

### [2:20 - 2:50] Concurrency-Safe Resource Matching & Dispatch
- **Visual**: Scroll to **Resource Matching & Dispatch Approval**.
- **Action**: View ranked recommendation: *"Municipal Drainage & High-Flow Vacuum Unit"* (Suitability: 0.99, specialized pump capability, available). Coordinator clicks **Approve & Dispatch**.
- **Narrator**:
  > *"Next, our resource matching engine recommends available units ranked by equipment capability and travel proximity. The coordinator approves the dispatch. This triggers an atomic Firestore transaction: if another coordinator attempted to dispatch the same pump simultaneously, the transaction prevents double-booking and rejects conflicting assignments with HTTP 409."*

---

### [2:50 - 3:15] Field Responder Progress & Incident Resolution
- **Visual**: Switch navbar persona to **Responder (Field Team)**.
- **Action**: In the **Responder Field Progress Log**, enter: *"Vacuum pump deployed; culvert intake cleared and water receded 10 inches."* Click **Log Note** and click **Mark In Progress**.
- **Visual**: Switch back to **Coordinator**, verify the responder's note, and click **Approve Resolution**.
- **Narrator**:
  > *"The field team updates progress notes and sets status to In Progress. Once the hazard is resolved, the coordinator approves the resolution. This immediately updates the public command deck and releases the vacuum pump unit back to the Available pool."*

---

### [3:15 - 3:30] Real-Time Transparency & Conclusion
- **Visual**: Return to the **Incident Map** (`/map`) or **Operations Dashboard** (`/dashboard`). Point out the green 'Resolved' indicator and updated ready units count.
- **Narrator**:
  > *"Back on the Operations Command Deck, all status metrics and maps update reactively via Firestore real-time listeners. CommunityOS provides a hardened, transparent, and concurrency-safe civic response system powered by Google Cloud. Thank you."*
