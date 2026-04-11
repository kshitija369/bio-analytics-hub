# Witness State Monitoring

A modular data pipeline and research tool for monitoring physiological manifestations of non-dual awareness (the "Witness State") using Oura and Apple Health data.

## Architecture
The system follows a **Provider Pattern**, separating data ingestion from normalization and visualization:
- **`app/providers/`**: Pluggable modules for Oura (API-based) and Apple Health (Webhook-based).
- **`app/core/`**: Handles SQLite storage, 1-minute time-series normalization, and local timezone alignment.
- **`app/api/`**: FastAPI endpoints for receiving health data.
- **`app/visualization/`**: High-contrast dark-mode dashboard with master practice key.
- **`app/core/alerts.py`**: Somatic Rules Engine for real-time biometric triggers.

## Setup & Integration

### 1. Cloud Deployment (GCP)
The system is designed to run on **Google Cloud Run** with persistent storage via **Cloud Storage FUSE**.
- **Service:** `witness-monitoring`
- **Region:** `us-central1`
- **Persistence:** Mounts a GCS bucket to `/app/data` to keep `Somatic_Log.sqlite` persistent across deployments.

### 2. Alerts & Apple Watch
Biometric triggers (e.g., HR > 100 BPM) send haptic "Witness Prompts" to your Apple Watch via **Pushover**.
- **Config:** Managed in `config/triggers.yaml`.
- **Secrets:** Requires `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN`.

### 3. Local Dashboard
The dashboard is automatically localized to your system timezone (e.g., **PDT** for Palo Alto).
```bash
# Generate/Refresh locally
python3 -m app.main pipeline 168
```

## Visualizing Insights
Open `unified_somatic_dashboard.html` to see the **High-Contrast State Analyzer**:
- **Row 1:** Master Practice Key (Indigo blocks).
- **Row 2:** Somatic Baseline (BPM) – turns Purple during practice.
- **Row 3:** Recovery Density (HRV) – turns Green during practice.

## License
MIT
 
