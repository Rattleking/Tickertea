import { describe, it, expect } from "vitest";
import { SignalSchema, SignalScoreSchema, FORBIDDEN_ADVICE_FIELDS } from "../src/signal.js";

/**
 * Compliance guardrail (contract layer): the public signal/score shapes must never
 * expose recommendation / target-price / expected-return fields. If someone adds one,
 * this test fails. See docs/architecture/08-compliance-guardrails.md.
 */
describe("compliance: no advice fields on signal contracts", () => {
  const signalKeys = Object.keys(SignalSchema.shape);
  const scoreKeys = Object.keys(SignalScoreSchema.shape);
  const allKeys = [...signalKeys, ...scoreKeys];

  for (const forbidden of FORBIDDEN_ADVICE_FIELDS) {
    it(`does not expose a "${forbidden}" field`, () => {
      expect(allKeys).not.toContain(forbidden);
    });
  }

  it("score components are descriptive intensities, not returns", () => {
    expect(scoreKeys.sort()).toEqual(
      ["composite", "confidence", "magnitude", "model_version", "novelty"].sort(),
    );
  });
});
