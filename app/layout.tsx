import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Software Reviews", template: "%s | Software Reviews" },
  description: "Software reviews, pricing and alternatives.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-neutral-900 antialiased">{children}</body>
    </html>
  );
}
