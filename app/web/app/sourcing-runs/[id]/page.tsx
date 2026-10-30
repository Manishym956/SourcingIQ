import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api, type SourcingRun, BUYER_TOKEN, RequestError } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

async function fetchRun(id: string): Promise<SourcingRun | null | "forbidden"> {
  try {
    return await api<SourcingRun>(`/sourcing-runs/${id}`, { token: BUYER_TOKEN });
  } catch (err) {
    if (err instanceof RequestError) {
      if (err.status === 404) return null;
      if (err.status === 403) return "forbidden";
    }
    return null;
  }
}

const STEP_LABELS: Record<string, string> = {
  start: "Run started",
  eligibility: "Eligibility checked",
  costing: "Costs calculated",
  ranking: "Offers ranked",
  comparison_saved: "Comparison saved",
  negotiation_started: "Negotiation started",
  negotiation_accepted: "Negotiation accepted",
  draft_created: "Draft PO created",
};

function Timeline({ steps }: { steps: string[] }) {
  if (steps.length === 0) {
    return <p className="text-sm text-zinc-500">No steps recorded.</p>;
  }
  return (
    <ol aria-label="Run steps" className="relative flex flex-col gap-0">
      {steps.map((step, i) => (
        <li key={i} className="flex items-start gap-3 pb-4 last:pb-0">
          <div className="flex flex-col items-center">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
              <svg aria-hidden="true" className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
                <path d="M10.28 2.28a.75.75 0 0 0-1.06 0L4.5 7 2.78 5.28a.75.75 0 1 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.06 0l5.25-5.25a.75.75 0 0 0 0-1.06Z" />
              </svg>
            </div>
            {i < steps.length - 1 && (
              <div className="h-full w-px flex-1 bg-zinc-200 dark:bg-zinc-800 mt-0.5 min-h-[1rem]" />
            )}
          </div>
          <span className="pt-0.5 text-sm text-zinc-700 dark:text-zinc-300">
            {STEP_LABELS[step] ?? step}
          </span>
        </li>
      ))}
    </ol>
  );
}

async function RunDetailContent({
  idPromise,
}: {
  idPromise: Promise<{ id: string }>;
}) {
  const { id } = await idPromise;
  const run = await fetchRun(id);

  if (run === null) notFound();
  if (run === "forbidden") {
    return <ErrorAlert title="Permission denied" message="You do not have access to this run." />;
  }

  return (
    <>
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">
          <Link href="/sourcing-runs" className="hover:underline">Sourcing Runs</Link> /
        </p>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight font-mono">
            {run.id.slice(0, 8)}…
          </h1>
          <StatusBadge status={run.status} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Metadata */}
        <div className="lg:col-span-1">
          <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Details</h2>
            <dl className="flex flex-col gap-3">
              <div>
                <dt className="text-xs text-zinc-500">RFQ ID</dt>
                <dd className="font-mono text-xs text-zinc-700 dark:text-zinc-300">
                  <Link href={`/rfqs/${run.rfq_id}`} className="underline hover:no-underline">
                    {run.rfq_id.slice(0, 8)}…
                  </Link>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Eligible suppliers</dt>
                <dd className="text-sm font-medium">{run.eligible_count}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Started</dt>
                <dd className="text-xs text-zinc-700 dark:text-zinc-300">
                  {new Date(run.started_at).toLocaleString("en-IN")}
                </dd>
              </div>
              {run.finished_at && (
                <div>
                  <dt className="text-xs text-zinc-500">Finished</dt>
                  <dd className="text-xs text-zinc-700 dark:text-zinc-300">
                    {new Date(run.finished_at).toLocaleString("en-IN")}
                  </dd>
                </div>
              )}
              {run.error_code && (
                <div>
                  <dt className="text-xs text-zinc-500">Error</dt>
                  <dd className="text-xs text-red-600 dark:text-red-400">{run.error_code}</dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-zinc-500">Orchestrator</dt>
                <dd className="text-xs text-zinc-600 dark:text-zinc-400">{run.orchestrator}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Data mode</dt>
                <dd className="text-xs text-zinc-600 dark:text-zinc-400">{run.data_mode}</dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Timeline + Actions */}
        <div className="lg:col-span-2 flex flex-col gap-5">
          <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Timeline</h2>
            <Timeline steps={run.steps} />
          </div>

          <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Actions</h2>
            <div className="flex flex-wrap gap-3">
              <Link
                href={`/sourcing-runs/${run.id}/offers`}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
              >
                View comparison →
              </Link>
              <Link
                href={`/sourcing-runs/${run.id}/negotiations`}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
              >
                Negotiation →
              </Link>
              <Link
                href={`/sourcing-runs/${run.id}/purchase-orders`}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
              >
                Purchase order →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<SkeletonList count={3} />}>
      <RunDetailContent idPromise={params} />
    </Suspense>
  );
}
