import { Suspense } from "react";
import Link from "next/link";
import { api, type SourcingRun, BUYER_TOKEN } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { NotFound } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

async function fetchRuns(): Promise<SourcingRun[] | null> {
  try {
    const page = await api<{ items: SourcingRun[] }>("/sourcing-runs?limit=50", {
      token: BUYER_TOKEN,
    });
    return page.items;
  } catch {
    return null;
  }
}

async function RunsTable() {
  const runs = await fetchRuns();

  if (runs === null) {
    return <NotFound resource="Sourcing runs" />;
  }

  if (runs.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 p-10 text-center dark:border-zinc-700">
        <p className="text-sm text-zinc-500">No sourcing runs yet.</p>
        <Link
          href="/rfqs/new"
          className="mt-3 inline-block text-sm font-medium underline text-zinc-700 dark:text-zinc-300"
        >
          Create your first RFQ →
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-sm" role="table">
        <caption className="sr-only">Sourcing runs</caption>
        <thead className="bg-zinc-50 dark:bg-zinc-900">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Run ID</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Status</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Eligible</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Started</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {runs.map((run) => (
            <tr
              key={run.id}
              className="hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
            >
              <td className="px-4 py-3 font-mono text-xs text-zinc-500">{run.id.slice(0, 8)}…</td>
              <td className="px-4 py-3">
                <StatusBadge status={run.status} />
              </td>
              <td className="px-4 py-3 text-zinc-700 dark:text-zinc-300">{run.eligible_count}</td>
              <td className="px-4 py-3 text-zinc-500 text-xs">
                {new Date(run.started_at).toLocaleString("en-IN")}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  href={`/sourcing-runs/${run.id}`}
                  className="text-xs font-medium text-zinc-700 hover:text-zinc-900 underline dark:text-zinc-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 rounded"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SourcingRunsPage() {
  return (
    <>
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">Sourcing Runs</p>
          <h1 className="text-2xl font-semibold tracking-tight">All runs</h1>
        </div>
        <Link
          href="/rfqs/new"
          className="shrink-0 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          + New RFQ
        </Link>
      </header>

      <Suspense fallback={<SkeletonList count={3} />}>
        <RunsTable />
      </Suspense>
    </>
  );
}
