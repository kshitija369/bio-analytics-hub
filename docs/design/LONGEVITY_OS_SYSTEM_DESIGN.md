# Software Architecture Design Document: Longevity OS (Bio-Analytics Hub)

## 1. Executive Summary
The **Bio-Analytics Hub** has evolved from a retrospective physiological data tracker into **Longevity OS**, a proactive, Multi-Scale Digital Twin (MSDT) platform. The primary objective is to automate biological maintenance and administrative workflow management through a multi-agent orchestrated architecture. By acting as a closed-loop control system, Longevity OS handles high-frequency wearable data, contextual scheduling, and environmental actuation to proactively protect the user’s cognitive bandwidth and focus.

This document outlines the end-to-end software architecture for the platform, detailing how real-time wearable ingestion, Large Language Model (LLM) reasoning, and ambient smart home actuation are structurally unified on the Google Cloud Platform (GCP).

---

## 2. Architectural Principles
1. **Hardware-Agnostic Ingestion:** The domain layer must never rely on proprietary data models. All incoming data streams (Oura, Apple) are normalized into standard timeseries formats (and ultimately FHIR R4).
2. **Neuro-Symbolic Reasoning:** LLM decision-making (Gemini) is bounded by hard-coded biological and scheduling constraints (e.g., circadian rhythms, maximum daily deep-work limits).
3. **Provenance-Aware Explanations (PA-XDT):** Every autonomous action (e.g., declining a meeting, changing the thermostat) must write an immutable audit trail detailing the biometric context and Chain-of-Thought reasoning.
4. **Calm Technology Execution:** The system prefers ambient state changes (e.g., lighting, temperature) over screen-based push notifications to reduce autonomic friction.

---

## 3. High-Level Container Architecture (C4 Model - Level 2)

The system operates on a hybrid event-driven and scheduled batch architecture, deployed primarily on stateless GCP infrastructure.

* **API / Orchestration Gateway (FastAPI):** The central nervous system, handling webhook ingestion, streaming, and UI serving.
* **Adapter Boundary:** Dedicated modules for external I/O (Oura, Apple Health, Home Assistant, Google Calendar).
* **Cognitive Engine:** The AI routing and evaluation suite, containing the Digital Twin Simulator, Constraint Filters, and Multi-Agent Orchestrator.
* **Data Tier:** A tiered persistence model utilizing a high-speed working database, persistent storage, and an immutable ledger.

---

## 4. Detailed Component View (Core Subsystems)

### 4.1 Ingestion & Normalization Layer
Located in `app/adapters/` and `app/core/`, this layer translates raw external state into computational biology.
* **`apple_health.py` & `oura.py`**: Webhook receivers and API pollers. They abstract away the provider-specific payloads.
* **`BiometricNormalizer`**: Translates disparate data into a unified, resampled Pandas timeseries, resolving timezone mismatches and standardizing metric names (e.g., standardizing `heart_rate_variability` across sources).

### 4.2 The Cognitive Engine (The "Brain")
Located in `app/engine/`, this handles probabilistic modeling and agentic reasoning.
* **`agent_orchestrator.py`**: The central Multi-Agent supervisor. It subscribes to anomaly events via Pub/Sub and routes them to Vertex AI to evaluate context (e.g., distinguishing expected post-workout HRV suppression from systemic psychological stress).
* **`simulation_engine.py`**: The DT4H (Digital Twin) predictive sandbox. It uses Bayesian modeling to compute the projected physiological cost of prospective events.
* **`finitude_filter.py`**: The symbolic constraint layer. Enforces hard limits on scheduling (e.g., the 3-4 hour daily deep work capacity) to prevent LLM hallucination of unrealistic productivity goals.
* **`nar_evaluator.py`**: Evaluates the Nocturnal Autonomic Recovery (EXP-NAR-001 study), calculating Z-score deviations and the overnight "Hammock Curve" efficiency.
* **`registry.py`**: The tool registry that binds external capabilities (like Google Calendar API or Home Assistant commands) into Gemini function-calling schemas.

### 4.3 Action & Actuation Layer (The "Hands")
* **`notifiers.py`**: Manages bidirectional communication (WhatsApp, Pushover) for Human-in-the-Loop refusal paths ("Accept, Reject, Snooze").
* **`home_assistant.py`**: Interacts with the local network's IoT devices to enact ambient circadian alignment (e.g., modifying Philips Hue color temperature or Nest thermostat settings based on sleep stages).

### 4.4 Explainability & Memory
* **`provenance.py`**: Enforces the PA-XDT architecture. Before any autonomous state change is executed, this module logs the hashed biometric state, the system prompt, and the AI's intended goal into a JSONL format directed to Google BigQuery.

---

## 5. Data Architecture
The data strategy uses a tiered approach optimized for both high-frequency reads and long-term durability.

1.  **Working Tier (In-Memory / Local Volatile):** For high-speed webhook ingestion without lock contention, a local `/tmp/Bio_Analytics_Hub_Working.sqlite` is utilized.
2.  **Persistent Tier:** A FUSE-mounted directory `/app/data/Bio_Analytics_Hub.sqlite` ensures that Cloud Run instance cycling does not lose operational data. 
3.  *(Target State)* **FHIR Interoperability:** Migration of the `biometrics` table to the GCP Healthcare API as FHIR R4 `Observation` resources.
4.  *(Target State)* **Ledger Tier:** BigQuery tables storing `provenance_logs` for historical XAI dashboarding and model tuning.

---

## 6. End-to-End Workflows

### Workflow A: Proactive Context Nudge (JITAI)
1. **Trigger:** `app.core.alerts` detects an HRV drop >20% below the 7-day rolling baseline. 
2. **Contextualize:** The system publishes an event to Pub/Sub. `agent_orchestrator.py` picks it up, fetches recent timeseries via `BiometricNormalizer`, and queries the user's Google Calendar via `registry.py`.
3. **Reason:** The LLM evaluates the context using Chain-of-Thought (e.g., "High biological load detected + back-to-back deep work sessions scheduled").
4. **Draft:** The agent drafts a calendar restructuring plan, suggesting a 20-minute "Nature Fix" block.
5. **Execute:** `notifiers.py` prompts the user. If accepted, the calendar is modified. `provenance.py` logs the entire transaction to BigQuery.

### Workflow B: The Predictive Sandbox
1. **Input:** User submits a hypothetical intervention via `app/api/experiment_ui.py` (e.g., "Heavy late-night meal at 10 PM").
2. **Simulate:** `simulation_engine.py` applies negative vectors (metabolic load) against the user's `Baseline_HRV` to project the next 24 hours of Autonomic Nervous System state.
3. **Visualize:** `dashboard.py` generates an interactive Plotly chart showing the predicted delayed "Hammock Curve" dip, providing transparent foresight into the cost of the intervention.

---

## 7. Deployment & Infrastructure (GCP)
The application leverages containerized, cloud-native deployment.
* **CI/CD:** Governed by GitHub Actions in `.github/workflows/deploy.yml`.
* **Compute:** Hosted on GCP Cloud Run. Initiated via `gcp_entrypoint.sh` using Gunicorn/Uvicorn to handle concurrent webhooks and API requests. Asynchronous tasks are routed via Cloud Pub/Sub.
* **Dependencies:** Managed in `requirements.txt` (FastAPI, Pandas, Plotly, Vertex AI SDK). Validated via pytest suites (e.g., `test_pipeline.py`, `test_secular_witness_agent.py`).
