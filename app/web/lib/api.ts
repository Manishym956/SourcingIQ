export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const BUYER_TOKEN = "local-demo";
export const APPROVER_TOKEN = "local-approver";

export type Money = { amount: string; currency: string };

export type Offer = {
  supplier_id: string;
  supplier_name: string;
  quotation_id: string;
  eligible: boolean;
  exclusion_reasons: string[];
  landed_cost: Money | null;
  lead_time_days: number | null;
  ranking_reasons: string[];
  cost_breakdown: Record<string, string | boolean> | null;
};

export type Rfq = {
  id: string;
  material: string;
  specification: string;
  quantity: string;
  unit: string;
  delivery_location: string;
  needed_by: string;
  budget_amount: string | null;
  currency: string;
  notes: string | null;
  status: string;
  created_at: string;
};

export type SourcingRun = {
  id: string;
  rfq_id: string;
  status: string;
  workflow_version: string;
  started_at: string;
  finished_at: string | null;
  error_code: string | null;
  eligible_count: number;
  data_mode: string;
  orchestrator: string;
  steps: string[];
};

export type WorkflowEvent = {
  id: string;
  event_type: string;
  actor_type: string;
  payload: Record<string, unknown>;
  correlation_id: string;
  created_at: string;
};

export type Negotiation = {
  id: string;
  sourcing_run_id: string;
  quotation_id: string;
  status: string;
  round_count: number;
  max_rounds: number;
  policy: Record<string, string | number>;
  transcript: Array<Record<string, unknown>>;
  final_offer_id: string | null;
  simulation: boolean;
  data_mode: string;
};

export type PurchaseOrder = {
  id: string;
  sourcing_run_id: string;
  rfq_id: string;
  quotation_id: string;
  supplier_id: string;
  supplier_name: string;
  status: string;
  items: Array<Record<string, unknown>>;
  subtotal: string;
  freight: string;
  tax: string;
  discount: string;
  total: string;
  currency: string;
  terms: Record<string, unknown>;
  version: number;
  notice: string;
  created_at: string;
};

export type Supplier = {
  id: string;
  name: string;
  status: string;
  verification_status: string;
  service_regions: string[];
  data_source: string;
  last_updated_at: string;
};

export type EvaluationCaseResult = {
  case_id: string;
  suite: string;
  description: string;
  status: "passed" | "failed";
  duration_ms: number;
  expected: Record<string, unknown>;
  actual: unknown;
  error: string | null;
};

export type EvaluationReport = {
  status: "completed" | "not_run" | "failed";
  message?: string;
  commit?: string;
  timestamp?: string;
  environment?: string;
  fixture_version?: string;
  total_cases?: number;
  passed_cases?: number;
  failed_cases?: number;
  pass_rate?: number;
  failed_case_ids?: string[];
  duration_ms?: number;
  metrics?: {
    extraction_accuracy: number;
    eligibility_precision: number;
    pricing_exact_match: number;
    policy_violation_block_rate: number;
    rag_grounded_rate: number;
  };
  results?: EvaluationCaseResult[];
};

export type ObservabilityMetrics = {
  service: string;
  data_mode: string;
  counts: {
    rfqs_total: number;
    suppliers_total: number;
    sourcing_runs: {
      total: number;
      by_status: Record<string, number>;
    };
    purchase_orders: {
      total: number;
      approved: number;
      rejected: number;
      awaiting_review: number;
    };
  };
};

export type ApiError = {
  error?: { code?: string; message?: string; details?: Array<{ field?: string; issue?: string }> };
};

export class RequestError extends Error {
  status: number;
  code: string;
  details: Array<{ field?: string; issue?: string }>;

  constructor(status: number, message: string, code = "HTTP_ERROR", details: Array<{ field?: string; issue?: string }> = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function api<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    token?: string;
    idempotencyKey?: string;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${options.token ?? BUYER_TOKEN}`,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  const payload = (await response.json()) as T & ApiError;
  if (!response.ok) {
    throw new RequestError(
      response.status,
      payload.error?.message ?? "The request could not be completed.",
      payload.error?.code ?? "HTTP_ERROR",
      payload.error?.details ?? [],
    );
  }
  return payload;
}

export function errorMessage(error: unknown): string {
  if (error instanceof RequestError) {
    const extra = error.details.map((item) => item.issue).filter(Boolean).join(" ");
    return extra ? `${error.message} ${extra}` : error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "The request could not be completed.";
}
