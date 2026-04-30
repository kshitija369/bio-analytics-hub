# System Instructions: Longevity OS UI Generation

You are generating frontend code for an "Existential Simulator" (Longevity OS). This is NOT a standard B2B SaaS dashboard. It is a proactive, calm, agentic interface based on biological metrics (HRV, Sleep, Glucose).

## Tech Stack
* Backend: FastAPI (Python)
* Frontend: HTML5, HTMX (for reactivity), TailwindCSS (for styling).
* Visualizations: Plotly.js (only when explicitly requested for "X-Ray" views).

## Mandatory UI/UX Rules
1.  **Zero-Friction Default:** Do not generate dense tables or grids of data as the default view. The default view must be conversational or a single, highly readable "Next Action" card.
2.  **Calm Color Palette:** Use dark modes with muted, organic colors (slate, zinc, deep forest greens, soft ambers). Avoid aggressive primary colors (pure red, pure blue) unless indicating a critical biological threshold.
3.  **Provenance Overlays:** Every time you generate an agent recommendation (e.g., "You should take a walk"), you MUST include an HTMX-powered `<button>` labeled "View Rationale" or "X-Ray". When clicked, this should expand to show the underlying biometric data (e.g., "HRV dropped 15% + Glucose spike at 21:00").
4.  **Actionable Sandboxes:** When generating a visualization, include interactive inputs (sliders, toggles) that trigger HTMX `hx-post` requests to the `/simulate` endpoint, dynamically swapping the chart to show predicted future states.

## Component Patterns
* **Use Skeletal Loading:** When fetching LLM responses or running biological simulations, use Tailwind pulse animations to indicate "Agent is thinking..."
* **Typography:** Use serif fonts for philosophical/existential agent responses (representing the "Buddha") and monospace fonts for raw data, FHIR logs, and biological metrics (representing the "Zorba").
