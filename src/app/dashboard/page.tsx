import { Suspense } from "react";
import type { SignalCategorySlug } from "@tickertea/contracts";
import { fetchSignalFeed, type SignalFeedFilters } from "@/lib/api/signals";
import { CATEGORY_LABELS } from "@/lib/categories";
import { FilterRail } from "@/components/signal/FilterRail";
import { SignalCard } from "@/components/signal/SignalCard";
import styles from "./dashboard.module.css";

export const dynamic = "force-dynamic"; // feed is per-request (auth + filters)

type SearchParams = Record<string, string | string[] | undefined>;

const DIRECTIONS = new Set(["up", "down", "neutral"]);

function parseFilters(sp: SearchParams): SignalFeedFilters {
  const filters: SignalFeedFilters = {};

  const category = typeof sp.category === "string" ? sp.category : undefined;
  if (category && category in CATEGORY_LABELS) {
    filters.category = category as SignalCategorySlug;
  }

  const dir = typeof sp.direction === "string" ? sp.direction : undefined;
  if (dir && DIRECTIONS.has(dir)) filters.direction = dir as SignalFeedFilters["direction"];

  const min = typeof sp.min_composite === "string" ? Number(sp.min_composite) : NaN;
  if (Number.isFinite(min) && min > 0) filters.min_composite = Math.min(Math.max(min, 0), 1);

  return filters;
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const filters = parseFilters(sp);

  let feed;
  let error: string | null = null;
  try {
    feed = await fetchSignalFeed(filters);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load signals.";
  }

  const signals = feed?.data ?? [];

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.wordmark}>
          <span className={styles.glyph}>◵</span> TICKERTEA
        </div>
        <div className={styles.stance}>
          <b>Signals, not advice.</b> Every signal traces to source evidence.
        </div>
        <span className={styles.tenant}>
          <span className={styles.dot}>●</span> demo tenant
        </span>
      </header>

      <div className={styles.console}>
        <Suspense fallback={<aside />}>
          <FilterRail />
        </Suspense>

        <main className={styles.feedWrap}>
          <div className={styles.feedHead}>
            <span className={styles.feedTitle}>SIGNAL FEED</span>
            <span className={styles.feedMeta}>
              {error ? "—" : `${signals.length} signal${signals.length === 1 ? "" : "s"}`}
            </span>
            <span className={styles.feedSort}>sorted by recency</span>
          </div>

          {error ? (
            <div className={styles.panel} role="alert">
              <strong>Couldn&apos;t load the feed.</strong>
              <p className={styles.panelMsg}>{error}</p>
              <p className={styles.panelHint}>
                Confirm the dev server is running and the database is reachable.
              </p>
            </div>
          ) : signals.length === 0 ? (
            <div className={styles.panel}>
              <strong>No signals match these filters.</strong>
              <p className={styles.panelHint}>Lower the strength threshold or clear the category.</p>
            </div>
          ) : (
            <div className={styles.feed}>
              {signals.map((s) => (
                <SignalCard key={s.id} signal={s} />
              ))}
            </div>
          )}
        </main>
      </div>

      <footer className={styles.footer}>
        live source: <code>GET /api/v1/signals</code> · Tickertea surfaces signals, not investment advice.
      </footer>
    </div>
  );
}
