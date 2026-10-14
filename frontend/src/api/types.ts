export type Product = {
  id: string;
  name: string;
  brand: string;
  category: string;
  price_cents: number;
  stock: number;
  specs: string;
  description: string;
};

export type CartLine = {
  product_id: string;
  name: string;
  category: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
};

export type OrderLine = Omit<CartLine, "line_total_cents">;

export type TextBlock = { type: "text"; markdown: string };
export type ProductCardsBlock = { type: "product_cards"; products: Product[] };
export type ComparisonBlock = {
  type: "comparison";
  products: Product[];
  rows: { attribute: string; values: string[]; differs: boolean }[];
};
export type FiltersBlock = { type: "filters"; applied: { field: string; value: string | number }[] };
export type CartBlock = {
  type: "cart";
  lines: CartLine[];
  subtotal_cents: number;
  shipping_cents: number;
  tax_cents: number;
  total_cents: number;
  cart_hash: string;
};
export type ConfirmationBlock = { type: "confirmation"; action: "order" | "cancel" | "return"; prompt: string };
export type OrderBlock = {
  type: "order";
  order_id: string;
  status: string;
  eta: string | null;
  lines: OrderLine[];
  total_cents: number;
  cart_hash: string;
  created_at: string;
};
export type CitationsBlock = {
  type: "citations";
  items: { source: "catalog" | "policy"; ref: string; quote: string }[];
};

export type Block =
  | TextBlock
  | ProductCardsBlock
  | ComparisonBlock
  | FiltersBlock
  | CartBlock
  | ConfirmationBlock
  | OrderBlock
  | CitationsBlock;

export type ChatResponse = {
  session_id: string;
  skill: string | null;
  blocks: Block[];
  pending_confirmation: boolean;
  confirm_token: string | null;
};

export type StreamEvent =
  | { event: "session"; data: { session_id: string } }
  | { event: "step"; data: { node: string; status: "start" | "done" } }
  | { event: "delta"; data: { text: string } }
  | { event: "done"; data: ChatResponse }
  | { event: "error"; data: { code: string; message: string; retry_after?: number | null } };

export type EvalResults = {
  model: string;
  run_at: string;
  routing: { cases: number; correct: number; accuracy: number; failures: Record<string, number> };
  injection: { cases: number; blocked: number };
};
