import { Suspense } from "react";
import { api, type Supplier, BUYER_TOKEN } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { NotFound } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

async function fetchSuppliers(): Promise<Supplier[] | null> {
  try {
    const page = await api<{ items: Supplier[] }>("/suppliers?limit=50", { token: BUYER_TOKEN });
    return page.items;
  } catch {
    return null;
  }
}

async function SupplierTable() {
  const suppliers = await fetchSuppliers();

  if (suppliers === null) {
    return <NotFound resource="Suppliers" />;
  }

  if (suppliers.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 p-10 text-center dark:border-zinc-700">
        <p className="text-sm text-zinc-500">No suppliers in the catalogue.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-sm" role="table">
        <caption className="sr-only">Supplier catalogue</caption>
        <thead className="bg-zinc-50 dark:bg-zinc-900">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Name</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Status</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Verified</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Regions</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Source</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {suppliers.map((s) => (
            <tr key={s.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors">
              <td className="px-4 py-3 font-medium">{s.name}</td>
              <td className="px-4 py-3">
                <StatusBadge status={s.status} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={s.verification_status} />
              </td>
              <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400 text-xs">
                {s.service_regions.join(", ") || "—"}
              </td>
              <td className="px-4 py-3 text-zinc-500 text-xs">{s.data_source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SuppliersPage() {
  return (
    <>
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">Suppliers</p>
        <h1 className="text-2xl font-semibold tracking-tight">Supplier catalogue</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Seeded demo catalogue. Eligibility is determined per RFQ at sourcing time.
        </p>
      </header>

      <Suspense fallback={<SkeletonList count={3} />}>
        <SupplierTable />
      </Suspense>
    </>
  );
}
