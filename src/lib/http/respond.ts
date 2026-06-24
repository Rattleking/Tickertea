import { NextResponse } from "next/server";
import { z } from "zod";
import type { ApiError } from "@tickertea/contracts";

/** JSON success response. */
export function ok<T>(data: T, init?: ResponseInit) {
  return NextResponse.json(data, init);
}

/** JSON error response in the standard envelope. */
export function fail(
  status: number,
  code: string,
  message: string,
  details?: unknown,
) {
  const body: ApiError = { error: { code, message, details } };
  return NextResponse.json(body, { status });
}

/** Validate a query/body with a Zod schema, returning a typed value or a 400 response. */
export function parseOr400<T extends z.ZodTypeAny>(
  schema: T,
  input: unknown,
): { ok: true; value: z.infer<T> } | { ok: false; response: NextResponse } {
  const result = schema.safeParse(input);
  if (result.success) return { ok: true, value: result.data };
  return {
    ok: false,
    response: fail(400, "invalid_request", "Request validation failed", result.error.flatten()),
  };
}

/** Parse URLSearchParams into a plain object for schema validation. */
export function searchParamsToObject(url: string): Record<string, string> {
  return Object.fromEntries(new URL(url).searchParams.entries());
}
