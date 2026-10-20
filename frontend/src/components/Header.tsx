import { COMPANY_NAME } from "../lib/api";
import type { Theme } from "../lib/theme";
import { BrandMark, MonitorIcon, MoonIcon, SunIcon } from "./Icons";

export type Tab = "rank" | "pool";
export type ServerState = "checking" | "waking" | "ready" | "down";

interface Props {
  tab: Tab;
  server: ServerState;
  onRetry: () => void;
  theme: Theme;
  onTheme: () => void;
  /** Resumes still queued or uploading, shown on the Pool tab so a batch isn't forgotten from the Rank tab. */
  uploadsLeft: number;
}

const THEME_LABEL: Record<Theme, string> = { system: "Theme: match system", light: "Theme: light", dark: "Theme: dark" };

export function Header({ tab, server, onRetry, theme, onTheme, uploadsLeft }: Props) {
  const ThemeIcon = theme === "light" ? SunIcon : theme === "dark" ? MoonIcon : MonitorIcon;
  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-[color-mix(in_srgb,var(--paper)_82%,transparent)] backdrop-blur-md backdrop-saturate-150">
      <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-x-8 px-4 sm:px-6">
        <a href="#rank" className="flex items-center gap-2.5 rounded-md" aria-label="HireView home">
          <BrandMark size={28} />
          <span className="font-serif text-[21px] font-semibold tracking-[-0.015em]">HireView</span>
        </a>
        <nav aria-label="Main" className="flex gap-6 text-[15px]">
          <a href="#rank" className="tab" aria-current={tab === "rank" ? "page" : undefined}>
            Rank
          </a>
          <a href="#pool" className="tab inline-flex items-center gap-1.5" aria-current={tab === "pool" ? "page" : undefined}>
            Pool
            {uploadsLeft > 0 && (
              <span className="chip-count" title={`${uploadsLeft} resume${uploadsLeft === 1 ? "" : "s"} uploading`}>
                {uploadsLeft}
                <span className="sr-only"> uploading</span>
              </span>
            )}
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2 text-[13px] text-pencil">
          <span className="hidden items-center gap-2 rounded-full border border-rule bg-sheet py-1 pr-3 pl-1 shadow-[var(--shadow-sm)] sm:inline-flex">
            <span className="monogram h-6 w-6 text-[11px]" aria-hidden="true">
              {COMPANY_NAME.slice(0, 1)}
            </span>
            <span className="font-medium text-ink">{COMPANY_NAME}</span>
          </span>
          <ServerStatus server={server} onRetry={onRetry} />
          <button type="button" className="btn btn-quiet btn-icon btn-sm" onClick={onTheme} aria-label={THEME_LABEL[theme]} title={THEME_LABEL[theme]}>
            <ThemeIcon />
          </button>
        </div>
      </div>
    </header>
  );
}

function ServerStatus({ server, onRetry }: { server: ServerState; onRetry: () => void }) {
  if (server === "ready") {
    return (
      <span className="inline-flex items-center gap-2 px-2" title="Connected to the HireView server">
        <span className="live-dot h-2 w-2 rounded-full bg-ok" />
        <span className="hidden md:inline">Connected</span>
      </span>
    );
  }
  if (server === "down") {
    return (
      <span className="inline-flex items-center gap-2 px-2 text-red">
        <span className="h-2 w-2 rounded-full bg-red" />
        <span className="hidden md:inline">Server unreachable</span>
        <button type="button" className="btn-text btn-text-red" onClick={onRetry}>
          Retry
        </button>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 px-2">
      <span className="h-2 w-2 animate-pulse rounded-full bg-rule-strong" />
      <span className="working hidden md:inline">Connecting</span>
    </span>
  );
}
