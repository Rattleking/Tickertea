import { z } from "zod";
import {
  UuidSchema,
  TimestampSchema,
  ScoreUnitSchema,
  PaginationQuerySchema,
} from "./common.js";
import { SignalCategorySlugSchema } from "./category.js";

/** Describes the OBSERVATION, never a recommendation. */
export const DirectionSchema = z.enum(["up", "down", "neutral"]);
export const SignalStatusSchema = z.enum([
  "candidate",
  "scored",
  "published",
  "suppressed",
  "expired",
]);

/** Descriptive intensities in [0,1]. NOT expected return, probability of profit, or price target. */
export const SignalScoreSchema = z.object({
  magnitude: ScoreUnitSchema,
  confidence: ScoreUnitSchema,
  novelty: ScoreUnitSchema,
  composite: ScoreUnitSchema,
  model_version: z.string(),
});
export type SignalScore = z.infer<typeof SignalScoreSchema>;

export const SignalCompanyRefSchema = z.object({
  id: UuidSchema,
  name: z.string(),
  nse_symbol: z.string().nullable(),
});

export const SignalSchema = z.object({
  id: UuidSchema,
  company: SignalCompanyRefSchema,
  category: z.object({ slug: SignalCategorySlugSchema, name: z.string() }),
  title: z.string(),
  summary: z.string().nullable(),
  direction: DirectionSchema,
  status: SignalStatusSchema,
  observed_at: TimestampSchema,
  score: SignalScoreSchema.nullable(),
  evidence_count: z.number().int().nonnegative(),
  disclaimer: z.string(),
});
export type Signal = z.infer<typeof SignalSchema>;

/** Evidence chain item: traces a signal back to an immutable source event. */
export const EvidenceSchema = z.object({
  id: UuidSchema,
  evidence_type: z.enum([
    "filing",
    "news",
    "job_posting",
    "price_series",
    "mca_record",
    "holding_disclosure",
    "llm_extraction",
  ]),
  excerpt: z.string().nullable(),
  artifact_uri: z.string().nullable(),
  weight: ScoreUnitSchema,
  source: z.object({
    key: z.string(),
    event_type: z.string(),
    occurred_at: TimestampSchema.nullable(),
    raw_uri: z.string(),
  }),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const SignalListQuerySchema = PaginationQuerySchema.extend({
  company_id: UuidSchema.optional(),
  category: SignalCategorySlugSchema.optional(),
  direction: DirectionSchema.optional(),
  min_composite: z.coerce.number().min(0).max(1).optional(),
  observed_from: TimestampSchema.optional(),
  observed_to: TimestampSchema.optional(),
  status: SignalStatusSchema.default("published"),
});
export type SignalListQuery = z.infer<typeof SignalListQuerySchema>;

// Compile-time guardrail: this list of forbidden field names must NEVER appear on
// a signal/score schema. Referenced by a contracts unit test.
export const FORBIDDEN_ADVICE_FIELDS = [
  "recommendation",
  "rating",
  "target_price",
  "expected_return",
  "action",
  "buy",
  "sell",
] as const;
