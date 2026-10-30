import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { Suspense } from "react";
import "./globals.css";
import { Nav } from "@/components/Nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SourcingIQ",
  description: "AI-assisted procurement workflow for steel sourcing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full bg-white dark:bg-zinc-950">
        <aside className="hidden w-56 shrink-0 border-r border-zinc-200 dark:border-zinc-800 lg:flex lg:flex-col">
          <Suspense fallback={<div className="p-4 text-xs text-zinc-400">Loading…</div>}>
            <Nav />
          </Suspense>
        </aside>
        <div className="flex flex-1 flex-col min-w-0">
          {/* Mobile nav bar */}
          <header className="flex items-center gap-4 border-b border-zinc-200 px-4 py-3 lg:hidden dark:border-zinc-800">
            <span className="text-sm font-semibold">SourcingIQ</span>
            <nav className="flex gap-2 overflow-x-auto" aria-label="Main navigation">
              <Link href="/" className="shrink-0 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400">Overview</Link>
              <Link href="/rfqs/new" className="shrink-0 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400">New RFQ</Link>
              <Link href="/sourcing-runs" className="shrink-0 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400">Runs</Link>
              <Link href="/suppliers" className="shrink-0 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400">Suppliers</Link>
              <Link href="/evaluations" className="shrink-0 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400">Evaluations</Link>
            </nav>
          </header>
          <main className="flex-1 px-6 py-8 max-w-5xl mx-auto w-full">{children}</main>
        </div>
      </body>
    </html>
  );
}
