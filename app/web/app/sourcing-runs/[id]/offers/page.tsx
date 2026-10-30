"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { api, type Offer, BUYER_TOKEN, errorMessage, type SourcingRun } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

function CostBreakdown({ bd }: { bd: Record<string, string | boolean> }) {
  const rows = Object.entries(bd).filter(([k]) => !["eligible"].includes(k));
  return (
    <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2 col-span-1">
          <dt className="capitalize text-zinc-500">{k.replace(/_/g, " ")}</dt>
          <dd className="font-mono">{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function OfferRow({
  offer,
  runId,
  expanded,
  onToggle,
}: {
  offer: Offer;
  runId: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const router = useRouter();

  async function startDraft() {
    try {
      const po = await api<{ id: string }>("/purchase-orders/drafts", {
        method: "POST",
        body: { sourcing_run_id: runId, quotation_id: offer.quotation_id },
        token: BUYER_TOKEN,
        idempotencyKey: `draft-${runId}-${offer.quotation_id}`,
      });
      router.push(`/purchase-orders/${po.id}`);
    } catch (err) {
      alert(errorMessage(err));
    }
  }

  return (
    <>
      <tr className={`border-b border-zinc-100 dark:border-zinc-800 ${offer.eligible ? "hover:bg-zinc-50 dark:hover:bg-zinc-900" : "opacity-70"}`}>
        <td className="px-4 py-3 text-sm font-medium">{offer.supplier_name}</td>
        <td className="px-4 py-3">
          <StatusBadge status={offer.eligible ? "active" : "rejected"} />
        </td>
        <td className="px-4 py-3 text-sm text-right font-mono">
          {offer.landed_cost ? (
            <span>₹{parseFloat(offer.landed_cost.amount).toLocaleString("en-IN")}</span>
          ) : (
            <span className="text-zinc-400">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-sm text-right text-zinc-600 dark:text-zinc-400">
          {offer.lead_time_days !== null ? `${offer.lead_time_days}d` : "—"}
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-2">
            {offer.cost_breakdown && (
              <button
                onClick={onToggle}
                aria-expanded={expanded}
                className="rounded text-xs text-zinc-500 underline hover:text-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
              >
                {expanded ? "Hide" : "Details"}
              </button>
            )}
            {offer.eligible && (
              <>
                <Link
                  href={`/sourcing-runs/${runId}/negotiations?quotation_id=${offer.quotation_id}`}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:text-zinc-300"
                >
                  Negotiate
                </Link>
                <button
                  onClick={startDraft}
                  className="rounded-md bg-zinc-900 px-2 py-1 text-xs font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  Draft PO
                </button>
              </>
            )}
          </div>
        </td>
      </tr>

      {/* Exclusion reasons */}
      {!offer.eligible && offer.exclusion_reasons.length > 0 && (
        <tr className="border-b border-zinc-100 dark:border-zinc-800 bg-red-50/50 dark:bg-red-900/5">
          <td colSpan={5} className="px-4 pb-3 pt-0">
            <ul className="flex flex-wrap gap-2">
              {offer.exclusion_reasons.map((r) => (
                <li
                  key={r}
                  className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300"
                >
                  {r}
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}

      {/* Cost breakdown expansion */}
      {expanded && offer.cost_breakdown && (
        <tr className="border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
          <td colSpan={5} className="px-4 pb-3 pt-0">
            <CostBreakdown bd={offer.cost_breakdown} />
          </td>
        </tr>
      )}
    </>
  );
}

function OffersDetail() {
  const params = useParams() as { id: string };
  const runId = params?.id ?? "";
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [run, setRun] = useState<SourcingRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    async function load() {
      try {
        const [runRes, offersRes] = await Promise.all([
          api<SourcingRun>(`/sourcing-runs/${runId}`, { token: BUYER_TOKEN }),
          api<{ offers: Offer[] }>(`/sourcing-runs/${runId}/offers`, { token: BUYER_TOKEN }),
        ]);
        if (!cancelled) {
          setRun(runRes);
          setOffers(offersRes.offers);
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [runId]);

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <>
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">
          <Link href="/sourcing-runs" className="hover:underline">Sourcing Runs</Link>
          {" / "}
          <Link href={`/sourcing-runs/${runId}`} className="hover:underline">
            {runId ? `${runId.slice(0, 8)}…` : "Run"}
          </Link>
          {" /"}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Supplier comparison</h1>
        {run && (
          <p className="mt-1 text-sm text-zinc-500">
            {run.eligible_count} eligible · status: {run.status}
          </p>
        )}
      </header>

      {error && <ErrorAlert message={error} />}

      {!error && offers === null && <SkeletonList count={4} />}

      {offers !== null && offers.length === 0 && (
        <p className="text-sm text-zinc-500">No offers found for this run.</p>
      )}

      {offers !== null && offers.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-sm" role="table">
            <caption className="sr-only">Supplier comparison for run {runId}</caption>
            <thead className="bg-zinc-50 dark:bg-zinc-900">
              <tr>
                <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Supplier</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Eligible</th>
                <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Landed cost (INR)</th>
                <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Lead time</th>
                <th scope="col" className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {offers.map((offer) => (
                <OfferRow
                  key={offer.quotation_id}
                  offer={offer}
                  runId={runId}
                  expanded={expanded.has(offer.quotation_id)}
                  onToggle={() => toggleExpanded(offer.quotation_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function OffersPage() {
  return (
    <Suspense fallback={<SkeletonList count={4} />}>
      <OffersDetail />
    </Suspense>
  );
}
