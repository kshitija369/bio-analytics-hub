# Agnostic Biometric Research Platform

A professional, provider-independent system designed for high-resolution physiological research. This platform anchors itself in established longevity frameworks (Attia, Walker, Panda) to quantify the realities of autonomic recovery.

## 🏗 System Architecture

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
