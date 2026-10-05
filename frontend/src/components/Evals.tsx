import { useEffect, useState } from "react";
import { fetchEvals } from "../api/client";
import type { EvalResults } from "../api/types";

type Load = { state: "loading" } | { state: "missing" } | { state: "error" } | { state: "ready"; results: EvalResults };

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="paper px-5 py-4">
      <p className="font-mono text-[11px] tracking-[0.25em] text-carbon uppercase">{label}</p>
      <p className="tabular mt-2 text-5xl">{value}</p>
      <p className="mt-1 text-sm text-carbon">{detail}</p>
    </div>
  );
}

export function Evals() {
  const [load, setLoad] = useState<Load>({ state: "loading" });

  useEffect(() => {
    fetchEvals()
      .then((results) => setLoad(results ? { state: "ready", results } : { state: "missing" }))
      .catch(() => setLoad({ state: "error" }));
  }, []);

  return (
    <section aria-labelledby="evals-title" className="mx-auto max-w-[880px]">
      <h2 id="evals-title" className="font-display text-5xl italic">
        Benchmarks, printed in public
      </h2>
      <p className="mt-2 max-w-prose text-carbon">
        A frozen set of real shopper phrasings checks that each message reaches the right skill, and a red-team set
        checks that prompt-injection attempts are refused.
      </p>
      <div className="mt-6">
        {load.state === "loading" ? <p className="font-mono text-sm text-carbon">Loading results...</p> : null}
        {load.state === "missing" ? (
          <p className="font-mono text-sm text-carbon">No benchmark run has been published yet.</p>
        ) : null}
        {load.state === "error" ? (
          <p role="alert" className="font-mono text-sm text-stamp">
            Results could not be loaded.
          </p>
        ) : null}
        {load.state === "ready" ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <Metric
                label="Skill routing accuracy"
                value={`${(load.results.routing.accuracy * 100).toFixed(1)}%`}
                detail={`${load.results.routing.correct} of ${load.results.routing.cases} phrasings routed correctly`}
              />
              <Metric
                label="Injection attempts refused"
                value={`${load.results.injection.blocked}/${load.results.injection.cases}`}
                detail="Adversarial prompts flagged as off-topic before any tool runs"
              />
            </div>
            {Object.keys(load.results.routing.failures).length > 0 ? (
              <div className="paper mt-4 px-5 py-4 font-mono text-sm">
                <p className="text-[11px] tracking-[0.25em] text-carbon uppercase">Misroutes</p>
                <ul className="mt-2 space-y-1">
                  {Object.entries(load.results.routing.failures).map(([pair, count]) => (
                    <li key={pair} className="flex items-baseline">
                      <span>{pair.replace("->", " routed as ")}</span>
                      <span aria-hidden className="leader" />
                      <span className="tabular">{count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="mt-4 font-mono text-[11px] text-carbon">
              Model {load.results.model}, run {new Date(load.results.run_at).toLocaleString()}
            </p>
          </>
        ) : null}
      </div>
    </section>
  );
}
