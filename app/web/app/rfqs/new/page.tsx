"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage, BUYER_TOKEN, type Rfq, type SourcingRun } from "@/lib/api";
import { ErrorAlert } from "@/components/ErrorAlert";

type FormData = {
  material: string;
  specification: string;
  quantity: string;
  delivery_location: string;
  needed_by: string;
  budget_amount: string;
  notes: string;
};

type FieldErrors = Partial<Record<keyof FormData | "_form", string>>;

const INITIAL: FormData = {
  material: "",
  specification: "",
  quantity: "",
  delivery_location: "",
  needed_by: "",
  budget_amount: "",
  notes: "",
};

function validateClient(data: FormData): FieldErrors {
  const errors: FieldErrors = {};
  if (!data.material.trim()) errors.material = "Material is required.";
  if (!data.specification.trim()) errors.specification = "Specification is required.";
  const qty = parseFloat(data.quantity);
  if (!data.quantity || isNaN(qty) || qty <= 0) errors.quantity = "Quantity must be a positive number.";
  if (!data.delivery_location.trim()) errors.delivery_location = "Delivery location is required.";
  if (!data.needed_by) {
    errors.needed_by = "Needed-by date is required.";
  } else {
    const todayStr = new Date().toISOString().split("T")[0];
    if (data.needed_by < todayStr) {
      errors.needed_by = "Needed-by date cannot be in the past.";
    }
  }
  if (data.budget_amount) {
    const b = parseFloat(data.budget_amount);
    if (isNaN(b) || b <= 0) errors.budget_amount = "Budget must be a positive number.";
  }
  return errors;
}

function Field({
  id,
  label,
  error,
  children,
  hint,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
        {label}
      </label>
      {hint && <p className="text-xs text-zinc-500">{hint}</p>}
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

function inputClass(error?: string) {
  return `w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-900 dark:text-zinc-100 ${
    error
      ? "border-red-400 dark:border-red-600"
      : "border-zinc-300 dark:border-zinc-700"
  }`;
}

export default function NewRfqPage() {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "review">("form");
  const [data, setData] = useState<FormData>(INITIAL);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  function update(field: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setData((prev) => ({ ...prev, [field]: e.target.value }));
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    };
  }

  function handleNext(e: React.FormEvent) {
    e.preventDefault();
    const errors = validateClient(data);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setStep("review");
  }

  async function handleSubmit() {
    setSubmitting(true);
    setServerError(null);
    try {
      const body: Record<string, unknown> = {
        material: data.material.trim(),
        specification: data.specification.trim(),
        quantity: parseFloat(data.quantity),
        unit: "tonne",
        delivery_location: data.delivery_location.trim(),
        needed_by: data.needed_by,
      };
      if (data.budget_amount) {
        body.budget = { amount: parseFloat(data.budget_amount), currency: "INR" };
      }
      if (data.notes.trim()) body.notes = data.notes.trim();

      const rfq = await api<Rfq>("/rfqs", {
        method: "POST",
        body,
        token: BUYER_TOKEN,
        idempotencyKey: `rfq-${Date.now()}`,
      });

      // Auto-start a sourcing run
      const run = await api<SourcingRun>("/sourcing-runs", {
        method: "POST",
        body: { rfq_id: rfq.id },
        token: BUYER_TOKEN,
        idempotencyKey: `run-${rfq.id}`,
      });

      router.push(`/sourcing-runs/${run.id}`);
    } catch (err) {
      setServerError(errorMessage(err));
      setStep("form");
      setSubmitting(false);
    }
  }

  if (step === "review") {
    return (
      <div>
        <header className="mb-8">
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">New RFQ</p>
          <h1 className="text-2xl font-semibold tracking-tight">Review your request</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Confirm the details before starting a sourcing run.
          </p>
        </header>

        <div className="rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
          <dl className="grid gap-4 sm:grid-cols-2">
            {[
              ["Material", data.material],
              ["Specification", data.specification],
              ["Quantity", `${data.quantity} tonne`],
              ["Delivery location", data.delivery_location],
              ["Needed by", new Date(data.needed_by).toLocaleDateString("en-IN")],
              ["Budget", data.budget_amount ? `₹${parseFloat(data.budget_amount).toLocaleString("en-IN")} INR` : "—"],
              ["Notes", data.notes || "—"],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-medium text-zinc-500">{label}</dt>
                <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        {serverError && (
          <div className="mt-4">
            <ErrorAlert message={serverError} />
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <button
            onClick={() => setStep("form")}
            disabled={submitting}
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
          >
            ← Edit
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="rounded-md bg-zinc-900 px-6 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            {submitting ? "Starting…" : "Confirm and start sourcing run"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-400">Phase 4</p>
        <h1 className="text-2xl font-semibold tracking-tight">New RFQ</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Enter the procurement details. All fields except budget and notes are required.
        </p>
      </header>

      {serverError && (
        <div className="mb-6">
          <ErrorAlert message={serverError} />
        </div>
      )}

      <form onSubmit={handleNext} noValidate className="flex flex-col gap-5 max-w-xl">
        <Field id="material" label="Material" error={fieldErrors.material}>
          <input
            id="material"
            type="text"
            value={data.material}
            onChange={update("material")}
            aria-describedby={fieldErrors.material ? "material-error" : undefined}
            aria-invalid={!!fieldErrors.material}
            placeholder="e.g. Steel"
            className={inputClass(fieldErrors.material)}
          />
        </Field>

        <Field id="specification" label="Specification" error={fieldErrors.specification}>
          <input
            id="specification"
            type="text"
            value={data.specification}
            onChange={update("specification")}
            aria-describedby={fieldErrors.specification ? "specification-error" : undefined}
            aria-invalid={!!fieldErrors.specification}
            placeholder="e.g. Fe 500D"
            className={inputClass(fieldErrors.specification)}
          />
        </Field>

        <Field id="quantity" label="Quantity (tonne)" error={fieldErrors.quantity}>
          <input
            id="quantity"
            type="number"
            min="0.001"
            step="any"
            value={data.quantity}
            onChange={update("quantity")}
            aria-describedby={fieldErrors.quantity ? "quantity-error" : undefined}
            aria-invalid={!!fieldErrors.quantity}
            placeholder="e.g. 10"
            className={inputClass(fieldErrors.quantity)}
          />
        </Field>

        <Field id="delivery_location" label="Delivery location" error={fieldErrors.delivery_location}>
          <input
            id="delivery_location"
            type="text"
            value={data.delivery_location}
            onChange={update("delivery_location")}
            aria-describedby={fieldErrors.delivery_location ? "delivery_location-error" : undefined}
            aria-invalid={!!fieldErrors.delivery_location}
            placeholder="e.g. Mumbai, Maharashtra"
            className={inputClass(fieldErrors.delivery_location)}
          />
        </Field>

        <Field id="needed_by" label="Needed by" error={fieldErrors.needed_by}>
          <input
            id="needed_by"
            type="date"
            value={data.needed_by}
            onChange={update("needed_by")}
            aria-describedby={fieldErrors.needed_by ? "needed_by-error" : undefined}
            aria-invalid={!!fieldErrors.needed_by}
            className={inputClass(fieldErrors.needed_by)}
          />
        </Field>

        <Field
          id="budget_amount"
          label="Budget (INR, optional)"
          error={fieldErrors.budget_amount}
          hint="Leave blank if no budget limit."
        >
          <input
            id="budget_amount"
            type="number"
            min="0.01"
            step="any"
            value={data.budget_amount}
            onChange={update("budget_amount")}
            aria-describedby={fieldErrors.budget_amount ? "budget_amount-error" : undefined}
            aria-invalid={!!fieldErrors.budget_amount}
            placeholder="e.g. 650000"
            className={inputClass(fieldErrors.budget_amount)}
          />
        </Field>

        <Field id="notes" label="Notes (optional)" error={fieldErrors.notes}>
          <textarea
            id="notes"
            rows={3}
            maxLength={2000}
            value={data.notes}
            onChange={update("notes")}
            placeholder="Any additional requirements…"
            className={inputClass(fieldErrors.notes)}
          />
        </Field>

        <div className="pt-2">
          <button
            type="submit"
            className="rounded-md bg-zinc-900 px-6 py-2 text-sm font-medium text-white hover:bg-zinc-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Review →
          </button>
        </div>
      </form>
    </div>
  );
}
