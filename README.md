# Witness State Monitoring

A modular data pipeline and research tool for monitoring physiological manifestations of non-dual awareness (the "Witness State") using Oura and Apple Health data.

## Architecture
The system follows a **Provider Pattern**, separating data ingestion from normalization and visualization:
- **`app/providers/`**: Pluggable modules for Oura (API-based) and Apple Health (Webhook-based).
- **`app/core/`**: Handles SQLite storage and 1-minute time-series normalization/interpolation.
- **`app/api/`**: FastAPI endpoints for receiving health data.
- **`app/visualization/`**: Interactive Plotly dashboards and "Witness Zoom" physiological analysis.

## Setup & Integration Flow

### 1. Start the Background Listener (Apple Health)
The server receives **push-based** data from your iPhone (via Health Auto Export).
```bash
python3 -m app.main server
```
*   **Endpoint:** `http://<your-ip>:8000/webhook/somatic-log`
*   **Function:** Standardizes and stores Apple Watch HRV, Heart Rate, and Mindful Minutes.

### 2. Run the Processing Pipeline (Oura + Merge)
The pipeline **pulls** data from Oura's Cloud API and merges it with Apple Health data.
```bash
# Default (Last 24 hours)
python3 -m app.main pipeline

# Custom (e.g., Last 7 days / 168 hours)
python3 -m app.main pipeline 168
```
**Actions performed:**
1.  **Polls Oura:** Connects to Oura v2 API.
2.  **Unifies:** Joins Oura metrics with Apple Health data from SQLite.
3.  **Normalizes:** Resamples all sources to a 1-minute frequency.
4.  **Generates:** Updates `unified_somatic_dashboard.html`.

## Visualizing Insights

### The Dual-Stream Timeline
Open `unified_somatic_dashboard.html` to see:
*   **Apple Watch HRV (SDNN):** Green diamonds on the secondary Y-axis.
*   **Oura Heart Rate:** Black baseline line.
*   **Practice Overlays:** Shaded regions or markers indicating "Witnessing" sessions.

### The "Witness Zoom" Analysis
The pipeline terminal output calculates the **HRV % Change**:
*   **Formula:** `((HRV_practice - HRV_baseline) / HRV_baseline) * 100`
*   **Insight:** A positive change (>20%) during practice indicates successful parasympathetic activation while maintaining cognitive awareness.

## Configuration
Set the following environment variables:
*   `OURA_PAT`: Your Oura Personal Access Token.
*   `FETCH_HOURS`: Default lookback period (optional).

## License
MIT
