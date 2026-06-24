import { z } from "zod";
import { UuidSchema } from "./common.js";

/** The closed-by-data set of signal category slugs in v1. */
export const SignalCategorySlugSchema = z.enum([
  "mean_reversion",
  "hiring_spike",
  "management_change",
  "capex_expansion",
  "subsidiary_creation",
  "narrative_shift",
  "news_event",
  "insider_activity",
  "institutional_flow",
]);
export type SignalCategorySlug = z.infer<typeof SignalCategorySlugSchema>;

export const SignalCategorySchema = z.object({
  id: UuidSchema,
  slug: SignalCategorySlugSchema,
  name: z.string(),
  description: z.string().nullable(),
  is_active: z.boolean(),
});
export type SignalCategory = z.infer<typeof SignalCategorySchema>;
