import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, getAccessCode, LOCKED_EVENT, messageFor } from "./lib/api";
import type { ChatTurn, Ranking, SearchResult } from "./lib/types";
import { jdTitle, personName } from "./lib/format";
import { AccessGate } from "./components/AccessGate";
import { CandidatePanel } from "./components/CandidatePanel";
import { Header, type ServerState, type Tab } from "./components/Header";
import { PoolScreen } from "./components/PoolScreen";
import { RankScreen } from "./components/RankScreen";
import { useTheme } from "./lib/theme";

const DRAFT_KEY = "hireview.jdDraft";

function readDraft(): string {
  try {
    return localStorage.getItem(DRAFT_KEY) ?? "";
  } catch {
    return "";
  }
}

// The last ranking lives for the browser tab's session, so a refresh doesn't throw it away.
const RANKING_KEY = "hireview.ranking";

function readRanking(): { ranking: Ranking | null; poolChanged: boolean } {
  try {
    const saved = JSON.parse(sessionStorage.getItem(RANKING_KEY) ?? "null");
    if (saved && typeof saved.jd === "string" && Array.isArray(saved.results)) {
      return { ranking: { jd: saved.jd, results: saved.results, at: Number(saved.at) || Date.now() }, poolChanged: Boolean(saved.poolChanged) };
    }
  } catch {
    /* nothing saved, or storage blocked */
  }
  return { ranking: null, poolChanged: false };
}

const tabFromHash = (): Tab => (window.location.hash === "#pool" ? "pool" : "rank");

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromHash);
  const [locked, setLocked] = useState(false);
  const [draft, setDraft] = useState(readDraft);
  const [saved] = useState(readRanking);
  const [ranking, setRanking] = useState<Ranking | null>(saved.ranking);
  const [editing, setEditing] = useState(false);
  const [rankPending, setRankPending] = useState(false);
  const [rankError, setRankError] = useState<string | null>(null);
  const [poolChanged, setPoolChanged] = useState(saved.poolChanged);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const turnId = useRef(1);
  const { theme, cycle: cycleTheme } = useTheme();

  // The backend scales to zero when idle, so the first call can take a while: retry patiently.
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 6, retryDelay: 4000, refetchOnWindowFocus: false });
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!health.isPending) return;
    const t = window.setTimeout(() => setSlow(true), 2500);
    return () => window.clearTimeout(t);
  }, [health.isPending]);
  const server: ServerState = health.isSuccess ? "ready" : health.isError ? "down" : slow ? "waking" : "checking";

  useEffect(() => {
    if (health.data?.access_code_required && !getAccessCode()) setLocked(true);
  }, [health.data]);

  // A file dropped outside the Pool's drop target would make the browser open it and lose the page.
  useEffect(() => {
    const stop = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes("Files")) e.preventDefault();
    };
    window.addEventListener("dragover", stop);
    window.addEventListener("drop", stop);
    return () => {
      window.removeEventListener("dragover", stop);
      window.removeEventListener("drop", stop);
    };
  }, []);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    const onLocked = () => setLocked(true);
    window.addEventListener("hashchange", onHash);
    window.addEventListener(LOCKED_EVENT, onLocked);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener(LOCKED_EVENT, onLocked);
    };
  }, []);

  useEffect(() => {
    try {
      if (ranking) sessionStorage.setItem(RANKING_KEY, JSON.stringify({ ...ranking, poolChanged }));
      else sessionStorage.removeItem(RANKING_KEY);
    } catch {
      /* keep it in memory only */
    }
  }, [ranking, poolChanged]);

  const updateDraft = (jd: string) => {
    setDraft(jd);
    try {
      localStorage.setItem(DRAFT_KEY, jd);
    } catch {
      /* keep the draft in memory only */
    }
  };

  const rank = async (jd: string) => {
    setRankPending(true);
    setRankError(null);
    try {
      void import("./components/Markdown"); // warm up for the AI answers that usually follow
      const results = await api.search(jd);
      setRanking({ jd, results, at: Date.now() });
      setEditing(false);
      setPoolChanged(false);
      setTurns([]);
      setSelected(null);
    } catch (err) {
      setRankError(messageFor(err));
    } finally {
      setRankPending(false);
    }
  };

  const ask = (query: string) => {
    if (!ranking) return;
    const id = turnId.current++;
    setTurns((prev) => [...prev, { id, query, status: "pending" }]);
    api
      .chat(ranking.jd, query)
      .then((response) => setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, status: "done", response } : t))))
      .catch((err) => setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, status: "error", error: messageFor(err) } : t))));
  };

  const markPoolChanged = useCallback(() => setPoolChanged(true), []);
  const closePanel = useCallback(() => setSelected(null), []);

  // The open candidate's place in the ranking, so the panel can step through it with ← and →.
  const results = ranking?.results ?? [];
  const index = selected ? results.findIndex((r) => r.candidate_id === selected.candidate_id) : -1;
  const goPrev = useCallback(() => index > 0 && setSelected(results[index - 1]), [index, results]);
  const goNext = useCallback(() => index >= 0 && index < results.length - 1 && setSelected(results[index + 1]), [index, results]);

  useEffect(() => {
    const page = locked
      ? "Access code"
      : tab === "pool"
        ? "Pool"
        : selected
          ? personName(selected.candidate_name)
          : ranking && !editing
            ? jdTitle(ranking.jd)
            : "Rank";
    document.title = `${page} · HireView`;
  }, [locked, tab, selected, ranking, editing]);

  if (locked) return <AccessGate onUnlocked={() => setLocked(false)} />;

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
        className="btn skip-link"
      >
        Skip to content
      </a>
      <Header tab={tab} server={server} onRetry={() => health.refetch()} theme={theme} onTheme={cycleTheme} />
      {server === "waking" && (
        <div className="border-b border-rule bg-red-wash">
          <p className="mx-auto flex max-w-[1240px] items-center gap-3 px-4 py-2.5 text-[13.5px] sm:px-6">
            <span className="hand">One moment:</span>
            <span className="working">Waking the server. The first request after a quiet spell can take up to a minute while the AI models load</span>
          </p>
        </div>
      )}
      <main id="main" tabIndex={-1} className="mx-auto max-w-[1240px] px-4 pt-10 pb-24 sm:px-6 sm:pt-12">
        {tab === "rank" ? (
          <RankScreen
            draft={draft}
            onDraft={updateDraft}
            ranking={ranking}
            editing={editing}
            onEdit={(value) => {
              if (value && ranking) updateDraft(ranking.jd);
              setEditing(value);
            }}
            onRank={rank}
            rankPending={rankPending}
            rankError={rankError}
            poolChanged={poolChanged}
            turns={turns}
            onAsk={ask}
            onClearChat={() => setTurns([])}
            onOpen={setSelected}
            selectedId={selected?.candidate_id ?? null}
          />
        ) : (
          <PoolScreen onPoolChanged={markPoolChanged} />
        )}
      </main>
      {selected && ranking && (
        <CandidatePanel
          result={selected}
          rank={index >= 0 ? index + 1 : null}
          total={results.length}
          jd={ranking.jd}
          onClose={closePanel}
          onPrev={index > 0 ? goPrev : undefined}
          onNext={index >= 0 && index < results.length - 1 ? goNext : undefined}
        />
      )}
    </div>
  );
}
