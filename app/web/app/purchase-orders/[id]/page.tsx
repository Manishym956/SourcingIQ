"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, type PurchaseOrder, BUYER_TOKEN, APPROVER_TOKEN, errorMessage, RequestError } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";
import { ConfirmDialog } from "@/components/ConfirmDialog";

const DRAFT_NOTICE = "Draft — not submitted. This purchase order has not been sent to the supplier.";

function MoneyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5 text-sm">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="font-mono font-medium">₹{parseFloat(value).toLocaleString("en-IN")}</dd>
    </div>
  );
}

function PurchaseOrderDetail() {
  const params = useParams() as { id: string };
  const poId = params?.id ?? "";
  const [po, setPo] = useState<PurchaseOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [acting, setActing] = useState(false);

  useEffect(() => {
    if (!poId) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await api<PurchaseOrder>(`/purchase-orders/${poId}`, {
          token: BUYER_TOKEN,
        });
        if (!cancelled) setPo(data);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [poId]);

  async function executeDecision(action: "approve" | "reject") {
    if (!po || !poId) return;
    setActing(true);
    setActionError(null);
    try {
      const updated = await api<PurchaseOrder>(`/purchase-orders/${poId}/${action}`, {
        method: "POST",
        body: { draft_version: po.version, reason: reason.trim() || null },
        token: APPROVER_TOKEN,
      });
      setPo(updated);
      setDialog(null);
      setReason("");
    } catch (err) {
      if (err instanceof RequestError && err.status === 403) {
        setActionError(
          "Permission denied. Only an approver can approve or reject this draft.",
        );
      } else {
        setActionError(errorMessage(err));
      }
    } finally {
      setActing(false);
    }
  }

  const isDraft = po?.status === "awaiting_review" || po?.status === "draft_ready";

  return (
    <>
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">
          <Link href="/sourcing-runs" className="hover:underline">Sourcing Runs</Link> /
        </p>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Purchase order</h1>
          {po && <StatusBadge status={po.status} />}
        </div>
      </header>

      {error && <ErrorAlert message={error} />}
      {!error && po === null && <SkeletonList count={3} />}

      {po !== null && (
        <div className="flex flex-col gap-6 max-w-2xl">
          {/* Notice banner */}
          <div
            role="note"
            className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-900/20"
          >
            <p className="text-sm text-amber-800 dark:text-amber-300">{DRAFT_NOTICE}</p>
          </div>

          {/* Supplier + RFQ info */}
          <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-sm font-semibold mb-4">Order details</h2>
            <dl className="grid sm:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-zinc-500">Supplier</dt>
                <dd className="text-sm font-medium">{po.supplier_name}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Currency</dt>
                <dd className="text-sm">{po.currency}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Created</dt>
                <dd className="text-sm">{new Date(po.created_at).toLocaleString("en-IN")}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Version</dt>
                <dd className="text-sm">{po.version}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs text-zinc-500">Run ID</dt>
                <dd className="font-mono text-xs">
                  <Link
                    href={`/sourcing-runs/${po.sourcing_run_id}`}
                    className="underline hover:no-underline"
                  >
                    {po.sourcing_run_id}
                  </Link>
                </dd>
              </div>
            </dl>
          </div>

          {/* Line items */}
          {po.items.length > 0 && (
            <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
              <table className="w-full text-sm">
                <caption className="sr-only">Line items</caption>
                <thead className="bg-zinc-50 dark:bg-zinc-900">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Item</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Qty</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Unit price</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Line total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {po.items.map((item, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 text-zinc-800 dark:text-zinc-200">
                        {String(item.material ?? "")} {String(item.specification ?? "")}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{String(item.quantity ?? "")} {String(item.unit ?? "")}</td>
                      <td className="px-4 py-3 text-right font-mono">₹{Number(item.unit_price).toLocaleString("en-IN")}</td>
                      <td className="px-4 py-3 text-right font-mono">₹{Number(item.line_total).toLocaleString("en-IN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Financials */}
          <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-sm font-semibold mb-3">Financials</h2>
            <dl>
              <MoneyRow label="Subtotal" value={po.subtotal} />
              <MoneyRow label="Freight" value={po.freight} />
              <MoneyRow label="Tax" value={po.tax} />
              <MoneyRow label="Discount" value={po.discount} />
              <div className="border-t border-zinc-200 dark:border-zinc-700 mt-1 pt-1">
                <MoneyRow label="Total" value={po.total} />
              </div>
            </dl>
          </div>

          {/* Terms */}
          {Object.keys(po.terms).length > 0 && (
            <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
              <h2 className="text-sm font-semibold mb-3">Terms</h2>
              <dl className="flex flex-col gap-2 text-sm">
                {Object.entries(po.terms).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4">
                    <dt className="text-zinc-500 capitalize">{k.replace(/_/g, " ")}</dt>
                    <dd className="text-zinc-800 dark:text-zinc-200">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {/* Action error */}
          {actionError && <ErrorAlert message={actionError} />}

          {/* Approve / Reject */}
          {isDraft && (
            <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
              <h2 className="text-sm font-semibold mb-1">Approval</h2>
              <p className="text-xs text-zinc-500 mb-4">
                Only an approver role can approve or reject. Approval keeps the draft on record and
                does not submit anything to the supplier.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDialog("approve")}
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
                >
                  Approve
                </button>
                <button
                  onClick={() => setDialog("reject")}
                  className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 dark:border-red-700 dark:text-red-400"
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {po.status === "approved_draft" && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-800 dark:bg-emerald-900/20">
              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">
                ✓ Approved — this draft is on record. Nothing has been sent to the supplier.
              </p>
            </div>
          )}

          {po.status === "rejected" && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-800 dark:bg-red-900/20">
              <p className="text-sm font-medium text-red-800 dark:text-red-300">
                ✗ Rejected.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={dialog === "approve"}
        title="Approve this draft?"
        description="The draft will be marked approved_draft. This is a record only — nothing is sent to the supplier."
        confirmLabel="Approve"
        confirmVariant="primary"
        onConfirm={() => executeDecision("approve")}
        onCancel={() => !acting && setDialog(null)}
      />
      <ConfirmDialog
        open={dialog === "reject"}
        title="Reject this draft?"
        description="The draft will be marked rejected. This action cannot be undone."
        confirmLabel="Reject"
        confirmVariant="danger"
        onConfirm={() => executeDecision("reject")}
        onCancel={() => !acting && setDialog(null)}
      />
    </>
  );
}

export default function PurchaseOrderPage() {
  return (
    <Suspense fallback={<SkeletonList count={3} />}>
      <PurchaseOrderDetail />
    </Suspense>
  );
}
