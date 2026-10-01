import { Moon, RotateCcw, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchOrders } from "./api/client";
import type { CartBlock, OrderBlock, Product } from "./api/types";
import { Composer } from "./components/Composer";
import { CounterPanel } from "./components/CounterPanel";
import { Evals } from "./components/Evals";
import { Tape } from "./components/Tape";
import { WakeBanner } from "./components/WakeBanner";
import { useChat } from "./hooks/useChat";

type View = "counter" | "evals";
type Theme = "light" | "dark";

const MAX_COMPARED = 4;

function viewFromHash(): View {
  return window.location.hash === "#evals" ? "evals" : "counter";
}

function storedTheme(): string | null {
  try {
    return localStorage.getItem("cartagent.theme");
  } catch {
    return null;
  }
}

function initialTheme(): Theme {
  const stored = storedTheme();
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function App() {
  const { state, send, reset } = useChat();
  const [view, setView] = useState<View>(viewFromHash);
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [comparing, setComparing] = useState<Product[]>([]);
  const [orders, setOrders] = useState<OrderBlock[]>([]);

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("cartagent.theme", theme);
    } catch {
      return;
    }
  }, [theme]);

  useEffect(() => {
    if (!state.sessionId) {
      setOrders([]);
      return;
    }
    fetchOrders(state.sessionId)
      .then(setOrders)
      .catch(() => setOrders([]));
  }, [state.sessionId, state.turn]);

  const pendingCart = useMemo<CartBlock | null>(() => {
    if (state.pending?.action !== "order") return null;
    const lastAgent = [...state.entries].reverse().find((entry) => entry.role === "agent");
    if (lastAgent?.role !== "agent") return null;
    return lastAgent.blocks.find((block): block is CartBlock => block.type === "cart") ?? null;
  }, [state.entries, state.pending]);

  const toggleCompare = (product: Product) =>
    setComparing((current) =>
      current.some((p) => p.id === product.id)
        ? current.filter((p) => p.id !== product.id)
        : [...current, product].slice(-MAX_COMPARED),
    );

  const compareSelected = () => {
    const names = comparing.map((p) => p.name);
    send(`Compare the ${names.slice(0, -1).join(", the ")} and the ${names.at(-1)}`);
  };

  const startOver = () => {
    reset();
    setComparing([]);
  };

  const busy = state.streaming !== null;

  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex max-w-[1180px] flex-wrap items-end gap-x-6 gap-y-2 px-4 pt-6 pb-4 sm:px-6">
        <div className="mr-auto">
          <h1 className="font-display text-5xl leading-none sm:text-6xl">
            Cart<span className="italic text-stamp">Agent</span>
          </h1>
          <p className="mt-1 font-mono text-[11px] tracking-[0.25em] text-carbon uppercase">
            The counter that can't make up prices
          </p>
        </div>
        <nav aria-label="Primary" className="flex items-center gap-1 font-mono text-xs tracking-[0.15em] uppercase">
          <a
            href="#"
            aria-current={view === "counter" ? "page" : undefined}
            className="focus-ring px-2 py-1 aria-[current=page]:underline aria-[current=page]:decoration-stamp aria-[current=page]:decoration-2 aria-[current=page]:underline-offset-4"
          >
            Counter
          </a>
          <a
            href="#evals"
            aria-current={view === "evals" ? "page" : undefined}
            className="focus-ring px-2 py-1 aria-[current=page]:underline aria-[current=page]:decoration-stamp aria-[current=page]:decoration-2 aria-[current=page]:underline-offset-4"
          >
            Evals
          </a>
          <button
            type="button"
            onClick={startOver}
            className="focus-ring ml-2 inline-flex items-center gap-1 px-2 py-1 hover:text-stamp"
          >
            <RotateCcw aria-hidden size={14} /> New receipt
          </button>
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            className="focus-ring grid size-8 place-items-center hover:text-stamp"
          >
            {theme === "dark" ? <Sun aria-hidden size={16} /> : <Moon aria-hidden size={16} />}
          </button>
        </nav>
      </header>

      <main className="mx-auto max-w-[1180px] px-4 pb-10 sm:px-6">
        {view === "evals" ? (
          <Evals />
        ) : (
          <>
            <WakeBanner />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="flex min-w-0 flex-col gap-3">
                <Tape
                  entries={state.entries}
                  streaming={state.streaming}
                  pending={state.pending}
                  comparing={comparing.map((p) => p.id)}
                  onSend={send}
                  onToggleCompare={toggleCompare}
                />
                <div className="sticky bottom-3">
                  <Composer onSend={send} busy={busy} awaitingConfirmation={state.pending !== null} />
                </div>
              </div>
              <CounterPanel
                cart={pendingCart}
                orders={orders}
                comparing={comparing}
                busy={busy}
                onCompare={compareSelected}
                onRemoveCompare={toggleCompare}
                onAsk={send}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
