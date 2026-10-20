import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatTurn, SearchResult } from "../lib/types";
import { personName, skillName } from "../lib/format";
import { ArrowRight, ArrowUp } from "./Icons";
import { LabelMark, Monogram } from "./Marks";
import { ErrorLine, Note, WritingSkeleton } from "./Note";

interface Props {
  results: SearchResult[];
  turns: ChatTurn[];
  onAsk: (query: string) => void;
  onClear: () => void;
  onOpen: (result: SearchResult) => void;
}

function suggestionsFor(results: SearchResult[]): string[] {
  const names = results.map((r) => personName(r.candidate_name));
  const skill =
    results.flatMap((r) => r.matched_preferred)[0] ??
    results.flatMap((r) => [...r.matched_required, ...r.missing_required])[0];
  const list = ["Show me the top 3"];
  if (skill) list.push(`Who knows ${skillName(skill)}?`);
  list.push("Any hidden gems?");
  if (names.length >= 2) list.push(`Compare ${names[0]} and ${names[1]}`);
  if (names.length >= 1) list.push(`Interview questions for ${names[0]}`);
  if (names.length >= 2) list.push(`Why is ${names[names.length - 1]} ranked low?`);
  return list;
}

const isTyping = (el: Element | null) => el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || (el as HTMLElement | null)?.isContentEditable;

export function AskPanel({ results, turns, onAsk, onClear, onOpen }: Props) {
  const [query, setQuery] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestions = useMemo(() => suggestionsFor(results), [results]);
  const busy = turns.some((t) => t.status === "pending");

  // Scroll only the conversation box; scrollIntoView would also drag the whole page down to the panel.
  useEffect(() => {
    const el = listRef.current;
    if (el && turns.length) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [turns]);

  // "/" jumps to the question box from anywhere on the results screen.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || isTyping(document.activeElement)) return;
      if (document.querySelector('[role="dialog"]')) return;
      e.preventDefault();
      inputRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const send = (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    onAsk(q);
    setQuery("");
  };

  return (
    <section className="sheet sheet-raised settle flex max-h-[calc(100vh-8rem)] min-w-0 flex-col overflow-hidden lg:min-h-[460px]" style={{ ["--d" as string]: "120ms" }} aria-labelledby="ask-title">
      <header className="flex items-start justify-between gap-3 border-b border-rule px-5 pt-4 pb-3.5">
        <div className="grid gap-0.5">
          <h2 id="ask-title" className="font-serif text-[18px] font-semibold tracking-[-0.01em]">
            Ask about these candidates
          </h2>
          <p className="text-[12.5px] text-pencil">Each question is answered on its own, without memory of earlier ones.</p>
        </div>
        {turns.length > 0 && (
          <button type="button" className="btn btn-quiet btn-sm -mr-2" onClick={onClear}>
            Clear
          </button>
        )}
      </header>

      <div ref={listRef} className="grid min-h-0 flex-1 content-start gap-6 overflow-y-auto px-5 py-5">
        {turns.length === 0 && (
          <div className="grid gap-2">
            <span className="eyebrow">Try asking</span>
            <ul className="-mx-2 grid">
              {suggestions.map((s, i) => (
                <li key={s} className="settle" style={{ ["--d" as string]: `${200 + i * 40}ms` }}>
                  <button
                    type="button"
                    className="row group flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-[14px]"
                    onClick={() => send(s)}
                  >
                    {s}
                    <ArrowRight size={14} className="row-go shrink-0 text-pencil" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {turns.map((t) => (
          <div key={t.id} className="settle grid gap-3">
            <p className="max-w-[85%] justify-self-end rounded-2xl rounded-br-md bg-ink px-3.5 py-2 text-[14px] text-paper shadow-[var(--shadow-sm)]">{t.query}</p>
            <div className="grid gap-2">
              {t.status === "pending" && <WritingSkeleton caption="Thinking" lines={3} />}
              {t.status === "error" && <ErrorLine message={t.error ?? "Something went wrong."} onRetry={() => onAsk(t.query)} />}
              {t.status === "done" && t.response && <Answer response={t.response} onOpen={onOpen} />}
            </div>
          </div>
        ))}
      </div>

      <form
        className="border-t border-rule bg-sheet-2 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(query);
        }}
      >
        <label htmlFor="ask" className="sr-only">
          Question
        </label>
        <div className="relative">
          <input
            ref={inputRef}
            id="ask"
            className="field h-11 pr-12"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question…"
            autoComplete="off"
            maxLength={500}
          />
          {!query && <span className="kbd pointer-events-none absolute top-1/2 right-12 -translate-y-1/2">/</span>}
          <button
            type="submit"
            className="btn btn-icon btn-sm absolute top-1/2 right-1.5 -translate-y-1/2 rounded-lg"
            disabled={!query.trim() || busy}
            aria-label="Ask"
          >
            <ArrowUp size={15} />
          </button>
        </div>
      </form>
    </section>
  );
}

function Answer({ response, onOpen }: { response: NonNullable<ChatTurn["response"]>; onOpen: (r: SearchResult) => void }) {
  if (response.response_candidates) {
    const list = response.response_candidates;
    if (!list.length) {
      // The backend now explains empty answers in response_text; this covers an older server.
      return <p className="text-[14px] text-pencil">No matching candidates.</p>;
    }
    return (
      <ul className="-mx-2 grid gap-0.5">
        {list.map((r) => (
          <li key={r.resume_id}>
            <button type="button" onClick={() => onOpen(r)} className="row flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left">
              <Monogram name={r.candidate_name} size={30} />
              <span className="min-w-0 flex-1 truncate font-serif text-[15px] font-semibold">{personName(r.candidate_name)}</span>
              <LabelMark label={r.label} size="sm" />
            </button>
          </li>
        ))}
      </ul>
    );
  }
  return <Note text={response.response_text ?? "No answer came back."} serif={false} />;
}
