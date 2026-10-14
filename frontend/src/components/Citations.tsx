import type { CitationsBlock } from "../api/types";

export function Citations({ block }: { block: CitationsBlock }) {
  return (
    <details className="group font-mono text-[11px] text-carbon">
      <summary className="focus-ring cursor-pointer list-none tracking-[0.18em] uppercase select-none">
        <span className="group-open:hidden">+</span>
        <span className="hidden group-open:inline">-</span> Sources ({block.items.length})
      </summary>
      <ul className="mt-2 space-y-1">
        {block.items.map((item) => (
          <li key={`${item.source}-${item.ref}`} className="flex gap-2">
            <span className="shrink-0 text-ink">[{item.ref}]</span>
            <span>{item.quote}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
