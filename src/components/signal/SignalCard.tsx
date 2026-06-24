import type { Signal } from "@tickertea/contracts";
import { CATEGORY_DOT } from "@/lib/categories";
import styles from "./SignalCard.module.css";

const DIRECTION_GLYPH: Record<string, string> = {
  up: "↑ up",
  down: "↓ down",
  neutral: "◦ neutral",
};

function clamp01(n: unknown): number {
  const v = typeof n === "number" && Number.isFinite(n) ? n : 0;
  return Math.min(Math.max(v, 0), 1);
}

function isoDate(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? "—" : d.toISOString().slice(0, 10);
}

export function SignalCard({ signal }: { signal: Signal }) {
  // Defensive: tolerate partial payloads so one bad row never crashes the feed.
  const company = signal.company ?? { id: "", name: "Unknown company", nse_symbol: null };
  const category = signal.category ?? { slug: "news_event", name: "Uncategorised" };
  const score = signal.score ?? null;
  const direction = signal.direction ?? "neutral";
  const evidenceCount = typeof signal.evidence_count === "number" ? signal.evidence_count : 0;
  const dot = CATEGORY_DOT[category.slug as keyof typeof CATEGORY_DOT] ?? "var(--muted)";

  return (
    <article className={styles.card}>
      <div className={styles.main}>
        <div className={styles.top}>
          <span className={styles.ticker}>{company.nse_symbol ?? company.name}</span>
          <span className={styles.coname}>{company.name}</span>
          <span className={styles.chip}>
            <span className={styles.cdot} style={{ background: dot }} />
            {category.name}
          </span>
          {/* Direction is intentionally neutral-coloured: it describes the observation, not a trade. */}
          <span className={styles.dir}>{DIRECTION_GLYPH[direction] ?? "◦ neutral"}</span>
        </div>

        <h3 className={styles.title}>{signal.title || "Untitled signal"}</h3>

        <div className={styles.foot}>
          <span>{isoDate(signal.observed_at)}</span>
          <span>
            {evidenceCount} evidence{evidenceCount === 1 ? "" : "s"}
          </span>
          {signal.status ? <span className={styles.status}>{signal.status}</span> : null}
        </div>
      </div>

      <div className={styles.score}>
        <div className={styles.compositeLabel}>composite</div>
        <div className={styles.composite}>{score ? clamp01(score.composite).toFixed(2) : "—"}</div>
        {score ? (
          <div className={styles.meters}>
            <Meter mark="M" value={clamp01(score.magnitude)} />
            <Meter mark="C" value={clamp01(score.confidence)} />
            <Meter mark="N" value={clamp01(score.novelty)} />
          </div>
        ) : null}
      </div>
    </article>
  );
}

function Meter({ mark, value }: { mark: string; value: number }) {
  return (
    <div className={styles.meter}>
      <span className={styles.mk}>{mark}</span>
      <div className={styles.bar}>
        <span style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
    </div>
  );
}
