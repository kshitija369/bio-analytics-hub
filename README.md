# Witness State Monitoring

A robust, cloud-native somatic research platform for monitoring the physiological signatures of non-dual awareness (the "Witness State"). This system unifies high-resolution data from **Oura** and **Apple Watch** into a single, high-contrast dashboard with real-time biometric alerting.

## 🚀 Key Features
- **Modular Data Pipeline:** Uses the Provider Pattern to cleanly integrate disparate biometric sources.
- **High-Contrast Analyzer:** A dark-mode Plotly dashboard designed for intuitive "State Decryption" (Heart Rate vs. HRV).
- **Somatic Rules Engine:** Real-time alerting via **Pushover** that taps your Apple Watch during stress spikes or recovery dips.
- **Cloud Persistence:** Deployed on **Google Cloud Run** with a "Two-Tier" SQLite strategy for persistent, zero-lock storage on GCS.
- **Automated Sync:** Hourly background pulls from Oura via **Cloud Scheduler**.

---

## 🛠️ System Architecture
- **`app/providers/`**: Data ingestion logic for Oura (API) and Apple Health (Webhook).
- **`app/core/`**: The "Brain" – handles 1-minute normalization, localized time-alignment (PDT), and the Rules Engine.
- **`app/api/`**: FastAPI endpoints for real-time webhooks, automated syncs, and serving the live dashboard.
- **`config/triggers.yaml`**: Configurable biometric thresholds for your haptic alerts.

---

## 🚦 Setup & Deployment

### 1. Environment Secrets
Add the following to your GitHub Secrets or `.env` file:
- `OURA_PAT`: Your Oura Personal Access Token.
- `PUSHOVER_USER_KEY`: Your Pushover User Key.
- `PUSHOVER_API_TOKEN`: Your Pushover Application Token.
- `GCS_BUCKET_NAME`: The GCP bucket for persistent data.
- `GCP_SA_KEY`: Service Account JSON for deployment.

### 2. Apple Watch Integration
1. Install **Health Auto Export** on your iPhone.
2. Set the REST API URL to: `https://[YOUR-CLOUD-URL]/webhook/somatic-log`
3. Any "Mindful Minutes" session on your Watch is automatically tagged as **"Witnessing"** on the dashboard.

### 3. Automated Heartbeat
Set up the hourly Oura pull using the GCloud CLI:
```bash
gcloud scheduler jobs create http hourly-oura-sync \
    --schedule="0 * * * *" \
    --uri="https://[YOUR-CLOUD-URL]/sync" \
    --http-method=GET \
    --location=us-central1
```

---

## 📊 Usage & Visualization

### View the Dashboard
Visit: **`https://[YOUR-CLOUD-URL]/dashboard`**
- **Row 1 (Master Key):** Purple blocks indicate active practice sessions.
- **Row 2 (Somatic Flow):** Heart rate (BPM). Turns vibrant purple during "Witnessing."
- **Row 3 (Recovery Density):** HRV (SDNN). Turns vibrant green during "Witnessing."

### System Status
Check the database integrity and record counts at:
`https://[YOUR-CLOUD-URL]/db-status`

### Manual Sync
Force an immediate Oura data pull:
`https://[YOUR-CLOUD-URL]/sync`

---

## 🧪 Testing & Debugging
The repository includes a suite of verification tools:
- `python3 test_push.py`: Tests the haptic tap on your Apple Watch.
- `python3 -m pytest tests/test_endpoints.py`: Validates all API routes and DB logic.
- `python3 tests/debug_stack.py`: Performs a deep check of credentials and engine logic.

## 📜 License
MIT
