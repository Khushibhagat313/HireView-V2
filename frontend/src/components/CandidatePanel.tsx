import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, messageFor } from "../lib/api";
import type { SearchResult } from "../lib/types";
import { FACETS, duration, latestRole, personName, skillName } from "../lib/format";
import { copyText, useToast } from "../lib/toast";
import { ChevronLeft, ChevronRight, CloseIcon, CopyIcon, MailIcon, PenIcon, PhoneIcon, QuestionIcon } from "./Icons";
import { LabelMark, Monogram, ScoreMeter } from "./Marks";
import { ErrorLine, Note, WritingSkeleton } from "./Note";

interface Props {
  result: SearchResult;
  rank: number | null;
  total: number;
  jd: string;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
}

const isTyping = (el: Element | null) => el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;

export function CandidatePanel({ result, rank, total, jd, onClose, onPrev, onNext }: Props) {
  const toast = useToast();
  const bodyRef = useRef<HTMLElement>(null);
  const [showExplain, setShowExplain] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [allSkills, setAllSkills] = useState(false);
  const id = result.candidate_id;

  // Reset the per-candidate toggles when a different candidate is opened.
  useEffect(() => {
    setShowExplain(false);
    setShowGuide(false);
    setAllSkills(false);
    bodyRef.current?.scrollTo({ top: 0 });
    bodyRef.current?.focus({ preventScroll: true });
  }, [id]);

  // Give focus back to whatever opened the panel (usually the ranked row) when it closes.
  const returnTo = useRef<Element | null>(document.activeElement);
  useEffect(() => {
    const target = returnTo.current;
    return () => {
      if (target instanceof HTMLElement && target.isConnected) target.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      // Keep Tab inside the panel while it's open.
      if (e.key === "Tab" && bodyRef.current) {
        const focusable = [...bodyRef.current.querySelectorAll<HTMLElement>("a[href], button:not(:disabled), input, textarea, [tabindex='0']")];
        if (!focusable.length) return;
        // -1 when focus is on the panel itself or somewhere outside it.
        const at = focusable.indexOf(document.activeElement as HTMLElement);
        if (e.shiftKey && at <= 0) {
          e.preventDefault();
          focusable[focusable.length - 1].focus();
        } else if (!e.shiftKey && (at === -1 || at === focusable.length - 1)) {
          e.preventDefault();
          focusable[0].focus();
        }
        return;
      }
      if (isTyping(document.activeElement)) return;
      if (e.key === "ArrowLeft" && onPrev) onPrev();
      if (e.key === "ArrowRight" && onNext) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onPrev, onNext]);

  // Keep the page behind the panel still.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const profile = useQuery({ queryKey: ["candidate", id], queryFn: () => api.candidate(id), retry: false });
  const explain = useQuery({
    // The label is in the key: after a re-rank it can change, and the explanation names it.
    queryKey: ["feedback", id, jd, result.label],
    queryFn: () => api.feedback(id, jd),
    enabled: showExplain,
    staleTime: Infinity,
    retry: false,
  });
  const guide = useQuery({
    queryKey: ["guide", id, jd],
    queryFn: () => api.interviewGuide(id, jd),
    enabled: showGuide,
    staleTime: Infinity,
    retry: false,
  });

  const name = personName(result.candidate_name);
  const gone = profile.error instanceof ApiError && profile.error.status === 404;
  const copy = async (text: string, done: string) => toast((await copyText(text)) ? done : "Couldn't copy. Select the text instead.");

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="panel-name">
      <button type="button" tabIndex={-1} aria-label="Close candidate" className="scrim absolute inset-0 cursor-default bg-[var(--scrim)]" onClick={onClose} />
      <article ref={bodyRef} tabIndex={-1} className="drawer relative outline-none flex h-full w-full max-w-[600px] flex-col overflow-y-auto border-l border-rule bg-paper shadow-[var(--shadow-lg)]">
        <div className="sticky top-0 z-10 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-rule bg-[color-mix(in_srgb,var(--paper)_88%,transparent)] px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-1">
            <button type="button" className="btn btn-quiet btn-icon btn-sm" onClick={onPrev} disabled={!onPrev} aria-label="Previous candidate" title="Previous (←)">
              <ChevronLeft />
            </button>
            <button type="button" className="btn btn-quiet btn-icon btn-sm" onClick={onNext} disabled={!onNext} aria-label="Next candidate" title="Next (→)">
              <ChevronRight />
            </button>
            {rank && (
              <span className="ml-2 text-[13px] text-pencil tabular-nums">
                Candidate {rank} of {total}
              </span>
            )}
          </div>
          <button type="button" onClick={onClose} className="btn btn-ghost btn-icon btn-sm" aria-label="Close" title="Close (Esc)">
            <CloseIcon size={15} />
          </button>
        </div>

        <div key={id} className="grid gap-9 px-5 pt-7 pb-12 sm:px-8">
          <section className="settle flex items-start gap-4">
            <Monogram name={result.candidate_name} size={60} />
            <div className="grid min-w-0 gap-1.5">
              <h2 id="panel-name" className="font-serif text-[30px] leading-[1.1] font-semibold tracking-[-0.02em]">
                {name}
              </h2>
              <p className="text-[14px] text-pencil">{latestRole(result) ?? "No work experience listed"}</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[13px]">
                {profile.isPending && <span className="skeleton h-8 w-56 rounded-full" />}
                {gone && <span className="text-red">This candidate is no longer in the pool.</span>}
                {profile.data && (
                  <>
                    <span className="inline-flex h-8 max-w-full items-center gap-1 rounded-full border border-rule bg-sheet pr-1 pl-3 shadow-[var(--shadow-sm)]">
                      <MailIcon size={14} className="shrink-0 text-pencil" />
                      <a href={`mailto:${profile.data.email}`} className="ml-1 truncate underline-offset-3 hover:underline" title="Write an email">
                        {profile.data.email}
                      </a>
                      <button type="button" className="btn btn-quiet btn-icon h-6 w-6 rounded-full" onClick={() => copy(profile.data.email, "Email copied")} aria-label="Copy email" title="Copy email">
                        <CopyIcon size={13} />
                      </button>
                    </span>
                    {profile.data.phone && (
                      <span className="inline-flex h-8 items-center gap-2 rounded-full border border-rule bg-sheet px-3 shadow-[var(--shadow-sm)] tabular-nums">
                        <PhoneIcon size={14} className="text-pencil" />
                        {profile.data.phone}
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          </section>

          <section className="sheet settle grid gap-4 p-5" style={{ ["--d" as string]: "60ms" }} aria-label="Match">
            <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
              <div className="grid gap-2">
                <span className="eyebrow">Match</span>
                <LabelMark label={result.label} size="lg" />
              </div>
              <div className="grid justify-items-end gap-1.5">
                <ScoreMeter score={result.display_score} width="w-40" delay={200} />
                {rank && (
                  <span className="text-[12.5px] text-pencil">
                    Ranked #{rank} of {total}
                  </span>
                )}
              </div>
            </div>
            {result.limited_data && (
              <p className="border-t border-dashed border-rule pt-3 text-[14px]">
                <span className="hand">Thin resume:</span> <span className="text-pencil">this ranking rests on very little information.</span>
              </p>
            )}
          </section>

          <Section title="Where the score comes from" delay={120}>
            <ul className="grid gap-3.5">
              {FACETS.map(({ key, name: facet }, i) => {
                const value = result.facet_scores[key];
                const present = typeof value === "number";
                const pct = present ? Math.max(0, Math.min(1, value)) * 100 : 0;
                return (
                  <li key={key} className="grid grid-cols-[minmax(0,12rem)_minmax(0,1fr)_2rem] items-center gap-4 text-[13.5px]">
                    <span className={present ? "" : "text-pencil"}>{facet}</span>
                    {present ? (
                      <span className="meter">
                        <span style={{ width: `${pct}%`, ["--d" as string]: `${250 + i * 70}ms` }} />
                      </span>
                    ) : (
                      <span className="text-[12.5px] text-pencil italic">not on resume</span>
                    )}
                    <span className="text-right font-medium tabular-nums">{present ? Math.round(pct) : ""}</span>
                  </li>
                );
              })}
            </ul>
          </Section>

          <Section title="Skills against this job" delay={180}>
            <dl className="grid gap-3 text-[14px]">
              <SkillRow term="Has · required" items={result.matched_required} kind="hl" empty="None of the required skills" />
              <SkillRow term="Missing · required" items={result.missing_required} kind="struck" empty="Nothing missing" />
              <SkillRow term="Has · preferred" items={result.matched_preferred} kind="plain" empty="None of the preferred skills" />
            </dl>
            {result.skills.length > 0 && (
              <div className="grid gap-3">
                <button type="button" className="btn-text justify-self-start" onClick={() => setAllSkills((v) => !v)} aria-expanded={allSkills}>
                  {allSkills ? "Hide full skill list" : `Show all ${result.skills.length} skills on the resume`}
                </button>
                {allSkills && (
                  <div className="settle flex flex-wrap gap-1.5">
                    {result.skills.map((s) => (
                      <span key={s} className="tag">
                        {skillName(s)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Section>

          <Section title="Experience" delay={240}>
            {result.work_experience.length ? (
              <ol className="grid">
                {result.work_experience.map((w, i) => (
                  <li key={i} className="relative grid grid-cols-[1rem_minmax(0,1fr)_auto] gap-3 pb-4 last:pb-0">
                    <span className="relative flex justify-center pt-1.5">
                      <span className={`z-[1] h-2.5 w-2.5 rounded-full border-2 ${i === 0 ? "border-red bg-red" : "border-rule-strong bg-paper"}`} />
                      {i < result.work_experience.length - 1 && <span className="absolute top-4 -bottom-4 w-px bg-rule-strong" />}
                    </span>
                    <span className="text-[14.5px] font-medium">{w.title}</span>
                    <span className="text-[13px] text-pencil tabular-nums">{duration(w.duration_years)}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-pencil">No work experience listed. Fine for a fresher role.</p>
            )}
          </Section>

          <section className="settle grid gap-4 border-t border-rule pt-8" style={{ ["--d" as string]: "300ms" }}>
            <span className="eyebrow">Go deeper</span>
            <div className="grid gap-3 sm:grid-cols-2">
              <ActionCard
                icon={<PenIcon size={17} />}
                title="Explain this match"
                note="A plain-language case for and against"
                active={showExplain}
                onClick={() => setShowExplain(true)}
                disabled={showExplain && !explain.isError}
              />
              <ActionCard
                icon={<QuestionIcon size={17} />}
                title="Interview questions"
                note="Built from the resume and its gaps"
                active={showGuide}
                onClick={() => setShowGuide(true)}
                disabled={showGuide && !guide.isError}
              />
            </div>

            {showExplain && (
              <AiSheet title={`Why ${result.label}`} onCopy={explain.data ? () => copy(explain.data, "Explanation copied") : undefined}>
                {explain.isPending && <WritingSkeleton caption="Writing the explanation" />}
                {explain.isError && <ErrorLine message={messageFor(explain.error)} onRetry={() => explain.refetch()} />}
                {explain.data && <Note text={explain.data} />}
              </AiSheet>
            )}

            {showGuide && (
              <AiSheet title="Interview questions" onCopy={guide.data ? () => copy(guide.data, "Questions copied") : undefined}>
                {guide.isPending && <WritingSkeleton caption="Writing questions from the resume and its gaps" lines={5} />}
                {guide.isError && <ErrorLine message={messageFor(guide.error)} onRetry={() => guide.refetch()} />}
                {guide.data && <Note text={guide.data} />}
              </AiSheet>
            )}
          </section>
        </div>
      </article>
    </div>
  );
}

function Section({ title, delay, children }: { title: string; delay: number; children: ReactNode }) {
  return (
    <section className="settle grid gap-4" style={{ ["--d" as string]: `${delay}ms` }} aria-label={title}>
      <h3 className="eyebrow">{title}</h3>
      {children}
    </section>
  );
}

function ActionCard(props: { icon: ReactNode; title: string; note: string; active: boolean; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={props.disabled}
      aria-pressed={props.active}
      className="sheet row grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-0.5 p-4 text-left disabled:cursor-default aria-pressed:border-rule-strong"
    >
      <span className="row-span-2 grid h-9 w-9 place-items-center rounded-lg border border-rule bg-sheet-2 text-red">{props.icon}</span>
      <span className="text-[14.5px] font-semibold">{props.title}</span>
      <span className="text-[12.5px] text-pencil">{props.note}</span>
    </button>
  );
}

function AiSheet({ title, onCopy, children }: { title: string; onCopy?: () => void; children: ReactNode }) {
  return (
    <div className="sheet settle grid gap-4 p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="eyebrow">{title}</h3>
        {onCopy && (
          <button type="button" className="btn btn-quiet btn-sm -my-1 -mr-2" onClick={onCopy}>
            <CopyIcon size={13} /> Copy
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

function SkillRow({ term, items, kind, empty }: { term: string; items: string[]; kind: "hl" | "struck" | "plain"; empty: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,9.5rem)_minmax(0,1fr)] gap-3">
      <dt className="text-[13px] text-pencil">{term}</dt>
      <dd className="flex flex-wrap gap-x-2.5 gap-y-1.5">
        {items.length ? (
          items.map((s) => (
            <span key={s} className={kind === "plain" ? "font-medium" : kind}>
              {skillName(s)}
            </span>
          ))
        ) : (
          <span className="text-pencil">{empty}</span>
        )}
      </dd>
    </div>
  );
}
