import { z } from "zod";
import { UuidSchema, TimestampSchema } from "./common.js";

export const WatchlistSchema = z.object({
  id: UuidSchema,
  name: z.string(),
  item_count: z.number().int().nonnegative(),
  created_at: TimestampSchema,
});
export type Watchlist = z.infer<typeof WatchlistSchema>;

export const CreateWatchlistSchema = z.object({
  name: z.string().min(1).max(120),
});

export const AddWatchlistItemSchema = z.object({
  company_id: UuidSchema,
});

export const AlertSchema = z.object({
  id: UuidSchema,
  category_slug: z.string().nullable(),
  watchlist_id: UuidSchema.nullable(),
  company_id: UuidSchema.nullable(),
  min_composite: z.number().min(0).max(1),
  channel: z.enum(["in_app", "email", "webhook"]),
  is_active: z.boolean(),
});
export type Alert = z.infer<typeof AlertSchema>;

export const CreateAlertSchema = z.object({
  category_slug: z.string().optional(),
  watchlist_id: UuidSchema.optional(),
  company_id: UuidSchema.optional(),
  min_composite: z.number().min(0).max(1).default(0.5),
  channel: z.enum(["in_app", "email", "webhook"]).default("in_app"),
});
