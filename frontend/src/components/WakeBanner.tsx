import { useEffect, useState } from "react";
import { fetchHealth } from "../api/client";

type Status = "checking" | "warming" | "ready" | "unavailable";

const SLOW_AFTER_MS = 1500;
const RETRY_EVERY_MS = 4000;
const GIVE_UP_AFTER_MS = 120_000;

export function WakeBanner() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    const started = Date.now();
    const slowTimer = setTimeout(() => !cancelled && setStatus((s) => (s === "checking" ? "warming" : s)), SLOW_AFTER_MS);

    const poll = async () => {
      while (!cancelled && Date.now() - started < GIVE_UP_AFTER_MS) {
        const ready = await fetchHealth().catch(() => false);
        if (cancelled) return;
        if (ready) {
          setStatus("ready");
          return;
        }
        setStatus("warming");
        await new Promise((resolve) => setTimeout(resolve, RETRY_EVERY_MS));
      }
      if (!cancelled) setStatus("unavailable");
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, []);

  if (status === "ready" || status === "checking") return null;
  return (
    <div
      role="status"
      className="mx-auto mb-4 flex w-full max-w-[640px] items-center gap-3 border border-dashed border-ink px-4 py-2 font-mono text-xs tracking-[0.15em] uppercase"
    >
      {status === "warming" ? (
        <>
          <span className="matrix-dot inline-block size-2 rounded-full bg-stamp" aria-hidden />
          Warming the printer. Free servers nap when idle, this takes up to a minute.
        </>
      ) : (
        <>The register is offline right now. Please try again later.</>
      )}
    </div>
  );
}
