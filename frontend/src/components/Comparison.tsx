import type { ComparisonBlock } from "../api/types";

export function Comparison({ block }: { block: ComparisonBlock }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">Product comparison</caption>
        <thead>
          <tr>
            <th scope="col" className="w-24 pb-2 font-mono text-[10px] tracking-[0.18em] text-carbon uppercase">
              Spec
            </th>
            {block.products.map((product) => (
              <th key={product.id} scope="col" className="pb-2 pr-3 align-bottom font-display text-xl font-normal">
                {product.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row) => (
            <tr key={row.attribute} className="rule-dashed">
              <th scope="row" className="py-2 pr-2 align-top font-mono text-[11px] font-normal text-carbon uppercase">
                {row.attribute}
              </th>
              {row.values.map((value, index) => (
                <td
                  key={block.products[index].id}
                  className={`py-2 pr-3 align-top ${row.attribute === "Price" ? "tabular" : ""} ${
                    row.differs ? "underline decoration-stamp decoration-2 underline-offset-4" : "text-carbon"
                  }`}
                >
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 font-mono text-[10px] text-carbon uppercase">Underlined values differ</p>
    </div>
  );
}
