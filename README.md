# Bio-Analytics Hub: Your Personal Digital Health Laboratory

The **Bio-Analytics Hub** is an advanced **personal health monitoring platform** designed for individuals seeking a high-precision, data-driven approach to longevity and performance. By unifying disparate biometric streams from wearables like the **Oura Ring** and **Apple Watch**, the hub transforms raw physiological data into actionable, research-grade insights.

## 🌟 Overview

Built for **longevity enthusiasts**, **biohackers**, and **performance athletes**, this platform empowers users to become the principal investigators of their own health. It moves beyond simple "activity tracking" to formal **Inference-Driven Research**, allowing you to quantify how specific lifestyle interventions or recovery protocols actually impact your autonomic nervous system.

### Why "Hardware-Agnostic"?
The system is **Provider-Agnostic**—meaning it works independently of any single hardware ecosystem. Whether you upgrade your watch or switch to a new biometric ring, your historical research data and Z-score baselines remain intact, protecting your long-term health narrative from proprietary "data silos."

## 🏗 System Architecture
...

The platform follows **Clean Architecture** principles to ensure provider-agnosticism and research integrity.

```mermaid
graph TD
    subgraph Data_Sources [Data Sources]
        A[Apple Watch] -->|Webhook| B[Biometric API]
        O[Oura Ring] -->|Pull| B
    end

    subgraph Core_Engine [Research Engine]
        B -->|Normalize| D[Domain Layer]
        D -->|Agnostic Dimensions| E[Inference Engine]
        E -->|Z-Score / Correlation| F[(Bio Analytics Hub)]
    end

    subgraph Visualization [Analytics]
        F --> G[Research Hub UI]
        G --> H[Interactive Plotly Dashboards]
        end
        ```

        ## 🛣 User Journeys

        ### 1. Real-time Performance Prompt (Agentic Nudge)
        When physiological stress is detected, the system uses **LLM-powered reasoning** to provide explainable "Care Nudges."

        ```mermaid
        sequenceDiagram
        participant W as Apple Watch
        participant API as Biometric API
        participant E as Agentic Hub
        participant LLM as Gemini (MSDT Context)

        W->>API: 1-min HR data
        API->>E: Evaluate Context
        E->>LLM: Pass recent FHIR Observations
        LLM-->>E: Generate explainable Nudge
        E-->>W: Haptic: "Elevated HR. Try a physiological sigh."
        ```

        ### 2. Prospective Physiological Simulation
        The "Predictive Sandbox" allows users to forecast how upcoming events will impact their recovery.

        ```mermaid
        graph LR
        A[User adds 'Late Meal' event] --> B[POST /simulate]
        B --> C[Vertex AI Bayesian Filter]
        C --> D[Generate Synthetic Day]
        D --> E[Stitch with History]
        E --> F[View 48h Predicted Trajectory on Dashboard]
        ```

        ### 3. Historical Research Backfill
        Establishing a robust physiological baseline for new users.

        ```mermaid
        graph TD
        A[Install System] --> B[Set OURA_PAT]
        B --> C[Run bulk_load_oura.py 90]
        C --> D[FHIR Observation Normalization]
        D --> E[Stream to GCP Healthcare API]
        E --> F[Provenance Log created in BigQuery]
        ```

        ## ✅ Validation Instructions

        To verify the **DT4H-Sim** architecture is functioning correctly in your environment, follow these steps:

        ### 1. Verify Clinical Ingestion (Phase 1)
        Check your logs after a sync. You should see:
        `--- [DT4H-Sim] Constructing X FHIR Observations ---`
        This confirms that raw data is being successfully mapped to **LOINC** standards.

        ### 2. Test the Predictive Sandbox (Phase 2)
        Run the following curl command to generate a synthetic trajectory:
        ```bash
        curl -X POST "https://[YOUR-URL]/api/v1/experiments/EXP-NAR-001/simulate" \
         -H "Content-Type: application/json" \
         -d '{"events": [{"event": "meal", "time": "22:00"}]}'
        ```
        **Expected:** A JSON response containing a 24-hour `prediction` array.

        ### 3. Trigger an Agentic Nudge (Phase 3)
        Send a high-stress heart rate value (e.g., 160 BPM) via the webhook:
        ```bash
        curl -X POST "https://[YOUR-URL]/webhook/biometric-log" \
         -H "Content-Type: application/json" \
         -d '{"data": {"metrics": [{"name": "heart_rate", "data": [{"date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "qty": 160.0}]}]}}'
        ```
        **Expected:** A Pushover notification titled **"AI Performance Nudge"** instead of the standard "Recovery Prompt."

        ## 📊 Visual Gallery
Explore the platform's analytical interfaces. 

### 1. Main Biometric Dashboard
High-resolution monitoring of Heart Rate, HRV, and State Decryption.
![Main Dashboard](docs/images/main_dashboard.png)

### 2. Agnostic Biometric Research Hub
The central registry for managing and tracking physiological research protocols.
![Research Hub](docs/images/research_hub.png)

### 3. NAR Study Laboratory (EXP-NAR-001)
Deep-dive inference showing overnight recovery trends vs. morning readiness.
![NAR Study Result](docs/images/study_detail.png)

## 🧬 Core Logic: The NAR Study

The flagship **Nocturnal Autonomic Research (NAR)** study (`EXP-NAR-001`) analyzes the relationship between high-resolution nocturnal data and daily readiness.

### Key Research Metrics
*   **Baseline Delta (Z)**: Measures deviations from your personal 21-day physiological baseline using Z-Score normalization ($Z = \frac{x - \mu}{\sigma}$).
*   **Sleep Efficiency (Dip)**: Analyzes the "Hammock Curve" of your heart rate. Dips occurring after 03:00 AM indicate autonomic misalignment and are automatically flagged.

## 🛠 Operation Guide

### 1. Hydration & Sync
To establish a statistically sound baseline, hydrate the system with historical data:
```bash
export OURA_PAT="your_token"
python3 scripts/bulk_load_oura.py 90
```

### 2. One-Click Refresh
The platform features a built-in refresh mechanism. Clicking **"Sync & Refresh"** on any dashboard will:
1.  Trigger a delta-sync from all providers.
2.  Recalculate study results for the last 72 hours.
3.  Update all interactive charts.

## 📚 Interactive Laboratory
The system is fully documented via OpenAPI. Access these endpoints directly on your deployed instance:
*   **Interactive API Docs**: `/docs`
*   **Technical Reference**: `/redoc`

---
*Designed for precise measurement of Peak Autonomic Recovery and Performance States.*
