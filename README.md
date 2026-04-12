# Agnostic Biometric Research Platform

Welcome to the **Agnostic Biometric Research Platform**, a robust, provider-independent system designed to conduct rigorous physiological research based on established longevity frameworks.

By moving beyond simple data collection to **Inference-Driven Research**, this system anchors itself in the methodologies of Attia, Walker, and Panda, helping to quantify the physiological realities of autonomic recovery.

## 🧬 Core Architecture: The Modular Data Pipeline

1. **Clean Provider Adapters (`app/adapters/`):** All biometric sources (Oura, Apple Health) are strictly encapsulated as adapters. The system is provider-agnostic.
2. **Universal Dimensions (`app/domain/`):** Raw data is mapped into universal dimensions (e.g., `Dimension.HRV`, `Dimension.HeartRate`) ensuring experiments run flawlessly regardless of the hardware used.
3. **Inference Engine (`app/engine/`):** Orchestrates the research. Calculates Z-Score Normalization and evaluates statistical significance (e.g., Pearson Correlation) to translate passive tracking into active feedback.

## 🔬 The NAR Study (Nocturnal Autonomic Research)

The flagship study of this platform is **NAR** (`EXP-NARC-001`). It analyzes how high-resolution nocturnal autonomic behaviors correlate with daily aggregate readiness.

### Key Metrics Tracked
* **Z-Score Normalization**: Focuses on deviations from your personal 21-day baseline ($Z = \frac{x - \mu}{\sigma}$).
* **Circadian Dip Alignment**: Identifies the timing of `min(heart_rate)`. Dips occurring after 03:00 AM indicate autonomic misalignment (e.g., sympathetic arousal, late-night digestion) and apply a penalty to the correlation.

## 🛠 System Operations & Hydration

To support longitudinal longevity trends (e.g., viewing 90-day RHR hammock curves), the system utilizes a two-tier **Hydration & Sync Strategy**.

### The Quarter Bulk Read
For a new installation, you must hydrate the system's `Bio_Analytics_Hub` with historical data to establish your Z-Score baselines.
```bash
# Run the bulk loader to pull the last 90 days from Oura
export OURA_PAT="your_personal_access_token"
export PYTHONPATH=$PYTHONPATH:.
python3 scripts/bulk_load_oura.py 90
```

### The Delta Sync
The system handles incremental updates via Cloud Scheduler hitting the `/sync` API or through Webhooks from Apple Health (`/webhook/biometric-log`), seamlessly merging high-res intra-day data with daily aggregates.

## 📚 Interactive Laboratory (API & Documentation)

The entire platform is documented as an Interactive Laboratory via built-in OpenAPI specifications. 
* **Swagger UI**: `/docs` (Test endpoints interactively)
* **Redoc**: `/redoc` (Deep reading)

Endpoints are organized into logical categories:
* **Data Ingestion**: Syncs and Webhooks.
* **Research API**: Dynamic endpoints for fetching correlation statistics and raw time-series data with dynamic zooming (`start_date` / `end_date`).
* **Somatic Dashboard**: High-contrast visual analytics.
* **System Diagnostics**: Database health and API connectivity checks.

---

*Designed for precise measurement of Peak Autonomic Recovery and Performance States.*
