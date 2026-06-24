import Link from "next/link";

export default function Home() {
  return (
    <main style={{ padding: "2.5rem", maxWidth: 720, lineHeight: 1.5 }}>
      <h1 style={{ marginBottom: 0 }}>Tickertea</h1>
      <p style={{ color: "var(--muted)", marginTop: ".25rem" }}>
        Alternative intelligence platform for public equities.
      </p>
      <p>
        <strong>Tickertea surfaces signals, not investment advice.</strong> You decide what to do.
      </p>
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/dashboard">Open the signal dashboard →</Link>
      </p>
    </main>
  );
}
