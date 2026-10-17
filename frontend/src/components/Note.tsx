import { lazy, Suspense } from "react";

const Markdown = lazy(() => import("./Markdown"));

/** AI-written text (feedback, interview guides, chat answers) arrives as Markdown. */
export function Note({ text, serif = true }: { text: string; serif?: boolean }) {
  return (
    <div className={`prose-note settle ${serif ? "font-serif text-[15.5px] leading-[1.75]" : "text-[14.5px] leading-relaxed"}`}>
      <Suspense fallback={<p className="whitespace-pre-wrap">{text}</p>}>
        <Markdown text={text} />
      </Suspense>
    </div>
  );
}

export function Working({ children }: { children: string }) {
  return (
    <p className="working text-sm text-pencil" role="status">
      {children}
    </p>
  );
}

/** Placeholder paragraph while the AI writes; the caption says what it's doing. */
export function WritingSkeleton({ caption, lines = 4 }: { caption: string; lines?: number }) {
  const widths = ["100%", "94%", "97%", "62%", "88%", "76%"];
  return (
    <div className="grid gap-3" role="status">
      <p className="working text-[13px] text-pencil">{caption}</p>
      <div className="grid gap-2.5" aria-hidden="true">
        {Array.from({ length: lines }, (_, i) => (
          <span key={i} className="skeleton h-3.5" style={{ width: widths[i % widths.length] }} />
        ))}
      </div>
    </div>
  );
}

export function ErrorLine({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <p
      className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-lg border border-[color-mix(in_srgb,var(--red)_25%,transparent)] bg-red-wash px-3.5 py-2.5 text-sm text-red"
      role="alert"
    >
      {message}
      {onRetry && (
        <button type="button" className="btn-text btn-text-red" onClick={onRetry}>
          Try again
        </button>
      )}
    </p>
  );
}
