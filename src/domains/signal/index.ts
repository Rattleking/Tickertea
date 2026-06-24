/**
 * Signal domain — public API.
 *
 * Other domains and the app/API layer may import ONLY from this barrel
 * (enforced by .dependency-cruiser.cjs). repository.ts / service.ts internals
 * are private to this domain.
 */
export { getSignalFeed } from "./service.js";
export type { SignalRow } from "./repository.js";
