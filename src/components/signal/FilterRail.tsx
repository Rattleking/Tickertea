"use client";

import { type CSSProperties, useCallback, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { SignalCategorySlug } from "@tickertea/contracts";
import { CATEGORY_LABELS, CATEGORY_ORDER, CATEGORY_DOT } from "@/lib/categories";
import styles from "./FilterRail.module.css";

const DIRECTIONS = [
  { key: "", label: "All" },
  { key: "up", label: "↑ Up" },
  { key: "neutral", label: "◦ Neut" },
  { key: "down", label: "↓ Down" },
] as const;

/**
 * Filter rail. Every control writes to the URL query string; the /dashboard server
 * component reads those params and re-fetches the real /api/v1/signals feed. URL-driven
 * filters are shareable, back-button friendly, and need no client data store.
 */
export function FilterRail() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  const activeCategory = params.get("category") ?? "";
  const activeDirection = params.get("direction") ?? "";
  const minComposite = Number(params.get("min_composite") ?? "0");
  const [sliderValue, setSliderValue] = useState(minComposite);

  const commit = useCallback(
    (mutate: (p: URLSearchParams) => void) => {
      const next = new URLSearchParams(params.toString());
      mutate(next);
      const qs = next.toString();
      startTransition(() => router.push(qs ? `${pathname}?${qs}` : pathname));
    },
    [params, pathname, router],
  );

  const setParam = (key: string, value: string) =>
    commit((p) => (value ? p.set(key, value) : p.delete(key)));

  const toggleCategory = (slug: SignalCategorySlug) =>
    setParam("category", activeCategory === slug ? "" : slug);

  return (
    <aside className={styles.rail} data-pending={pending || undefined}>
      <section className={styles.group}>
        <div className={styles.head}>
          <span className={styles.label}>Min strength</span>
          <span className={styles.readout}>{sliderValue.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={sliderValue}
          aria-label="Minimum composite strength"
          style={{ "--fill": `${sliderValue * 100}%` } as CSSProperties}
          onChange={(e) => setSliderValue(Number(e.target.value))}
          onPointerUp={(e) => setParam("min_composite", String((e.target as HTMLInputElement).value))}
          onKeyUp={(e) => setParam("min_composite", String((e.target as HTMLInputElement).value))}
        />
        <p className={styles.hint}>Composite notability, 0–1</p>
      </section>

      <section className={styles.group}>
        <span className={styles.label}>Category</span>
        <div className={styles.cats}>
          {CATEGORY_ORDER.map((slug) => {
            const active = activeCategory === slug;
            return (
              <button
                key={slug}
                type="button"
                className={styles.cat}
                aria-pressed={active}
                onClick={() => toggleCategory(slug)}
              >
                <span className={styles.catDot} style={{ background: CATEGORY_DOT[slug] }} />
                {CATEGORY_LABELS[slug]}
              </button>
            );
          })}
        </div>
        <p className={styles.hint}>One category at a time (API filter).</p>
      </section>

      <section className={styles.group}>
        <span className={styles.label}>Direction</span>
        <div className={styles.seg} role="group" aria-label="Direction">
          {DIRECTIONS.map((d) => (
            <button
              key={d.key || "all"}
              type="button"
              aria-pressed={activeDirection === d.key}
              onClick={() => setParam("direction", d.key)}
            >
              {d.label}
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
