import { X } from "lucide-react";
import type { ReactNode } from "react";
import type { CartBlock, OrderBlock, Product } from "../api/types";
import { formatCents } from "../format";
import { CartReceipt } from "./Receipt";

type Props = {
  cart: CartBlock | null;
  orders: OrderBlock[];
  comparing: Product[];
  busy: boolean;
  onCompare: () => void;
  onRemoveCompare: (product: Product) => void;
  onAsk: (message: string) => void;
};

function Slot({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="paper px-4 py-4">
      <h2 className="font-mono text-[11px] tracking-[0.25em] text-carbon uppercase">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function CounterPanel({ cart, orders, comparing, busy, onCompare, onRemoveCompare, onAsk }: Props) {
  return (
    <aside aria-label="Counter" className="space-y-4">
      <Slot title="Cart awaiting approval">
        {cart ? (
          <CartReceipt cart={cart} />
        ) : (
          <p className="text-sm text-carbon">Nothing on the counter. Order from a product card to see the full total.</p>
        )}
      </Slot>

      <Slot title={`Compare tray (${comparing.length}/4)`}>
        {comparing.length === 0 ? (
          <p className="text-sm text-carbon">Tap Compare on two or more products.</p>
        ) : (
          <>
            <ul className="space-y-1">
              {comparing.map((product) => (
                <li key={product.id} className="flex items-baseline font-mono text-sm">
                  <span className="truncate">{product.name}</span>
                  <span aria-hidden className="leader" />
                  <span className="tabular">{formatCents(product.price_cents)}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${product.name} from comparison`}
                    onClick={() => onRemoveCompare(product)}
                    className="focus-ring ml-2 text-carbon hover:text-stamp"
                  >
                    <X aria-hidden size={14} />
                  </button>
                </li>
              ))}
            </ul>
            <button
              type="button"
              disabled={comparing.length < 2 || busy}
              onClick={onCompare}
              className="focus-ring mt-3 w-full bg-ink py-2 font-mono text-xs tracking-[0.15em] text-paper uppercase disabled:opacity-30"
            >
              Compare side by side
            </button>
          </>
        )}
      </Slot>

      <Slot title="Your orders">
        {orders.length === 0 ? (
          <p className="text-sm text-carbon">No orders in this session yet.</p>
        ) : (
          <ul className="space-y-2 font-mono text-sm">
            {orders.map((order) => (
              <li key={order.order_id} className="flex items-baseline">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onAsk(`What is the status of ${order.order_id}?`)}
                  className="focus-ring hover:text-stamp"
                >
                  {order.order_id}
                </button>
                <span aria-hidden className="leader" />
                <span className="text-xs text-carbon uppercase">{order.status.replace("_", " ")}</span>
              </li>
            ))}
          </ul>
        )}
      </Slot>

      <p className="px-1 font-mono text-[10px] leading-relaxed text-carbon">
        Demo store with invented products and orders. Messages are processed by the Gemini API free tier, which may
        use them to improve Google products, so please do not share personal information.
      </p>
    </aside>
  );
}
