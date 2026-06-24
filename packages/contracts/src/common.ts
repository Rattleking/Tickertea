import { z } from "zod";

/** Shared primitives used across all Tickertea API contracts. */

export const UuidSchema = z.string().uuid();
export const TimestampSchema = z.string().datetime({ offset: true });

/** A score component or composite: a descriptive intensity in [0,1] — NOT an expected return. */
export const ScoreUnitSchema = z.number().min(0).max(1);

/** Cursor pagination query params. */
export const PaginationQuerySchema = z.object({
  cursor: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(100).default(25),
});
export type PaginationQuery = z.infer<typeof PaginationQuerySchema>;

/** Standard list envelope. */
export function listEnvelope<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    data: z.array(item),
    next_cursor: z.string().nullable(),
  });
}

/** Standard error envelope. */
export const ErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});
export type ApiError = z.infer<typeof ErrorSchema>;

/** Mandatory disclaimer carried on every signal-bearing payload (compliance guardrail). */
export const DISCLAIMER =
  "Tickertea surfaces signals, not investment advice. You decide what to do.";
