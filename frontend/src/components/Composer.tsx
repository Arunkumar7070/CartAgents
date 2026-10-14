import { ArrowUp } from "lucide-react";
import { type FormEvent, useState } from "react";

type Props = {
  onSend: (message: string) => void;
  busy: boolean;
  awaitingConfirmation: boolean;
};

export function Composer({ onSend, busy, awaitingConfirmation }: Props) {
  const [draft, setDraft] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <form onSubmit={submit} className="paper mx-auto flex w-full max-w-[640px] items-center gap-2 px-3 py-2">
      <label htmlFor="composer" className="sr-only">
        Message CartAgent
      </label>
      <span aria-hidden className="pl-1 font-mono text-carbon">
        &gt;
      </span>
      <input
        id="composer"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        maxLength={2000}
        autoComplete="off"
        placeholder={awaitingConfirmation ? "Reply yes or no, or use the buttons above" : "Ask the counter"}
        className="min-w-0 flex-1 bg-transparent py-2 font-mono text-sm placeholder:text-carbon focus:outline-none"
      />
      <button
        type="submit"
        disabled={busy || !draft.trim()}
        aria-label="Send"
        className="focus-ring grid size-9 place-items-center bg-ink text-paper transition-transform active:translate-y-px disabled:opacity-30"
      >
        <ArrowUp aria-hidden size={18} />
      </button>
    </form>
  );
}
