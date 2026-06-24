import { z } from "zod";
import { UuidSchema, TimestampSchema, PaginationQuerySchema } from "./common.js";

export const CompanyStatusSchema = z.enum(["active", "suspended", "delisted"]);

export const CompanySchema = z.object({
  id: UuidSchema,
  name: z.string(),
  legal_name: z.string().nullable(),
  cin: z.string().nullable(),
  sector: z.string().nullable(),
  industry: z.string().nullable(),
  status: CompanyStatusSchema,
  in_universe: z.boolean(),
  nse_symbol: z.string().nullable(),
  isin: z.string().nullable(),
  created_at: TimestampSchema,
});
export type Company = z.infer<typeof CompanySchema>;

export const CompanyListQuerySchema = PaginationQuerySchema.extend({
  index: z.string().optional(),          // NIFTY50, NIFTYNEXT50, FNO
  sector: z.string().optional(),
  in_universe: z.coerce.boolean().optional(),
  q: z.string().optional(),              // name search
});
export type CompanyListQuery = z.infer<typeof CompanyListQuerySchema>;
