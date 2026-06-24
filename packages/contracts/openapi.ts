/**
 * Generates an OpenAPI 3.1 document from the Zod contracts so the spec never drifts
 * from the schemas the API and frontend actually use.
 *
 *   pnpm --filter @tickertea/contracts openapi > openapi.json
 *
 * Uses @asteasolutions/zod-to-openapi. This is the skeleton wiring: register each
 * schema + path here as endpoints are implemented.
 */
import {
  OpenApiGeneratorV31,
  OpenAPIRegistry,
} from "@asteasolutions/zod-to-openapi";
import { SignalSchema, SignalListQuerySchema } from "./src/signal.js";
import { CompanySchema } from "./src/company.js";
import { SignalCategorySchema } from "./src/category.js";
import { DISCLAIMER } from "./src/common.js";

const registry = new OpenAPIRegistry();

registry.register("Signal", SignalSchema);
registry.register("Company", CompanySchema);
registry.register("SignalCategory", SignalCategorySchema);

registry.registerPath({
  method: "get",
  path: "/api/v1/signals",
  summary: "List signals (the core feed). Signals are observations, not advice.",
  request: { query: SignalListQuerySchema },
  responses: {
    200: {
      description: "A page of signals.",
      content: { "application/json": { schema: SignalSchema.array() } },
    },
  },
});

const generator = new OpenApiGeneratorV31(registry.definitions);
const doc = generator.generateDocument({
  openapi: "3.1.0",
  info: {
    title: "Tickertea API",
    version: "0.1.0",
    description: `Alternative intelligence platform for public equities. ${DISCLAIMER}`,
  },
  servers: [{ url: "/" }],
});

// eslint-disable-next-line no-console
console.log(JSON.stringify(doc, null, 2));
