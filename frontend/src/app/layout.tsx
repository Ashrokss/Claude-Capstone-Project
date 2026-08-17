import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

// Self-hosted by next/font at build time, so no request leaves the page for a
// stylesheet and there is no flash of unstyled text.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VeriClaim AI — Motor Claim Verification",
  description:
    "Submit a motor insurance claim and track its progress, with AI-assisted assessment reviewed by a human adjuster.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // The font classes sit on <html>, not <body>: globals.css maps them onto
    // --font-sans/-display/-mono at :root, and a custom property can only
    // reference another that is declared on the same element.
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${plexMono.variable}`}
    >
      <body className="antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-[9px] focus:bg-[#0d141c] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
        >
          Skip to content
        </a>
        <AppShell>
          <div id="main">{children}</div>
        </AppShell>
      </body>
    </html>
  );
}
