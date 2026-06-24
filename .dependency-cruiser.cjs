/**
 * Enforces modular domain design: a domain may only be reached through its public
 * barrel (src/domains/<name>/index.ts). Cross-domain deep imports are forbidden so
 * the seams stay clean for a later service split. See docs/architecture/01.
 */
module.exports = {
  forbidden: [
    {
      name: "no-cross-domain-deep-import",
      comment:
        "Import another domain only via its index.ts barrel, never its internals.",
      severity: "error",
      from: { path: "^src/domains/([^/]+)/" },
      to: {
        path: "^src/domains/([^/]+)/.+",
        pathNot: ["^src/domains/$1/", "^src/domains/[^/]+/index\\.ts$"],
      },
    },
    {
      name: "no-app-to-domain-internals",
      comment: "App/API layer must use domain barrels, not internals.",
      severity: "error",
      from: { path: "^src/app/" },
      to: { path: "^src/domains/[^/]+/(?!index\\.ts).+" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
  },
};
