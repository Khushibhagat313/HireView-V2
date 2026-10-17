import { useMemo, useState } from "react";
import type { Label, SearchResult } from "../lib/types";
import { LABELS } from "../lib/types";
import { labelTone, latestRole, personName, skillName } from "../lib/format";
import { ChevronRight } from "./Icons";
import { LabelMark, Monogram, RequiredSkills, ScoreMeter } from "./Marks";

interface Props {
  results: SearchResult[];
  onOpen: (result: SearchResult) => void;
  selectedId: string | null;
}

/** The marks are visual (highlight, strikethrough), so spell them out for screen readers. */
function rowLabel(rank: number, name: string, r: SearchResult): string {
  const parts = [`${rank}. ${name}`, r.label, `${Math.round(r.display_score)} out of 100`];
  if (r.matched_required.length) parts.push(`has ${r.matched_required.map(skillName).join(", ")}`);
  if (r.missing_required.length) parts.push(`missing ${r.missing_required.map(skillName).join(", ")}`);
  if (r.limited_data) parts.push("thin resume");
  return parts.join(". ");
}

export function ResultsList({ results, onOpen, selectedId }: Props) {
  const [hidden, setHidden] = useState<Set<Label>>(new Set());
  const counts = useMemo(() => {
    const c = new Map<Label, number>();
    results.forEach((r) => c.set(r.label, (c.get(r.label) ?? 0) + 1));
    return c;
  }, [results]);
  const visible = results.filter((r) => !hidden.has(r.label));

  if (!results.length) {
    return (
      <div className="sheet grid justify-items-start gap-3 px-7 py-10">
        <span className="hand text-[17px]">Nobody made the cut.</span>
        <p className="font-serif text-[20px] leading-snug font-medium">No one in the pool passed this job's requirements.</p>
        <p className="max-w-[60ch] text-pencil">
          Candidates are left out when they miss a hard requirement (such as graduation year or minimum experience) or score below 30.
        </p>
        <a href="#pool" className="btn btn-ghost mt-2">
          Open the resume pool
        </a>
      </div>
    );
  }

  const toggle = (label: Label) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });

  return (
    <div className="grid min-w-0 gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-1 text-[13px] text-pencil">Show</span>
        {LABELS.filter((l) => counts.has(l)).map((label) => (
          <button key={label} type="button" className="chip" aria-pressed={!hidden.has(label)} onClick={() => toggle(label)}>
            {label} <span className="chip-count">{counts.get(label)}</span>
          </button>
        ))}
      </div>

      <ol className="sheet sheet-raised divide-y divide-rule overflow-hidden" aria-label="Ranked candidates">
        {visible.map((r, i) => {
          const rank = results.indexOf(r) + 1;
          const name = personName(r.candidate_name);
          return (
            <li key={r.resume_id} className="settle" style={{ ["--d" as string]: `${Math.min(i, 8) * 60}ms` }}>
              <button
                type="button"
                onClick={() => onOpen(r)}
                aria-current={selectedId === r.candidate_id ? "true" : undefined}
                aria-label={rowLabel(rank, name, r)}
                className="row grid w-full grid-cols-[1.75rem_minmax(0,1fr)] items-start gap-x-3 gap-y-3 px-4 py-5 text-left sm:grid-cols-[2rem_2.75rem_minmax(0,1fr)_auto_1rem] sm:items-center sm:gap-x-4 sm:px-6"
              >
                <span className="pt-1 font-serif text-[20px] leading-none text-pencil italic tabular-nums sm:pt-0">{rank}</span>
                <span className="hidden sm:block">
                  <Monogram name={r.candidate_name} size={44} />
                </span>
                <span className="grid min-w-0 gap-1">
                  <span className="flex flex-wrap items-baseline gap-x-3">
                    <span className="font-serif text-[20px] leading-snug font-semibold tracking-[-0.01em]">{name}</span>
                    {rank === 1 && labelTone(r.label) === "strong" && <span className="hand -rotate-2 text-[13.5px]">top pick</span>}
                  </span>
                  <span className="text-[13px] text-pencil">
                    {latestRole(r) ?? "No work experience listed"}
                    {r.limited_data && <span className="hand ml-2 text-[13px]">thin resume</span>}
                  </span>
                  <span className="mt-1.5">
                    <RequiredSkills result={r} animate />
                  </span>
                </span>
                <span className="col-start-2 flex items-center gap-5 sm:col-start-auto sm:pl-2">
                  <LabelMark label={r.label} />
                  <ScoreMeter score={r.display_score} delay={200 + Math.min(i, 8) * 60} />
                </span>
                <ChevronRight size={16} className="row-go hidden text-pencil sm:block" />
              </button>
            </li>
          );
        })}
      </ol>
      {visible.length === 0 && <p className="text-sm text-pencil">Every label is filtered out. Click a label above to show it again.</p>}
    </div>
  );
}
