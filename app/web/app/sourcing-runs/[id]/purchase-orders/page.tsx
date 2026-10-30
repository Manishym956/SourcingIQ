"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { api, BUYER_TOKEN, errorMessage, type PurchaseOrder } from "@/lib/api";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

function RunPurchaseOrderDetail() {
  const router = useRouter();
  const params = useParams() as { id: string };
  const runId = params?.id ?? "";
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    async function load() {
      try {
        const po = await api<PurchaseOrder>(`/sourcing-runs/${runId}/purchase-orders`, {
          token: BUYER_TOKEN,
        });
        if (!cancelled) {
          router.replace(`/purchase-orders/${po.id}`);
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [runId, router]);

  if (error) {
    return (
      <div>
        <header className="mb-8">
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">
            <Link href="/sourcing-runs" className="hover:underline">Sourcing Runs</Link>
            {" / "}
            <Link href={`/sourcing-runs/${runId}`} className="hover:underline">
              {runId ? `${runId.slice(0, 8)}…` : "Run"}
            </Link>
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Purchase order</h1>
        </header>
        <ErrorAlert
          title="No purchase order"
          message={`${error} — Draft one from the comparison page.`}
        />
        <div className="mt-4">
          <Link
            href={`/sourcing-runs/${runId}/offers`}
            className="text-sm underline text-zinc-600 dark:text-zinc-400"
          >
            ← View comparison
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Purchase order</h1>
      </header>
      <SkeletonList count={2} />
    </div>
  );
}

export default function RunPurchaseOrderPage() {
  return (
    <Suspense fallback={<SkeletonList count={2} />}>
      <RunPurchaseOrderDetail />
    </Suspense>
  );
}
