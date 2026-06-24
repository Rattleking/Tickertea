import type { SignalCategorySlug } from "@tickertea/contracts";

/**
 * UI labels + scan-dots for the signal categories. These mirror the closed
 * `SignalCategorySlug` enum in the contracts package, so they are a presentation
 * constant — not data and not a backend call. (A future GET /api/v1/categories
 * can replace this without touching the components.)
 */
export const CATEGORY_LABELS: Record<SignalCategorySlug, string> = {
  mean_reversion: "Mean Reversion",
  hiring_spike: "Hiring Spike",
  management_change: "Management Change",
  capex_expansion: "Capex Expansion",
  subsidiary_creation: "Subsidiary Creation",
  narrative_shift: "Narrative Shift",
  news_event: "News Event",
  insider_activity: "Insider Activity",
  institutional_flow: "Institutional Flow",
};

export const CATEGORY_ORDER: SignalCategorySlug[] = [
  "hiring_spike",
  "management_change",
  "capex_expansion",
  "subsidiary_creation",
  "institutional_flow",
  "insider_activity",
  "narrative_shift",
  "mean_reversion",
  "news_event",
];

export const CATEGORY_DOT: Record<SignalCategorySlug, string> = {
  hiring_spike: "#56C6C2",
  management_change: "#F4B740",
  institutional_flow: "#56C6C2",
  insider_activity: "#E08C6D",
  narrative_shift: "#B79CFF",
  capex_expansion: "#8FA3A0",
  subsidiary_creation: "#8FA3A0",
  mean_reversion: "#8FA3A0",
  news_event: "#8FA3A0",
};
