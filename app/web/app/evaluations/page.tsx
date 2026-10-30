"use client";

import { useEffect, useState, Suspense } from "react";
import {
  api,
  BUYER_TOKEN,
  errorMessage,
  type EvaluationReport,
  type ObservabilityMetrics,
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

function MetricCard({
  title,
  value,
  detail,
  alert = false,
}: {
  title: string;
  value: string;
  detail?: string;
  alert?: boolean;
}) {
  return (
    <article
      className={`rounded-xl border p-4 ${
        alert
          ? "border-red-200 bg-red-50/40 dark:border-red-900/40 dark:bg-red-900/10"
          : "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900/60"
      }`}
    >
      <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{title}</h3>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      {detail && <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">{detail}</p>}
    </article>
  );
}

function EvaluationsContent() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [metrics, setMetrics] = useState<ObservabilityMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [evalRes, obsRes] = await Promise.all([
          api<EvaluationReport>("/evaluations/latest", { token: BUYER_TOKEN }),
          api<ObservabilityMetrics>("/observability/metrics", { token: BUYER_TOKEN }).catch(() => null),
        ]);
        if (!cancelled) {
          setReport(evalRes);
          if (obsRes) setMetrics(obsRes);
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const newReport = await api<EvaluationReport>("/evaluations/run", {
        method: "POST",
        token: BUYER_TOKEN,
      });
      setReport(newReport);
      // Refresh observability metrics too
      const obsRes = await api<ObservabilityMetrics>("/observability/metrics", { token: BUYER_TOKEN }).catch(() => null);
      if (obsRes) setMetrics(obsRes);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-5xl">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">Phase 5</p>
          <h1 className="text-2xl font-semibold tracking-tight">Evaluations & Observability</h1>
          <p className="mt-1 text-sm text-zinc-500 max-w-2xl">
            Real test runs against versioned fixtures. Scores are computed from live execution, never hardcoded.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300 shrink-0"
        >
          {running ? "Running suite…" : "Run evaluation suite"}
        </button>
      </header>

      {error && <ErrorAlert message={error} />}

      {loading && <SkeletonList count={3} />}

      {!loading && report?.status === "not_run" && (
        <div className="rounded-xl border border-dashed border-zinc-300 p-10 text-center dark:border-zinc-700">
          <p className="text-base font-medium text-zinc-700 dark:text-zinc-300">Not run</p>
          <p className="mt-1 text-sm text-zinc-500 max-w-md mx-auto">
            The evaluation suite has not been executed yet. Click &ldquo;Run evaluation suite&rdquo; to evaluate
            the procurement core, pricing vectors, negotiation bounds, and security guardrails.
          </p>
          <button
            onClick={handleRun}
            disabled={running}
            className="mt-4 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {running ? "Running…" : "Run evaluation suite"}
          </button>
        </div>
      )}

      {!loading && report?.status === "completed" && (
        <>
          {/* Metadata bar */}
          <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/40 flex flex-wrap items-center justify-between gap-4 text-xs text-zinc-600 dark:text-zinc-400">
            <div>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">Report:</span>{" "}
              {report.timestamp ? new Date(report.timestamp).toLocaleString("en-IN") : "—"}
            </div>
            <div>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">Commit:</span>{" "}
              <span className="font-mono">{report.commit}</span>
            </div>
            <div>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">Fixture:</span> v{report.fixture_version}
            </div>
            <div>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">Execution time:</span>{" "}
              {report.duration_ms} ms
            </div>
            <div>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">Result:</span>{" "}
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                {report.passed_cases} of {report.total_cases} passed ({report.pass_rate}%)
              </span>
            </div>
          </div>

          {/* Metric cards */}
          {report.metrics && (
            <section aria-labelledby="metrics-heading">
              <h2 id="metrics-heading" className="text-sm font-semibold mb-3">
                Key Quality Gates & Metrics
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <MetricCard
                  title="Extraction"
                  value={`${report.metrics.extraction_accuracy}%`}
                  detail="Field extraction accuracy"
                />
                <MetricCard
                  title="Eligibility"
                  value={`${report.metrics.eligibility_precision}%`}
                  detail="Precision on labelled specs"
                />
                <MetricCard
                  title="Pricing"
                  value={`${report.metrics.pricing_exact_match}%`}
                  detail="Exact landed-cost match"
                />
                <MetricCard
                  title="Policy Blocks"
                  value={`${report.metrics.policy_violation_block_rate}%`}
                  detail="Unauthorized action stops"
                />
                <MetricCard
                  title="RAG Grounding"
                  value={`${report.metrics.rag_grounded_rate}%`}
                  detail="Citation & abstention rate"
                />
              </div>
            </section>
          )}

          {/* Fixture Test Results */}
          {report.results && report.results.length > 0 && (
            <section aria-labelledby="cases-heading">
              <h2 id="cases-heading" className="text-sm font-semibold mb-3">
                Fixture Test Cases ({report.results.length})
              </h2>
              <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
                <table className="w-full text-sm" role="table">
                  <caption className="sr-only">Evaluation cases</caption>
                  <thead className="bg-zinc-50 dark:bg-zinc-900">
                    <tr>
                      <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Case ID</th>
                      <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Suite</th>
                      <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Description</th>
                      <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Status</th>
                      <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {report.results.map((c) => (
                      <tr key={c.case_id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-medium text-zinc-800 dark:text-zinc-200">{c.case_id}</td>
                        <td className="px-4 py-3 text-xs text-zinc-500 capitalize">{c.suite.replace(/_/g, " ")}</td>
                        <td className="px-4 py-3 text-xs text-zinc-600 dark:text-zinc-400">{c.description}</td>
                        <td className="px-4 py-3">
                          <StatusBadge status={c.status === "passed" ? "accepted" : "rejected"} />
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-zinc-500">{c.duration_ms} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Operational Observability */}
          {metrics && (
            <section aria-labelledby="observability-heading">
              <h2 id="observability-heading" className="text-sm font-semibold mb-3">
                Pipeline Observability & Telemetry
              </h2>
              <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800 grid gap-6 sm:grid-cols-3">
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Catalogue & RFQs</h3>
                  <dl className="flex flex-col gap-1.5 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-zinc-500">Total RFQs:</dt>
                      <dd className="font-mono font-medium">{metrics.counts.rfqs_total}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-zinc-500">Seeded Suppliers:</dt>
                      <dd className="font-mono font-medium">{metrics.counts.suppliers_total}</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Sourcing Runs</h3>
                  <dl className="flex flex-col gap-1.5 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-zinc-500">Total Runs:</dt>
                      <dd className="font-mono font-medium">{metrics.counts.sourcing_runs.total}</dd>
                    </div>
                    {Object.entries(metrics.counts.sourcing_runs.by_status).map(([st, cnt]) => (
                      <div key={st} className="flex justify-between text-xs">
                        <dt className="text-zinc-500 capitalize">{st.replace(/_/g, " ")}:</dt>
                        <dd className="font-mono">{cnt}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Purchase Orders</h3>
                  <dl className="flex flex-col gap-1.5 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-zinc-500">Total Drafts:</dt>
                      <dd className="font-mono font-medium">{metrics.counts.purchase_orders.total}</dd>
                    </div>
                    <div className="flex justify-between text-xs">
                      <dt className="text-emerald-600 dark:text-emerald-400">Approved Drafts:</dt>
                      <dd className="font-mono">{metrics.counts.purchase_orders.approved}</dd>
                    </div>
                    <div className="flex justify-between text-xs">
                      <dt className="text-red-600 dark:text-red-400">Rejected Drafts:</dt>
                      <dd className="font-mono">{metrics.counts.purchase_orders.rejected}</dd>
                    </div>
                    <div className="flex justify-between text-xs">
                      <dt className="text-amber-600 dark:text-amber-400">Awaiting Review:</dt>
                      <dd className="font-mono">{metrics.counts.purchase_orders.awaiting_review}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default function EvaluationsPage() {
  return (
    <Suspense fallback={<SkeletonList count={3} />}>
      <EvaluationsContent />
    </Suspense>
  );
}
