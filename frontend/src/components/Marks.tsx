import type { Label, SearchResult } from "../lib/types";
import { initials, labelTone, skillName } from "../lib/format";

export function LabelMark({ label, size = "md" }: { label: Label | string; size?: "sm" | "md" | "lg" }) {
  const text = size === "lg" ? "text-[24px]" : size === "sm" ? "text-[13px]" : "text-[16px]";
  return <span className={`mark mark-${labelTone(label)} ${text}`}>{label}</span>;
}

/** Score out of 100: a number with a thin bar under it. Secondary to the label, so it stays quiet. */
export function ScoreMeter({ score, delay = 0, width = "w-16" }: { score: number; delay?: number; width?: string }) {
  const value = Math.max(0, Math.min(100, Math.round(score)));
  return (
    <span className={`grid ${width} gap-1`} aria-label={`Score ${value} out of 100`}>
      <span className="flex items-baseline justify-end gap-0.5 tabular-nums">
        <span className="font-serif text-[17px] font-semibold text-ink">{value}</span>
        <span className="text-[11px] text-pencil">/100</span>
      </span>
      <span className="meter meter-thin" aria-hidden="true">
        <span style={{ width: `${value}%`, ["--d" as string]: `${delay}ms` }} />
      </span>
    </span>
  );
}

export function Monogram({ name, size = 40 }: { name: string; size?: number }) {
  return (
    <span className="monogram" style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

/** Required skills: highlighted when the candidate has them, struck through in red when they don't. */
export function RequiredSkills({ result, animate = false }: { result: SearchResult; animate?: boolean }) {
  const { matched_required: has, missing_required: missing, matched_preferred: preferred } = result;
  if (!has.length && !missing.length && !preferred.length) {
    return <span className="text-sm text-pencil">No skills section on this resume</span>;
  }
  return (
    <span className={`flex flex-wrap items-baseline gap-x-2.5 gap-y-1.5 text-[14px] ${animate ? "swipe" : ""}`}>
      {has.map((s, i) => (
        <span key={s} className="hl" style={{ ["--d" as string]: `${160 + i * 90}ms` }}>
          {skillName(s)}
        </span>
      ))}
      {missing.map((s) => (
        <span key={s} className="struck">
          {skillName(s)}
        </span>
      ))}
      {preferred.length > 0 && (
        <span className="text-[13px] text-pencil">
          + {preferred.map(skillName).join(", ")} <span className="text-[11.5px] opacity-80">preferred</span>
        </span>
      )}
    </span>
  );
}
