const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function formatCents(cents: number): string {
  return usd.format(cents / 100);
}

const STEP_LABELS: Record<string, string> = {
  route_skill: "Reading your request",
  search_products: "Searching the catalog",
  generate_qa_answer: "Writing the answer",
  prepare_order: "Pricing your cart",
  prepare_return: "Checking the return policy",
  await_confirmation: "Waiting for your go-ahead",
  clarify_confirmation: "Waiting for your go-ahead",
  finalize_action: "Updating your order",
  track_order: "Looking up your orders",
  compare_products: "Lining products up",
};

export function stepLabel(node: string): string {
  return STEP_LABELS[node] ?? "Working";
}

const FILTER_LABELS: Record<string, (value: string | number) => string> = {
  category: (value) => String(value),
  brand: (value) => String(value),
  min_price_cents: (value) => `from ${formatCents(Number(value))}`,
  max_price_cents: (value) => `under ${formatCents(Number(value))}`,
};

export function filterLabel(field: string, value: string | number): string {
  return FILTER_LABELS[field]?.(value) ?? `${field}: ${value}`;
}
