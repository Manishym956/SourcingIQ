export function ErrorAlert({
  title = "Something went wrong",
  message,
  retry,
}: {
  title?: string;
  message: string;
  retry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
    >
      <p className="text-sm font-medium text-red-800 dark:text-red-300">{title}</p>
      <p className="mt-1 text-sm text-red-700 dark:text-red-400">{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="mt-3 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:bg-red-900/40 dark:text-red-300 dark:hover:bg-red-900/60"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function PermissionDenied() {
  return (
    <ErrorAlert
      title="Permission denied"
      message="You do not have permission to perform this action. Check your role and try again."
    />
  );
}

export function NotFound({ resource = "Resource" }: { resource?: string }) {
  return (
    <ErrorAlert
      title={`${resource} not found`}
      message={`The ${resource.toLowerCase()} could not be found. It may have been removed or you may not have access.`}
    />
  );
}
