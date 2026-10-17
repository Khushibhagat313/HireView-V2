import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, COMPANY_NAME } from "../lib/api";
import { SAMPLE_JD } from "../lib/sampleJd";
import { ArrowRight, DocIcon } from "./Icons";
import { ErrorLine } from "./Note";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onRank: () => void;
  onCancel?: () => void;
  ranking: boolean;
  error: string | null;
}

export const MOD_KEY = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";

export function JobInput({ value, onChange, onRank, onCancel, ranking, error }: Props) {
  const empty = !value.trim();
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  const pool = useQuery({ queryKey: ["resumes"], queryFn: api.resumes });
  const people = pool.data ? new Set(pool.data.map((r) => r.candidate_id)).size : 0;

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_288px] lg:gap-12">
      <form
        className="grid min-w-0 content-start gap-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (!empty && !ranking) onRank();
        }}
      >
        <div className="settle grid gap-3">
          <span className="eyebrow">{onCancel ? "Edit ranking" : "New ranking"}</span>
          <h1 className="font-serif text-[36px] leading-[1.08] font-semibold tracking-[-0.022em] sm:text-[44px]">
            Paste the <span className="hl-title">job description</span>
          </h1>
          <p className="max-w-[60ch] text-[15.5px] text-pencil">
            HireView reads it, ranks every resume in your pool against it, and marks up exactly why each person lands where they do.
          </p>
        </div>

        <div className="sheet sheet-raised settle overflow-hidden transition-shadow focus-within:shadow-[0_0_0_3px_var(--ring),var(--shadow-md)]" style={{ ["--d" as string]: "80ms" }}>
          <div className="flex h-12 items-center justify-between gap-3 border-b border-rule px-4">
            <label htmlFor="jd" className="flex items-center gap-2 text-[13px] font-medium whitespace-nowrap text-pencil">
              <DocIcon size={15} /> Job description
            </label>
            <div className="flex items-center gap-1">
              {words > 0 && <span className="mr-2 hidden text-xs text-pencil tabular-nums sm:inline">{words} words</span>}
              {!empty && (
                <button type="button" className="btn btn-quiet btn-sm" onClick={() => onChange("")} disabled={ranking}>
                  Clear
                </button>
              )}
              <button type="button" className="btn btn-quiet btn-sm" onClick={() => onChange(SAMPLE_JD)} disabled={ranking}>
                Use sample job
              </button>
            </div>
          </div>
          <textarea
            id="jd"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !empty && !ranking) onRank();
            }}
            placeholder={"Junior Backend Developer\n\nRequirements:\n- Python and FastAPI\n- ..."}
            rows={12}
            className="legal block min-h-[340px] w-full resize-y text-[15.5px] text-ink placeholder:text-pencil placeholder:opacity-45 focus:outline-none"
          />
          <div className="flex flex-wrap items-center gap-3 border-t border-rule bg-sheet-2 px-4 py-3">
            <span className="text-[12.5px] text-pencil">
              Ranks against {pool.data ? `all ${pool.data.length} resumes` : "every resume"} in {COMPANY_NAME}
            </span>
            <div className="ml-auto flex items-center gap-2">
              {onCancel && (
                <button type="button" className="btn btn-quiet" onClick={onCancel} disabled={ranking}>
                  Back to results
                </button>
              )}
              <button type="submit" className="btn" disabled={empty || ranking}>
                {ranking ? "Ranking…" : "Rank candidates"}
                {!ranking && <span className="kbd">{MOD_KEY} ↵</span>}
              </button>
            </div>
          </div>
        </div>

        {ranking && <RankingProgress />}
        {error && <ErrorLine message={error} onRetry={onRank} />}
      </form>

      <aside className="grid content-start gap-4" aria-label="How to read the results">
        <div className="sheet settle grid gap-5 p-5" style={{ ["--d" as string]: "160ms" }}>
          <span className="eyebrow">How to read the marks</span>
          <dl className="grid gap-4 text-[14px]">
            <div className="grid gap-1">
              <dt>
                <span className="hl">Python</span>
              </dt>
              <dd className="text-[13.5px] text-pencil">Has a skill the job requires.</dd>
            </div>
            <div className="grid gap-1">
              <dt>
                <span className="struck">Kubernetes</span>
              </dt>
              <dd className="text-[13.5px] text-pencil">Required, but not on the resume.</dd>
            </div>
            <div className="grid gap-2">
              <dt>
                <span className="mark mark-strong text-[15px]">Strong</span>
              </dt>
              <dd className="text-[13.5px] text-pencil">The match label, Exceptional down to Weak. It leads; the score out of 100 is secondary.</dd>
            </div>
          </dl>
        </div>

        <a href="#pool" className="sheet row settle group grid gap-1 overflow-hidden p-5" style={{ ["--d" as string]: "220ms" }}>
          <span className="eyebrow">Your pool</span>
          {pool.data ? (
            <span className="flex items-baseline gap-2">
              <span className="font-serif text-[34px] leading-none font-semibold tabular-nums">{pool.data.length}</span>
              <span className="text-[13.5px] text-pencil">
                {pool.data.length === 1 ? "resume" : "resumes"} · {people} {people === 1 ? "person" : "people"}
              </span>
            </span>
          ) : (
            <span className="skeleton mt-1 h-8 w-32" />
          )}
          <span className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium">
            Manage pool <ArrowRight size={14} className="row-go" />
          </span>
        </a>
      </aside>
    </div>
  );
}

/** Honest progress: elapsed seconds and a preview of where the results will land, no fake percentage. */
function RankingProgress() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, []);
  return (
    <div className="sheet settle grid gap-4 p-5" role="status">
      <div className="flex items-center justify-between gap-3 text-[13.5px]">
        <span className="working text-pencil">Reading the job description and scoring every resume</span>
        <span className="text-pencil tabular-nums">{seconds}s</span>
      </div>
      <div className="progress" aria-hidden="true" />
      <div className="grid gap-4" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center gap-4" style={{ opacity: 1 - i * 0.28 }}>
            <span className="skeleton h-10 w-10 rounded-full" />
            <span className="grid flex-1 gap-2">
              <span className="skeleton h-3.5 w-40" />
              <span className="skeleton h-3 w-64 max-w-full" />
            </span>
            <span className="skeleton h-7 w-24 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
