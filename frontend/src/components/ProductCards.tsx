import { Check, Plus, ShoppingBag } from "lucide-react";
import type { Product } from "../api/types";
import { formatCents } from "../format";

type Props = {
  products: Product[];
  comparing: string[];
  onToggleCompare: (product: Product) => void;
  onOrder: (product: Product) => void;
  disabled: boolean;
};

export function ProductCards({ products, comparing, onToggleCompare, onOrder, disabled }: Props) {
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {products.map((product) => {
        const isComparing = comparing.includes(product.id);
        const lowStock = product.stock > 0 && product.stock <= 3;
        return (
          <li key={product.id} className="flex flex-col border border-rule bg-paper-shade/60 p-3">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-[10px] tracking-[0.18em] text-carbon uppercase">
                {product.brand} / {product.category}
              </span>
              <span className="font-mono text-[10px] text-carbon">{product.id}</span>
            </div>
            <h3 className="mt-1 font-display text-2xl leading-tight">{product.name}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-carbon">{product.specs}</p>
            <div className="mt-auto flex items-end justify-between pt-3">
              <span className="tabular text-xl">{formatCents(product.price_cents)}</span>
              <span className={`font-mono text-[11px] ${lowStock ? "text-stamp" : "text-carbon"}`}>
                {product.stock === 0 ? "SOLD OUT" : `${product.stock} LEFT`}
              </span>
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                disabled={disabled || product.stock === 0}
                onClick={() => onOrder(product)}
                className="focus-ring inline-flex flex-1 items-center justify-center gap-1.5 bg-ink px-2 py-1.5 font-mono text-xs tracking-wider text-paper uppercase transition-transform active:translate-y-px disabled:opacity-40"
              >
                <ShoppingBag aria-hidden size={14} /> Order
              </button>
              <button
                type="button"
                aria-pressed={isComparing}
                onClick={() => onToggleCompare(product)}
                className="focus-ring inline-flex items-center gap-1.5 border border-ink px-2 py-1.5 font-mono text-xs tracking-wider uppercase transition-colors hover:bg-ink/5 aria-pressed:border-stamp aria-pressed:text-stamp"
              >
                {isComparing ? <Check aria-hidden size={14} /> : <Plus aria-hidden size={14} />} Compare
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
