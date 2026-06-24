import { DISCLAIMER, type Signal } from "@tickertea/contracts";

/**
 * Fallback sample signals — rendered ONLY when the live /api/v1/signals fetch fails
 * (network error, 401, 5xx), so the dashboard stays usable instead of showing a dead 500.
 * These are clearly-labelled samples in the UI; they never replace a successful live fetch.
 */
export const FALLBACK_SIGNALS: Signal[] = [
  {
    id: "sample-1",
    company: { id: "sample-infy", name: "Infosys", nse_symbol: "INFY" },
    category: { slug: "hiring_spike", name: "Hiring Spike" },
    title: "Open engineering roles up 3.2σ vs trailing 90-day mean",
    summary:
      "Engineering job postings rose to 412, about 3.2 standard deviations above the trailing 90-day average of 180. Observation only.",
    direction: "up",
    status: "published",
    observed_at: "2026-06-20T06:30:00.000Z",
    score: { magnitude: 0.88, confidence: 0.7, novelty: 0.64, composite: 0.76, model_version: "score-1.0.0" },
    evidence_count: 1,
    disclaimer: DISCLAIMER,
  },
  {
    id: "sample-2",
    company: { id: "sample-ril", name: "Reliance Industries", nse_symbol: "RELIANCE" },
    category: { slug: "management_change", name: "Management Change" },
    title: "New Chief Technology Officer appointed (KMP)",
    summary:
      "Appointment of a new CTO disclosed via an NSE board-meeting announcement. Key managerial personnel change.",
    direction: "neutral",
    status: "published",
    observed_at: "2026-06-21T11:05:00.000Z",
    score: { magnitude: 0.6, confidence: 0.9, novelty: 0.7, composite: 0.72, model_version: "score-1.0.0" },
    evidence_count: 1,
    disclaimer: DISCLAIMER,
  },
  {
    id: "sample-3",
    company: { id: "sample-lt", name: "Larsen & Toubro", nse_symbol: "LT" },
    category: { slug: "capex_expansion", name: "Capex Expansion" },
    title: "Capex guidance raised alongside new fabrication facility",
    summary: "Management guided to higher FY capex and disclosed a new heavy-fabrication facility. Observation only.",
    direction: "up",
    status: "published",
    observed_at: "2026-06-19T09:00:00.000Z",
    score: { magnitude: 0.74, confidence: 0.66, novelty: 0.71, composite: 0.69, model_version: "score-1.0.0" },
    evidence_count: 1,
    disclaimer: DISCLAIMER,
  },
];
