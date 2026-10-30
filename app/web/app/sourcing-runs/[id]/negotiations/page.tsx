"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { api, type Negotiation, BUYER_TOKEN, errorMessage } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorAlert } from "@/components/ErrorAlert";
import { SkeletonList } from "@/components/LoadingSkeleton";

type Turn = Record<string, unknown>;

function SimulationBanner() {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-900/20"
    >
      <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
        Simulation — no message will be sent to any supplier.
      </p>
    </div>
  );
}

function Transcript({ turns }: { turns: Turn[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length]);

  if (turns.length === 0) {
    return <p className="text-sm text-zinc-500">No turns yet. Submit your first offer below.</p>;
  }

  return (
    <ol aria-label="Negotiation transcript" className="flex flex-col gap-3">
      {turns.map((turn, i) => {
        const actor = String(turn.actor ?? "unknown");
        const isBuyer = actor === "buyer";
        const price = turn.proposed_unit_price ?? turn.counter_unit_price;
        const outcome = turn.outcome ? String(turn.outcome) : null;
        return (
          <li
            key={i}
            className={`rounded-lg px-4 py-3 text-sm max-w-md ${
              isBuyer
                ? "bg-zinc-100 dark:bg-zinc-800 self-end"
                : "bg-blue-50 dark:bg-blue-900/20 self-start"
            }`}
          >
            <p className="font-medium text-xs text-zinc-500 mb-1">{isBuyer ? "You (buyer)" : "Supplier (simulated)"}</p>
            {price !== undefined && (
              <p>
                Proposed: <span className="font-mono font-medium">₹{Number(price).toLocaleString("en-IN")}/tonne</span>
              </p>
            )}
            {turn.message != null && <p className="text-zinc-600 dark:text-zinc-400 mt-1">{String(turn.message as string)}</p>}
            {outcome && (
              <p className="mt-1">
                <StatusBadge status={outcome} />
              </p>
            )}
          </li>
        );
      })}
      <div ref={bottomRef} />
    </ol>
  );
}

function StartNegotiationForm({
  runId,
  quotationId,
  onStarted,
}: {
  runId: string;
  quotationId: string;
  onStarted: (neg: Negotiation) => void;
}) {
  const [floor, setFloor] = useState("");
  const [ceiling, setCeiling] = useState("");
  const [maxRounds, setMaxRounds] = useState("3");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const neg = await api<Negotiation>(`/sourcing-runs/${runId}/negotiations`, {
        method: "POST",
        body: {
          quotation_id: quotationId,
          max_rounds: parseInt(maxRounds, 10),
          floor_unit_price: parseFloat(floor),
          ceiling_unit_price: parseFloat(ceiling),
        },
        token: BUYER_TOKEN,
        idempotencyKey: `neg-${runId}-${quotationId}-${Date.now()}`,
      });
      onStarted(neg);
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 max-w-sm">
      <h2 className="text-sm font-semibold">Configure simulation</h2>
      {error && <ErrorAlert message={error} />}
      <div className="flex flex-col gap-1">
        <label htmlFor="floor" className="text-sm font-medium">Floor unit price (INR/tonne)</label>
        <input
          id="floor"
          type="number"
          min="0.01"
          step="any"
          required
          value={floor}
          onChange={(e) => setFloor(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="ceiling" className="text-sm font-medium">Ceiling unit price (INR/tonne)</label>
        <input
          id="ceiling"
          type="number"
          min="0.01"
          step="any"
          required
          value={ceiling}
          onChange={(e) => setCeiling(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="maxRounds" className="text-sm font-medium">Max rounds (1–5)</label>
        <input
          id="maxRounds"
          type="number"
          min="1"
          max="5"
          step="1"
          required
          value={maxRounds}
          onChange={(e) => setMaxRounds(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {submitting ? "Starting…" : "Start simulation"}
      </button>
    </form>
  );
}

function TurnForm({
  negotiationId,
  onTurn,
  disabled,
}: {
  negotiationId: string;
  onTurn: (neg: Negotiation) => void;
  disabled: boolean;
}) {
  const [price, setPrice] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const neg = await api<Negotiation>(`/negotiations/${negotiationId}/turns`, {
        method: "POST",
        body: {
          proposed_unit_price: parseFloat(price),
          message: message.trim() || null,
        },
        token: BUYER_TOKEN,
      });
      onTurn(neg);
      setPrice("");
      setMessage("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
      <h3 className="text-sm font-medium">Submit your offer</h3>
      {error && <ErrorAlert message={error} />}
      <div className="flex gap-3 items-end">
        <div className="flex flex-col gap-1 flex-1">
          <label htmlFor="price" className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Unit price (INR/tonne)
          </label>
          <input
            id="price"
            type="number"
            min="0.01"
            step="any"
            required
            disabled={disabled}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <button
          type="submit"
          disabled={disabled || submitting}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 shrink-0"
        >
          {submitting ? "Sending…" : "Submit"}
        </button>
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="neg-message" className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Message (optional)
        </label>
        <input
          id="neg-message"
          type="text"
          maxLength={500}
          disabled={disabled}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Your buyer comment…"
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>
    </form>
  );
}

function NegotiationView({ runId }: { runId: string }) {
  const searchParams = useSearchParams();
  const quotationId = searchParams.get("quotation_id") ?? "";

  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const neg = await api<Negotiation>(`/sourcing-runs/${runId}/negotiations`, {
          token: BUYER_TOKEN,
        });
        if (!cancelled) {
          setNegotiation(neg);
        }
      } catch {
        // 404 means not started yet — that's fine
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [runId]);

  const isTerminal =
    negotiation !== null &&
    ["accepted", "round_cap", "cancelled_by_buyer", "failed"].includes(negotiation.status);

  return (
    <div className="flex flex-col gap-5 max-w-2xl">
      <SimulationBanner />

      {loading && <SkeletonList count={2} />}

      {!loading && negotiation === null && (
        <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
          {!quotationId ? (
            <p className="text-sm text-zinc-500">
              Select a supplier from the{" "}
              <Link href={`/sourcing-runs/${runId}/offers`} className="underline">
                comparison page
              </Link>{" "}
              to start a negotiation.
            </p>
          ) : (
            <StartNegotiationForm
              runId={runId}
              quotationId={quotationId}
              onStarted={setNegotiation}
            />
          )}
        </div>
      )}

      {negotiation !== null && (
        <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800 flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <StatusBadge status={negotiation.status} />
              <span className="text-sm text-zinc-500">
                Round {negotiation.round_count} of {negotiation.max_rounds}
              </span>
            </div>
            <dl className="flex gap-4 text-xs text-zinc-500">
              <div>
                <dt className="inline">Floor: </dt>
                <dd className="inline font-mono">₹{String(negotiation.policy.floor_unit_price ?? "—")}</dd>
              </div>
              <div>
                <dt className="inline">Ceiling: </dt>
                <dd className="inline font-mono">₹{String(negotiation.policy.ceiling_unit_price ?? "—")}</dd>
              </div>
            </dl>
          </div>

          <Transcript turns={negotiation.transcript} />

          {!isTerminal && (
            <TurnForm
              negotiationId={negotiation.id}
              onTurn={setNegotiation}
              disabled={isTerminal}
            />
          )}

          {isTerminal && (
            <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Negotiation complete — {negotiation.status.replace(/_/g, " ")}
              </p>
              {negotiation.status === "accepted" && (
                <Link
                  href={`/sourcing-runs/${runId}/offers`}
                  className="mt-2 inline-block text-sm underline text-zinc-600 dark:text-zinc-400"
                >
                  Draft a purchase order →
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NegotiationContent() {
  const params = useParams() as { id: string };
  const runId = params?.id ?? "";

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
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Negotiation simulator</h1>
      </header>

      {runId ? <NegotiationView runId={runId} /> : <SkeletonList count={2} />}
    </>
  );
}

export default function NegotiationPage() {
  return (
    <Suspense fallback={<SkeletonList count={2} />}>
      <NegotiationContent />
    </Suspense>
  );
}
