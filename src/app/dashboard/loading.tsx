import styles from "./dashboard.module.css";

/** Route-level loading UI shown while the server component fetches the feed. */
export default function DashboardLoading() {
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
        <aside />
        <main className={styles.feedWrap}>
          <div className={styles.feedHead}>
            <span className={styles.feedTitle}>SIGNAL FEED</span>
            <span className={styles.feedMeta}>loading…</span>
          </div>
          <div className={styles.feed}>
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
          </div>
        </main>
      </div>
    </div>
  );
}
