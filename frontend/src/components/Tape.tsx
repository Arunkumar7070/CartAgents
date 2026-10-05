import { useEffect, useRef } from "react";
import type { Block, Product } from "../api/types";
import { filterLabel } from "../format";
import type { Entry, Pending } from "../hooks/useChat";
import { Citations } from "./Citations";
import { Comparison } from "./Comparison";
import { ConfirmBar } from "./ConfirmBar";
import { Markdown } from "./Markdown";
import { ProductCards } from "./ProductCards";
import { CartReceipt, OrderSlip } from "./Receipt";
import { StepLine } from "./StepLine";

const SUGGESTIONS = [
  "Something light to carry while travelling",
  "Wireless headphones under $150",
  "Compare the ProBook 15 and the UltraBook 13 Air",
  "What is your return policy?",
];

type Props = {
  entries: Entry[];
  streaming: { node: string | null; draft: string } | null;
  pending: Pending | null;
  comparing: string[];
  onSend: (message: string) => void;
  onToggleCompare: (product: Product) => void;
};

export function Tape({ entries, streaming, pending, comparing, onSend, onToggleCompare }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const lastEntryId = entries.at(-1)?.id;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [entries.length, streaming?.draft, streaming?.node]);

  const renderBlock = (block: Block, entryId: number) => {
    switch (block.type) {
      case "text":
        return <Markdown>{block.markdown}</Markdown>;
      case "product_cards":
        return (
          <ProductCards
            products={block.products}
            comparing={comparing}
            onToggleCompare={onToggleCompare}
            onOrder={(product) => onSend(`I'd like to buy the ${product.name}`)}
            disabled={streaming !== null}
          />
        );
      case "comparison":
        return <Comparison block={block} />;
      case "filters":
        return (
          <p className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] uppercase">
            <span className="text-carbon">Understood:</span>
            {block.applied.map((filter) => (
              <span key={filter.field} className="border border-ink px-1.5 py-0.5">
                {filterLabel(filter.field, filter.value)}
              </span>
            ))}
          </p>
        );
      case "cart":
        return <CartReceipt cart={block} />;
      case "order":
        return <OrderSlip order={block} />;
      case "citations":
        return <Citations block={block} />;
      case "confirmation":
        return (
          <ConfirmBar
            block={block}
            active={pending !== null && entryId === lastEntryId && streaming === null}
            onAnswer={onSend}
          />
        );
    }
  };

  return (
    <section
      aria-label="Conversation"
      className="paper perforated relative mx-auto w-full max-w-[640px] px-5 pt-8 pb-10 sm:px-8"
    >
      <header className="text-center">
        <p className="font-mono text-[11px] tracking-[0.3em] text-carbon uppercase">Register 01 / Gemini</p>
        <h2 className="mt-1 font-display text-4xl italic">Your receipt</h2>
        <p className="mt-1 font-mono text-[11px] text-carbon">
          {new Date().toLocaleDateString([], { weekday: "short", month: "short", day: "numeric", year: "numeric" })}
        </p>
        <div className="rule-dashed mt-4" />
      </header>

      <div role="log" aria-live="polite" aria-relevant="additions" className="mt-5 space-y-6">
        {entries.length === 0 ? (
          <div>
            <p className="font-display text-2xl leading-snug">
              Ask about any product. Every price on this tape is printed straight from the catalog.
            </p>
            <ul className="mt-4 space-y-1">
              {SUGGESTIONS.map((suggestion) => (
                <li key={suggestion}>
                  <button
                    type="button"
                    onClick={() => onSend(suggestion)}
                    className="focus-ring group flex w-full items-baseline text-left font-mono text-sm hover:text-stamp"
                  >
                    <span>{suggestion}</span>
                    <span aria-hidden className="leader" />
                    <span aria-hidden className="transition-transform group-hover:translate-x-0.5">
                      &rarr;
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {entries.map((entry) => {
          if (entry.role === "user") {
            return (
              <div key={entry.id} className="feed-in">
                <p className="font-mono text-[10px] tracking-[0.25em] text-carbon uppercase">Customer</p>
                <p className="mt-0.5 font-mono text-sm">&gt; {entry.text}</p>
              </div>
            );
          }
          if (entry.role === "error") {
            return (
              <p key={entry.id} role="alert" className="feed-in border-l-2 border-stamp pl-3 text-sm text-stamp">
                {entry.message}
              </p>
            );
          }
          return (
            <div key={entry.id} className="feed-in space-y-3">
              <p className="font-mono text-[10px] tracking-[0.25em] text-carbon uppercase">CartAgent</p>
              {entry.blocks.map((block, index) => (
                <div key={`${entry.id}-${index}`}>{renderBlock(block, entry.id)}</div>
              ))}
            </div>
          );
        })}

        {streaming ? (
          <div className="space-y-2" aria-busy="true">
            <StepLine node={streaming.node} />
            {streaming.draft ? <Markdown>{streaming.draft}</Markdown> : null}
          </div>
        ) : null}
      </div>
      <div ref={endRef} className="scroll-mb-28" />
    </section>
  );
}
