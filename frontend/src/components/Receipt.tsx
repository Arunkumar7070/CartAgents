import type { CartBlock, OrderBlock } from "../api/types";
import { formatCents } from "../format";

function LineItem({ label, amount, strong = false }: { label: string; amount: string; strong?: boolean }) {
  return (
    <div className={`flex items-baseline ${strong ? "text-base font-semibold" : "text-sm"}`}>
      <span>{label}</span>
      <span aria-hidden className="leader" />
      <span className="tabular">{amount}</span>
    </div>
  );
}

export function CartReceipt({ cart }: { cart: CartBlock }) {
  return (
    <div className="font-mono">
      {cart.lines.map((line) => (
        <LineItem
          key={line.product_id}
          label={`${line.quantity} x ${line.name}`}
          amount={formatCents(line.line_total_cents)}
        />
      ))}
      <div className="rule-dashed my-2" />
      <LineItem label="Subtotal" amount={formatCents(cart.subtotal_cents)} />
      <LineItem label="Shipping" amount={cart.shipping_cents ? formatCents(cart.shipping_cents) : "FREE"} />
      <LineItem label="Tax 8%" amount={formatCents(cart.tax_cents)} />
      <div className="rule-dashed my-2" />
      <LineItem label="TOTAL" amount={formatCents(cart.total_cents)} strong />
      <p className="mt-2 truncate text-[10px] text-carbon" title={cart.cart_hash}>
        MANDATE {cart.cart_hash.slice(0, 16)}
      </p>
    </div>
  );
}

const STAGES = ["processing", "shipped", "delivered"] as const;

const STAMP_TEXT: Record<string, string> = {
  processing: "Placed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
  return_requested: "Return",
};

export function OrderSlip({ order }: { order: OrderBlock }) {
  const stageIndex = STAGES.indexOf(order.status as (typeof STAGES)[number]);
  return (
    <article className="relative font-mono" aria-label={`Order ${order.order_id}, ${order.status.replace("_", " ")}`}>
      <div className="flex items-baseline justify-between">
        <span className="text-lg font-semibold tracking-wider">{order.order_id}</span>
        <span className="text-[11px] text-carbon">
          {new Date(order.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
        </span>
      </div>
      <div className="mt-2">
        {order.lines.map((line) => (
          <LineItem
            key={line.product_id}
            label={`${line.quantity} x ${line.name}`}
            amount={formatCents(line.unit_price_cents * line.quantity)}
          />
        ))}
        <div className="rule-dashed my-2" />
        <LineItem label="CHARGED" amount={formatCents(order.total_cents)} strong />
      </div>
      {stageIndex >= 0 ? (
        <ol className="mt-3 grid grid-cols-3 gap-1 text-[10px] uppercase" aria-label="Delivery progress">
          {STAGES.map((stage, index) => (
            <li key={stage} aria-current={index === stageIndex ? "step" : undefined}>
              <span className={`block h-1 ${index <= stageIndex ? "bg-ink" : "bg-rule"}`} />
              <span className={index <= stageIndex ? "" : "text-carbon"}>{stage}</span>
            </li>
          ))}
        </ol>
      ) : null}
      <p className="mt-2 min-h-8 pr-28 text-xs text-carbon">{order.eta}</p>
      <span
        aria-hidden
        className="stamp pointer-events-none absolute right-1 bottom-0 border-[3px] border-double border-stamp bg-paper/85 px-2 py-0.5 font-mono text-sm font-semibold tracking-[0.2em] text-stamp uppercase"
      >
        {STAMP_TEXT[order.status] ?? order.status}
      </span>
    </article>
  );
}
