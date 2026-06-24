import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Tickertea",
  description: "Alternative intelligence platform for public equities. Signals, not advice.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
