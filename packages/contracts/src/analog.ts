import { z } from "zod";
import { UuidSchema, TimestampSchema } from "./common.js";
import { SignalCategorySlugSchema } from "./category.js";

/** Seed: either an existing signal, or a company's state as of a date. */
export const AnalogSeedSchema = z.union([
  z.object({ signal_id: UuidSchema }),
  z.object({ company_id: UuidSchema, as_of: TimestampSchema }),
]);

export const AnalogSearchRequestSchema = z.object({
  seed: AnalogSeedSchema,
  filters: z
    .object({
      sector: z.string().optional(),
      index: z.string().optional(),
      category: SignalCategorySlugSchema.optional(),
      date_from: TimestampSchema.optional(),
      date_to: TimestampSchema.optional(),
    })
    .optional(),
  k: z.number().int().min(1).max(50).default(10),
});
export type AnalogSearchRequest = z.infer<typeof AnalogSearchRequestSchema>;

/** A matched PAST situation. Deliberately no outcome/return field (compliance). */
export const AnalogMatchSchema = z.object({
  snapshot_id: UuidSchema,
  company: z.object({ id: UuidSchema, name: z.string(), nse_symbol: z.string().nullable() }),
  as_of: TimestampSchema,
  similarity: z.number().min(0).max(1),
  explanation: z.record(z.string(), z.unknown()), // per-feature contribution, auditable
});
export type AnalogMatch = z.infer<typeof AnalogMatchSchema>;

export const AnalogSearchResponseSchema = z.object({
  query_id: UuidSchema,
  matches: z.array(AnalogMatchSchema),
  disclaimer: z.string(),
});
