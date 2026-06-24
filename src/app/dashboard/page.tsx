import { Suspense } from "react";
import type { Signal, SignalCategorySlug } from "@tickertea/contracts";
import { fetchSignalFeed, type SignalFeedFilters } from "@/lib/api/signals";
import { FALLBACK_SIGNALS } from "@/lib/fallback-signals";
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
  if (category && category in CATEGORY_LABELS) filters.category = category as SignalCategorySlug;

  const dir = typeof sp.direction === "string" ? sp.direction : undefined;
  if (dir && DIRECTIONS.has(dir)) filters.direction = dir as SignalFeedFilters["direction"];

  const min = typeof sp.min_composite === "string" ? Number(sp.min_composite) : NaN;
  if (Number.isFinite(min) && min > 0) filters.min_composite = Math.min(Math.max(min, 0), 1);

  return filters;
}

/** Apply the same filters client-side to fallback samples so the UI behaves consistently. */
function filterFallback(signals: Signal[], f: SignalFeedFilters): Signal[] {
  return signals.filter(
    (s) =>
      (!f.category || s.category?.slug === f.category) &&
      (!f.direction || s.direction === f.direction) &&
      (f.min_composite === undefined || (s.score?.composite ?? 0) >= f.min_composite),
  );
}

type Banner = { tone: "warn"; text: string };

export default async function DashboardPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const filters = parseFilters(sp);
  const result = await fetchSignalFeed(filters);

  let signals: Signal[];
  let banner: Banner | null = null;

  if (result.ok) {
    signals = result.data;
  } else {
    // API failed — keep the dashboard usable with clearly-labelled sample data.
    signals = filterFallback(FALLBACK_SIGNALS, filters);
    banner = {
      tone: "warn",
      text:
        result.status === 401
          ? "Live feed needs an authenticated session — showing sample signals."
          : `Live feed unavailable (${result.status || "network"}) — showing sample signals.`,
    };
  }

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
              {signals.length} signal{signals.length === 1 ? "" : "s"}
            </span>
            <span className={styles.feedSort}>{banner ? "sample data" : "live"}</span>
          </div>

          {banner ? (
            <div className={styles.banner} role="status">
              {banner.text}
            </div>
          ) : null}

          {signals.length === 0 ? (
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
