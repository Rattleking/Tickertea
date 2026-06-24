import type { Signal } from "@tickertea/contracts";
import { CATEGORY_DOT } from "@/lib/categories";
import styles from "./SignalCard.module.css";

const DIRECTION_GLYPH: Record<Signal["direction"], string> = {
  up: "↑ up",
  down: "↓ down",
  neutral: "◦ neutral",
};

function meterPct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

function isoDate(ts: string): string {
  // Stable, locale-independent date (avoids server/client hydration mismatch).
  return new Date(ts).toISOString().slice(0, 10);
}

export function SignalCard({ signal }: { signal: Signal }) {
  const { company, category, score } = signal;
  const dot = CATEGORY_DOT[category.slug] ?? "var(--muted)";

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
          <span className={styles.dir}>{DIRECTION_GLYPH[signal.direction]}</span>
        </div>

        <h3 className={styles.title}>{signal.title}</h3>

        <div className={styles.foot}>
          <span>{isoDate(signal.observed_at)}</span>
          <span>
            {signal.evidence_count} evidence{signal.evidence_count === 1 ? "" : "s"}
          </span>
          <span className={styles.status}>{signal.status}</span>
        </div>
      </div>

      <div className={styles.score}>
        <div className={styles.compositeLabel}>composite</div>
        <div className={styles.composite}>{score ? score.composite.toFixed(2) : "—"}</div>
        {score ? (
          <div className={styles.meters}>
            <Meter mark="M" value={score.magnitude} />
            <Meter mark="C" value={score.confidence} />
            <Meter mark="N" value={score.novelty} />
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
        <span style={{ width: meterPct(value) }} />
      </div>
    </div>
  );
}
