export type BadgeVariant = "ok" | "warn" | "error" | "neutral" | "info";

const MAP: Record<string, BadgeVariant> = {
  created: "neutral",
  validating: "info",
  sourcing: "info",
  comparing: "info",
  negotiating: "info",
  draft_ready: "ok",
  awaiting_review: "warn",
  approved_draft: "ok",
  rejected: "error",
  cancelled: "neutral",
  failed: "error",
  active: "ok",
  inactive: "neutral",
  pending: "warn",
  accepted: "ok",
  round_cap: "warn",
  cancelled_by_buyer: "neutral",
};

const STYLE: Record<BadgeVariant, string> = {
  ok: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:ring-emerald-800",
  warn: "bg-amber-50 text-amber-800 ring-1 ring-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:ring-amber-800",
  error: "bg-red-50 text-red-800 ring-1 ring-red-200 dark:bg-red-900/20 dark:text-red-300 dark:ring-red-800",
  neutral: "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700",
  info: "bg-blue-50 text-blue-800 ring-1 ring-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:ring-blue-800",
};

const DOT: Record<BadgeVariant, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  error: "bg-red-500",
  neutral: "bg-zinc-400",
  info: "bg-blue-500",
};

export function StatusBadge({ status }: { status: string }) {
  const variant = MAP[status] ?? "neutral";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLE[variant]}`}
      aria-label={`Status: ${status}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOT[variant]}`} aria-hidden="true" />
      {status.replace(/_/g, " ")}
    </span>
  );
}
