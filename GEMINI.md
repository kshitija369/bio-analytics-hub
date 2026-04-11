# Witness State Monitoring: System Mandates

Always refer to this file before writing code. It contains the project's foundational architecture, hard-won lessons from authentication/parsing bugs, and deployment constraints.

---

## 🏗️ Core Architecture: The Modular Data Pipeline
- **Provider Pattern:** All biometric sources (Oura, Apple Health) MUST implement the `BiometricProvider` interface in `app/providers/base.py`.
- **Atomic Normalization:** All raw data MUST be normalized to a 1-minute frequency UTC timeline in `app/core/normalization.py`.
- **High-Contrast Decryption:** Visualizations MUST prioritize "State Decryption." Use the 3-row subplot layout (Key, HR, HRV) with dynamic line coloring (Purple/Green for active practice).

---

## 🔒 Authentication Mandates (Hard-Won Fixes)
- **URL Purity:** Oura V2 is strict. NEVER use trailing slashes in usercollection URLs (e.g., use `.../heartrate`, NOT `.../heartrate/`).
- **PAT Sanitization:** Always `.strip()` the `OURA_PAT` environment variable. Hidden newlines or spaces in secrets will cause `400 "No access token header found"` errors.
- **Header Enforcement:** Explicitly pass a fresh header dictionary into every `requests` call. Do not rely solely on `Session.headers.update` for critical auth headers in Cloud Run environments.

---

## 💾 Persistence & Cloud Strategy (GCP)
- **Two-Tier DB Strategy:** 
    1. **Working Tier:** R/W to a local SQLite file in `/tmp/Somatic_Log_Working.sqlite` for speed and to avoid FUSE locking hangs.
    2. **Persistent Tier:** Periodically `shutil.copy2` the working DB to the persistent mount at `/app/data/Somatic_Log.sqlite`.
- **FUSE Safety:** Never allow SQLite to open a journal or lock file directly on the GCS FUSE mount. It will cause indefinite hangs and "database is locked" errors.
- **Timezone Fallback:** Use `pytz` for container stability. Hardcode `America/Los_Angeles` as the primary zone, but ALWAYS provide a fallback to `UTC` to prevent startup crashes.

---

## 📊 Data Parsing & Metric Mapping
- **Apple Health (HAE):** 
    - Support both `qty` and `avg` keys. 
    - Map `heart_rate_variability_sdnn` to the unified `heart_rate_variability` column.
    - Map `sleep_analysis` to `sleep_score` for unified Bio-Load analysis.
- **Oura V2:**
    - **Heart Rate:** Fetch from `/heartrate` (High-res).
    - **HRV:** Fetch from `/sleep` session data (`hrv.items` array).
    - **Fallback:** Use `contributors.hrv_balance` if high-res items are missing.

---

## 🧪 Testing & Validation Mandates
- **MANDATORY:** Integration tests MUST be updated to cover any new logic or endpoints before code is committed.
- **Pre-Push Requirement:** All test suites MUST pass locally before any commit:
    1. `tests/test_endpoints.py` (API & Logic Flow)
    2. `tests/test_parsing.py` (JSON Schema Integrity)
    3. `tests/test_auth.py` (Header & Token Integrity)
- **CI/CD Integration:** Automated tests MUST run in the GitHub Actions workflow. Any failure MUST abort the deployment to Cloud Run.

---

## 🚀 Deployment Verification
Before finalizing a cloud sync issue, verify these status endpoints:
1. `/health`: Basic API check.
2. `/db-status`: Integrity check (size, path, record counts).
3. `/test-oura`: Live API handshake check (headers, payload snippets).

---

**System Goal:** To transform passive biometric tracking into an active, closed-loop feedback system for monitoring the physiological reality of non-dual awareness.
