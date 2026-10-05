import { stepLabel } from "../format";

export function StepLine({ node }: { node: string | null }) {
  return (
    <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-carbon uppercase">
      <span>{stepLabel(node ?? "")}</span>
      <span aria-hidden className="flex gap-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="matrix-dot inline-block size-1 rounded-full bg-carbon"
            style={{ animationDelay: `${i * 140}ms` }}
          />
        ))}
      </span>
    </p>
  );
}
