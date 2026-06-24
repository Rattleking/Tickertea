"use client";

import { useEffect } from "react";
import styles from "./dashboard.module.css";

/**
 * Route-level error boundary. Catches any unexpected render/runtime error in /dashboard
 * so the user sees a recoverable panel with a retry, never a raw 500.
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface for server logs / observability.
    console.error("dashboard render error:", error);
  }, [error]);

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.wordmark}>
          <span className={styles.glyph}>◵</span> TICKERTEA
        </div>
      </header>
      <div className={styles.feedWrap}>
        <div className={styles.panel} role="alert">
          <strong>Something went wrong rendering the dashboard.</strong>
          <p className={styles.panelHint}>The feed couldn&apos;t be displayed. Try again.</p>
          <p style={{ marginTop: "1rem" }}>
            <button type="button" onClick={reset} className={styles.retry}>
              Retry
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
