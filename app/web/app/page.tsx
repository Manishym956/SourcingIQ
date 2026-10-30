import Link from "next/link";
import { Suspense } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonList } from "@/components/LoadingSkeleton";
import { api, type SourcingRun, type Rfq, BUYER_TOKEN } from "@/lib/api";

async function fetchRuns(): Promise<SourcingRun[]> {
  try {
    const page = await api<{ items: SourcingRun[] }>("/sourcing-runs?limit=10", {
      token: BUYER_TOKEN,
    });
    return page.items;
  } catch {
    return [];
  }
}

async function fetchRfqs(): Promise<Rfq[]> {
  try {
    const page = await api<{ items: Rfq[] }>("/rfqs?limit=5", { token: BUYER_TOKEN });
    return page.items;
  } catch {
    return [];
  }
}

async function ActiveRuns() {
  const runs = await fetchRuns();
  const active = runs.filter((r) =>
    ["created", "sourcing", "comparing", "negotiating", "awaiting_review"].includes(r.status),
  );
  const exceptions = runs.filter((r) => ["failed", "rejected"].includes(r.status));

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="active-runs-heading">
        <div className="flex items-center justify-between">
          <h2 id="active-runs-heading" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Active sourcing runs
          </h2>
          <Link
            href="/sourcing-runs"
            className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 rounded"
          >
            View all →
          </Link>
        </div>
        {active.length === 0 ? (
          <p className="mt-4 text-sm text-zinc-500">No active runs. <Link href="/rfqs/new" className="underline">Start one →</Link></p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {active.map((run) => (
              <li key={run.id}>
                <Link
                  href={`/sourcing-runs/${run.id}`}
                  className="flex items-center justify-between rounded-lg border border-zinc-200 p-3 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
                >
                  <span className="font-mono text-xs text-zinc-500">{run.id.slice(0, 8)}…</span>
                  <StatusBadge status={run.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {exceptions.length > 0 && (
        <section aria-labelledby="exceptions-heading">
          <h2 id="exceptions-heading" className="text-sm font-semibold text-red-700 dark:text-red-400">
            Exceptions
          </h2>
          <ul className="mt-3 flex flex-col gap-2">
            {exceptions.map((run) => (
              <li key={run.id}>
                <Link
                  href={`/sourcing-runs/${run.id}`}
                  className="flex items-center justify-between rounded-lg border border-red-100 p-3 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-900/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                >
                  <span className="font-mono text-xs text-zinc-500">{run.id.slice(0, 8)}…</span>
                  <StatusBadge status={run.status} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

async function RecentRfqs() {
  const rfqs = await fetchRfqs();
  if (rfqs.length === 0) {
    return (
      <p className="mt-4 text-sm text-zinc-500">
        No RFQs yet. <Link href="/rfqs/new" className="underline">Create one →</Link>
      </p>
    );
  }
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {rfqs.map((rfq) => (
        <li key={rfq.id} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-medium">
                {rfq.material} — {rfq.specification}
              </p>
              <p className="mt-0.5 text-xs text-zinc-500">
                {rfq.quantity} {rfq.unit} · {rfq.delivery_location} · by{" "}
                {new Date(rfq.needed_by).toLocaleDateString("en-IN")}
              </p>
            </div>
            <StatusBadge status={rfq.status} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <>
      <header className="flex flex-col gap-2 mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">Phase 5</p>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="max-w-xl text-sm leading-6 text-zinc-500">
          Deterministic procurement core, agent retrieval, bounded negotiation simulation, and human approval workflow.
          Live evaluation suite runs against versioned fixtures with structured observability telemetry.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <Suspense fallback={<SkeletonList count={2} />}>
            <ActiveRuns />
          </Suspense>
        </div>

        <section aria-labelledby="recent-rfqs-heading">
          <h2 id="recent-rfqs-heading" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Recent RFQs
          </h2>
          <Suspense fallback={<SkeletonList count={3} />}>
            <RecentRfqs />
          </Suspense>
        </section>
      </div>
    </>
  );
}
