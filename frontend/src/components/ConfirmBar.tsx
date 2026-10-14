import type { ConfirmationBlock } from "../api/types";

type Props = {
  block: ConfirmationBlock;
  active: boolean;
  onAnswer: (answer: "yes" | "no") => void;
};

const CONFIRM_LABELS: Record<ConfirmationBlock["action"], string> = {
  order: "Place order",
  cancel: "Cancel order",
  return: "Start return",
};

export function ConfirmBar({ block, active, onAnswer }: Props) {
  if (!active) {
    return <p className="font-mono text-[11px] text-carbon uppercase">{block.prompt} (answered)</p>;
  }
  return (
    <div role="group" aria-label={block.prompt} className="flex flex-wrap items-center gap-2">
      <span className="mr-auto font-display text-xl italic">{block.prompt}</span>
      <button
        type="button"
        onClick={() => onAnswer("yes")}
        className="focus-ring bg-stamp px-4 py-2 font-mono text-xs font-semibold tracking-[0.15em] text-stamp-ink uppercase transition-transform hover:-translate-y-px active:translate-y-px"
      >
        {CONFIRM_LABELS[block.action]}
      </button>
      <button
        type="button"
        onClick={() => onAnswer("no")}
        className="focus-ring border border-ink px-4 py-2 font-mono text-xs tracking-[0.15em] uppercase transition-colors hover:bg-ink/5"
      >
        Not now
      </button>
    </div>
  );
}
