/**
 * @tickertea/contracts — the single source of truth for API request/response shapes.
 *
 * API route handlers import these schemas to validate input and serialize output;
 * the frontend imports the inferred TypeScript types. One definition, no drift.
 *
 * Compliance: NONE of these schemas may contain recommendation / target-price /
 * expected-return fields. See FORBIDDEN_ADVICE_FIELDS and docs/architecture/08.
 */
export * from "./common.js";
export * from "./category.js";
export * from "./company.js";
export * from "./signal.js";
export * from "./watchlist.js";
export * from "./analog.js";
