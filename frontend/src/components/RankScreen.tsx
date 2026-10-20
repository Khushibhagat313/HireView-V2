import { useEffect, useState } from "react";
import type { ChatTurn, Ranking, SearchResult } from "../lib/types";
import { jdTitle, labelTone, personName, requiredSkills, skillName, timeAgo } from "../lib/format";
import { AskPanel } from "./AskPanel";
import { PenIcon, RefreshIcon } from "./Icons";
import { JobInput } from "./JobInput";
import { ResultsList } from "./ResultsList";

interface Props {
  draft: string;
  onDraft: (jd: string) => void;
  ranking: Ranking | null;
  editing: boolean;
  onEdit: (editing: boolean) => void;
  onRank: (jd: string) => void;
  rankPending: boolean;
  rankError: string | null;
  poolChanged: boolean;
  turns: ChatTurn[];
  onAsk: (query: string) => void;
  onClearChat: () => void;
  onOpen: (result: SearchResult) => void;
  selectedId: string | null;
}

export function RankScreen(p: Props) {
  if (!p.ranking || p.editing) {
    return (
      <JobInput
        value={p.draft}
        onChange={p.onDraft}
        onRank={() => p.onRank(p.draft)}
        onCancel={p.ranking ? () => p.onEdit(false) : undefined}
        ranking={p.rankPending}
        error={p.rankError}
      />
    );
  }

  const { ranking } = p;
  const { results } = ranking;
  const required = requiredSkills(results);
  const strong = results.filter((r) => labelTone(r.label) === "strong").length;
  const top = results[0];

  return (
    <div className="grid gap-8">
      <section className="settle flex flex-wrap items-end justify-between gap-x-8 gap-y-5" aria-label="Job being ranked">
        <div className="grid min-w-0 gap-3">
          <span className="eyebrow">
            Ranked <RankedAgo at={ranking.at} />
          </span>
          <h1 className="font-serif text-[34px] leading-[1.1] font-semibold tracking-[-0.022em] sm:text-[40px]">{jdTitle(ranking.jd)}</h1>
          {required.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-[13px] text-pencil">
              <span className="mr-1">Requires</span>
              {required.map((s) => (
                <span key={s} className="tag">
                  {skillName(s)}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className="btn btn-ghost" onClick={() => p.onEdit(true)}>
            <PenIcon size={15} /> Edit job
          </button>
          <button type="button" className="btn btn-ghost btn-icon" onClick={() => p.onRank(ranking.jd)} disabled={p.rankPending} aria-label="Rank again" title="Rank again">
            <RefreshIcon size={15} className={p.rankPending ? "animate-spin" : ""} />
          </button>
        </div>
      </section>

      {results.length > 0 && (
        <dl className="settle grid grid-cols-3 overflow-hidden rounded-[14px] border border-rule bg-sheet shadow-[var(--inset),var(--shadow-sm)]" style={{ ["--d" as string]: "60ms" }}>
          <Stat term="Ranked" value={String(results.length)} note={results.length === 1 ? "candidate" : "candidates"} />
          <Stat term="Shortlist" value={String(strong)} note="strong or better" />
          <Stat term="Top match" value={top ? String(Math.round(top.display_score)) : "–"} note={top ? personName(top.candidate_name) : ""} />
        </dl>
      )}

      {p.poolChanged && (
        <p className="settle flex flex-wrap items-center gap-3 rounded-xl border border-[color-mix(in_srgb,var(--red)_25%,transparent)] bg-red-wash px-4 py-3 text-[14px]">
          <span className="hand text-[15px]">Heads up:</span>
          Resumes were added or removed since this ranking.
          <button type="button" className="btn btn-ghost btn-sm ml-auto" onClick={() => p.onRank(ranking.jd)} disabled={p.rankPending}>
            <RefreshIcon size={14} className={p.rankPending ? "animate-spin" : ""} />
            {p.rankPending ? "Re-ranking…" : "Re-rank"}
          </button>
        </p>
      )}
      {p.rankError && <p className="text-sm text-red">{p.rankError}</p>}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        {/* keyed by ranking time, so a new ranking starts with every label shown again */}
        <ResultsList key={ranking.at} results={results} onOpen={p.onOpen} selectedId={p.selectedId} />
        <div className="lg:sticky lg:top-24">
          <AskPanel results={results} turns={p.turns} onAsk={p.onAsk} onClear={p.onClearChat} onOpen={p.onOpen} />
        </div>
      </div>
    </div>
  );
}

/** Re-renders every half minute so "5 min ago" stays true. */
function RankedAgo({ at }: { at: number }) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(t);
  }, []);
  return <time dateTime={new Date(at).toISOString()}>{timeAgo(at, now)}</time>;
}

function Stat({ term, value, note }: { term: string; value: string; note: string }) {
  return (
    <div className="grid min-w-0 gap-1 border-r border-rule px-4 py-4 last:border-r-0 sm:px-6">
      <dt className="eyebrow truncate">{term}</dt>
      <dd className="flex min-w-0 flex-wrap items-baseline gap-x-2">
        <span className="font-serif text-[28px] leading-none font-semibold tabular-nums">{value}</span>
        <span className="truncate text-[13px] text-pencil">{note}</span>
      </dd>
    </div>
  );
}
