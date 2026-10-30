"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/rfqs/new", label: "New RFQ" },
  { href: "/sourcing-runs", label: "Sourcing Runs" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/evaluations", label: "Evaluations" },
];

export function Nav() {
  const path = usePathname();

  return (
    <nav aria-label="Main navigation" className="flex flex-col gap-1 p-4">
      <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-zinc-400">
        SourcingIQ
      </p>
      {NAV_ITEMS.map((item) => {
        const active =
          item.href === "/"
            ? path === "/"
            : path === item.href || path.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 ${
              active
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
