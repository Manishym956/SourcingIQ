export function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="h-3 w-1/3 rounded bg-zinc-200 dark:bg-zinc-700" />
      <div className="mt-3 h-5 w-1/2 rounded bg-zinc-200 dark:bg-zinc-700" />
      <div className="mt-2 h-3 w-2/3 rounded bg-zinc-200 dark:bg-zinc-700" />
    </div>
  );
}

export function TableRowSkeleton({ cols = 5 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="animate-pulse h-4 rounded bg-zinc-200 dark:bg-zinc-700" />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <ul className="flex flex-col gap-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <li key={i}>
          <CardSkeleton />
        </li>
      ))}
    </ul>
  );
}
