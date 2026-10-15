import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, messageFor } from "../lib/api";
import type { ResumeSummary } from "../lib/types";
import { duration, personName, skillName, uploadedOn } from "../lib/format";
import { useToast } from "../lib/toast";
import { CheckIcon, CloseIcon, DocIcon, SearchIcon, TrashIcon, UploadIcon } from "./Icons";
import { Monogram } from "./Marks";
import { ErrorLine } from "./Note";

// Vercel caps a request body at 4.5 MB, below the backend's own 10 MB limit.
const MAX_BYTES = 4 * 1024 * 1024;

type Upload = {
  id: number;
  file: File;
  status: "waiting" | "uploading" | "done" | "failed";
  error?: string;
  startedAt?: number;
};

export function PoolScreen({ onPoolChanged }: { onPoolChanged: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.resumes });
  const [filter, setFilter] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [dragging, setDragging] = useState(false);
  const [, tick] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(1);

  const addFiles = useCallback((files: FileList | File[]) => {
    const fresh: Upload[] = [...files].map((file) => {
      const base = { id: nextId.current++, file };
      if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
        return { ...base, status: "failed", error: "Only PDF files can be uploaded." };
      }
      if (file.size > MAX_BYTES) return { ...base, status: "failed", error: "This PDF is over 4 MB." };
      return { ...base, status: "waiting" };
    });
    setUploads((prev) => [...prev, ...fresh]);
  }, []);

  // The whole page is a drop target. Counting enter/leave avoids the flicker that
  // dragleave causes each time the pointer crosses a child element.
  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => e.dataTransfer?.types.includes("Files") ?? false;
    const onEnter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth += 1;
      setDragging(true);
    };
    const onLeave = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const onOver = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault();
    };
    const onDrop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setDragging(false);
      if (e.dataTransfer?.files.length) addFiles(e.dataTransfer.files);
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("dragover", onOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("drop", onDrop);
    };
  }, [addFiles]);

  // Escape backs out of a pending delete.
  useEffect(() => {
    if (!confirming) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setConfirming(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [confirming]);

  // Upload one file at a time; each takes ~10–20 s while the AI reads the resume.
  useEffect(() => {
    if (uploads.some((u) => u.status === "uploading")) return;
    const next = uploads.find((u) => u.status === "waiting");
    if (!next) return;
    setUploads((prev) => prev.map((u) => (u.id === next.id ? { ...u, status: "uploading", startedAt: Date.now() } : u)));
    api
      .upload(next.file)
      .then(() => {
        setUploads((prev) => prev.map((u) => (u.id === next.id ? { ...u, status: "done" } : u)));
        queryClient.invalidateQueries({ queryKey: ["resumes"] });
        onPoolChanged();
      })
      .catch((err) => {
        setUploads((prev) => prev.map((u) => (u.id === next.id ? { ...u, status: "failed", error: messageFor(err) } : u)));
      });
  }, [uploads, queryClient, onPoolChanged]);

  // Honest progress: show elapsed seconds instead of a fake percentage.
  const uploading = uploads.some((u) => u.status === "uploading");
  useEffect(() => {
    if (!uploading) return;
    const t = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(t);
  }, [uploading]);

  const versions = useMemo(() => {
    const count = new Map<string, number>();
    resumes.data?.forEach((r) => count.set(r.candidate_id, (count.get(r.candidate_id) ?? 0) + 1));
    return count;
  }, [resumes.data]);

  const rows = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return resumes.data ?? [];
    return (resumes.data ?? []).filter(
      (r) => r.candidate_name.toLowerCase().includes(q) || r.candidate_email.toLowerCase().includes(q) || r.skills.some((s) => s.includes(q)),
    );
  }, [resumes.data, filter]);

  const latest = resumes.data?.reduce<string | null>((max, r) => (!max || r.uploaded_at > max ? r.uploaded_at : max), null);
  const pick = () => inputRef.current?.click();

  const remove = async (r: ResumeSummary) => {
    setDeleting(r.resume_id);
    try {
      await api.deleteResume(r.resume_id);
      toast(`Deleted ${personName(r.candidate_name)}'s resume`);
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      onPoolChanged();
    } catch (err) {
      toast(messageFor(err));
    } finally {
      setDeleting(null);
      setConfirming(null);
    }
  };

  const deleteControl = (r: ResumeSummary) =>
    confirming === r.resume_id ? (
      <span className="settle inline-flex items-center gap-2">
        <span className="text-[13px]">Delete?</span>
        <button type="button" className="btn btn-sm border-red bg-red text-paper hover:!bg-red" disabled={deleting === r.resume_id} onClick={() => remove(r)}>
          {deleting === r.resume_id ? "Deleting…" : "Delete"}
        </button>
        <button type="button" className="btn btn-quiet btn-sm" onClick={() => setConfirming(null)}>
          Cancel
        </button>
      </span>
    ) : (
      <button
        type="button"
        className="btn btn-quiet btn-icon btn-sm opacity-60 group-hover:opacity-100 hover:!text-red focus-visible:opacity-100"
        onClick={() => setConfirming(r.resume_id)}
        aria-label={`Delete ${personName(r.candidate_name)}'s resume`}
        title="Delete resume"
      >
        <TrashIcon size={15} />
      </button>
    );

  return (
    <div className="grid gap-8">
      {dragging && (
        <div className="scrim pointer-events-none fixed inset-0 z-50 grid place-items-center bg-[var(--scrim)] p-6" aria-hidden="true">
          <div className="grid w-full max-w-md justify-items-center gap-3 rounded-2xl border-2 border-dashed border-red bg-sheet px-8 py-10 text-center shadow-[var(--shadow-lg)]">
            <span className="grid h-14 w-14 place-items-center rounded-xl border border-red text-red">
              <UploadIcon size={24} />
            </span>
            <p className="font-serif text-[22px] font-semibold">Drop to add resumes</p>
            <p className="text-[13.5px] text-pencil">PDFs up to 4 MB each</p>
          </div>
        </div>
      )}
      <div className="settle flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <div className="grid gap-3">
          <span className="eyebrow">Resume pool</span>
          <h1 className="font-serif text-[36px] leading-[1.08] font-semibold tracking-[-0.022em] sm:text-[44px]">
            Everyone you can <span className="hl-title">rank</span>
          </h1>
          <p className="max-w-[60ch] text-[15.5px] text-pencil">
            Every ranking runs against everyone here. Add resumes as PDFs; remove anyone who is no longer in the running.
          </p>
        </div>
        <button type="button" className="btn" onClick={pick}>
          <UploadIcon size={15} /> Upload resumes
        </button>
      </div>

      <dl
        className="settle grid grid-cols-3 overflow-hidden rounded-[14px] border border-rule bg-sheet shadow-[var(--inset),var(--shadow-sm)]"
        style={{ ["--d" as string]: "60ms" }}
      >
        <PoolStat term="Resumes" value={resumes.data ? String(resumes.data.length) : null} />
        <PoolStat term="People" value={resumes.data ? String(versions.size) : null} />
        <PoolStat term="Last upload" value={resumes.data ? (latest ? uploadedOn(latest) : "–") : null} />
      </dl>

      <section aria-label="Upload resumes" className="settle grid gap-3" style={{ ["--d" as string]: "120ms" }}>
        <div
          className={`flex flex-wrap items-center gap-x-5 gap-y-4 rounded-[14px] border-2 border-dashed px-6 py-6 transition-colors sm:px-7 ${
            dragging ? "border-red bg-red-wash" : "border-rule-strong bg-[color-mix(in_srgb,var(--sheet)_55%,transparent)]"
          }`}
        >
          <span
            className={`grid h-12 w-12 shrink-0 place-items-center rounded-xl border bg-sheet shadow-[var(--shadow-sm)] transition-transform ${
              dragging ? "-translate-y-0.5 border-red text-red" : "border-rule text-pencil"
            }`}
          >
            <DocIcon size={22} />
          </span>
          <div className="grid min-w-0 flex-1 basis-60 gap-0.5">
            <p className="font-serif text-[18px] font-semibold">Drop PDF resumes anywhere on this page</p>
            <p className="text-[13.5px] text-pencil">Text-based PDFs up to 4 MB. Each one takes 10–20 seconds while it's read.</p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={pick}>
            Choose files
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="sr-only"
            tabIndex={-1}
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {uploads.length > 0 && (
          <ul className="sheet divide-y divide-rule overflow-hidden text-[14px]" aria-live="polite">
            {uploads.map((u) => (
              <li key={u.id} className="settle grid gap-2.5 px-5 py-3.5">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                  <span className="flex min-w-0 items-center gap-2.5">
                    <DocIcon size={15} className="shrink-0 text-pencil" />
                    <span className="truncate font-medium">{u.file.name}</span>
                    <span className="shrink-0 text-[12px] text-pencil tabular-nums">{(u.file.size / 1024 / 1024).toFixed(1)} MB</span>
                  </span>
                  <span className="flex items-center gap-3 text-[13px]">
                    {u.status === "waiting" && <span className="text-pencil">Waiting</span>}
                    {u.status === "uploading" && (
                      <span className="working text-pencil tabular-nums">
                        Reading resume · {Math.round((Date.now() - (u.startedAt ?? Date.now())) / 1000)}s
                      </span>
                    )}
                    {u.status === "done" && (
                      <span className="inline-flex items-center gap-1.5 font-medium text-ok">
                        <CheckIcon size={15} /> Added
                      </span>
                    )}
                    {u.status === "failed" && (
                      <>
                        <span className="text-red">{u.error}</span>
                        {u.error?.includes("busy") && (
                          <button
                            type="button"
                            className="btn-text"
                            onClick={() => setUploads((prev) => prev.map((x) => (x.id === u.id ? { ...x, status: "waiting", error: undefined } : x)))}
                          >
                            Retry
                          </button>
                        )}
                      </>
                    )}
                  </span>
                </div>
                {u.status === "uploading" && <div className="progress" aria-hidden="true" />}
              </li>
            ))}
            {!uploads.some((u) => u.status === "waiting" || u.status === "uploading") && (
              <li className="flex justify-end bg-sheet-2 px-4 py-2">
                <button type="button" className="btn btn-quiet btn-sm" onClick={() => setUploads([])}>
                  Clear this list
                </button>
              </li>
            )}
          </ul>
        )}
      </section>

      <section aria-label="Resumes" className="settle grid gap-3" style={{ ["--d" as string]: "180ms" }}>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="pool-filter" className="sr-only">
            Filter resumes
          </label>
          <div className="relative w-full max-w-sm">
            <SearchIcon size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-pencil" />
            <input id="pool-filter" className="field pr-10 pl-9" placeholder="Filter by name, email or skill" value={filter} onChange={(e) => setFilter(e.target.value)} />
            {filter && (
              <button
                type="button"
                className="btn btn-quiet btn-icon absolute top-1/2 right-1 h-8 w-8 -translate-y-1/2"
                onClick={() => setFilter("")}
                aria-label="Clear filter"
              >
                <CloseIcon size={13} />
              </button>
            )}
          </div>
          {filter && (
            <span className="text-sm text-pencil tabular-nums">
              {rows.length} of {resumes.data?.length ?? 0}
            </span>
          )}
        </div>

        {resumes.isPending && (
          <div className="sheet grid gap-5 p-5" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-4" style={{ opacity: 1 - i * 0.28 }}>
                <span className="skeleton h-10 w-10 rounded-full" />
                <span className="grid flex-1 gap-2">
                  <span className="skeleton h-3.5 w-40" />
                  <span className="skeleton h-3 w-56 max-w-full" />
                </span>
              </div>
            ))}
          </div>
        )}
        {resumes.isError && <ErrorLine message={messageFor(resumes.error)} onRetry={() => resumes.refetch()} />}
        {resumes.data && resumes.data.length === 0 && (
          <div className="sheet grid justify-items-start gap-2 px-7 py-10">
            <span className="hand text-[17px]">An empty desk.</span>
            <p className="font-serif text-[20px] font-medium">No resumes yet. Drop a few PDFs above to start ranking.</p>
          </div>
        )}
        {resumes.data && resumes.data.length > 0 && rows.length === 0 && <p className="px-1 text-sm text-pencil">Nobody matches "{filter}".</p>}

        {rows.length > 0 && (
          <ul className="sheet sheet-raised divide-y divide-rule overflow-hidden md:hidden">
            {rows.map((r) => {
              const copies = versions.get(r.candidate_id) ?? 1;
              return (
                <li key={r.resume_id} className="grid gap-3 px-4 py-4">
                  <div className="flex items-start gap-3">
                    <Monogram name={r.candidate_name} size={38} />
                    <div className="grid min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="font-serif text-[16px] font-semibold">{personName(r.candidate_name)}</span>
                        {copies > 1 && <span className="hand text-[12.5px]">{copies} versions</span>}
                      </div>
                      <div className="truncate text-[13px] text-pencil">{r.candidate_email}</div>
                      <div className="mt-0.5 text-[12.5px] text-pencil tabular-nums">
                        {r.years_experience ? duration(r.years_experience) : "No experience listed"} · Uploaded {uploadedOn(r.uploaded_at)}
                      </div>
                    </div>
                    <div className="shrink-0">{deleteControl(r)}</div>
                  </div>
                  {r.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pl-[50px]">
                      {r.skills.slice(0, 3).map((s) => (
                        <span key={s} className="tag">
                          {skillName(s)}
                        </span>
                      ))}
                      {r.skills.length > 3 && <span className="tag text-pencil">+{r.skills.length - 3}</span>}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {rows.length > 0 && (
          <div className="sheet sheet-raised relative hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-left text-[14px]">
              <thead>
                <tr className="border-b border-rule bg-sheet-2">
                  {["Candidate", "Skills", "Experience", "Uploaded", ""].map((h, i) => (
                    <th key={i} scope="col" className="eyebrow px-5 py-3 font-semibold">
                      {h || <span className="sr-only">Actions</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {rows.map((r) => {
                  const copies = versions.get(r.candidate_id) ?? 1;
                  return (
                    <tr key={r.resume_id} className="group align-middle transition-colors hover:bg-sheet-2">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <Monogram name={r.candidate_name} size={38} />
                          <div className="grid min-w-0">
                            <div className="flex flex-wrap items-baseline gap-x-2">
                              <span className="font-serif text-[16px] font-semibold">{personName(r.candidate_name)}</span>
                              {copies > 1 && <span className="hand text-[12.5px]">{copies} versions</span>}
                            </div>
                            <div className="truncate text-[13px] text-pencil">{r.candidate_email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="max-w-[340px] px-5 py-4">
                        <div className="flex flex-wrap gap-1.5">
                          {r.skills.slice(0, 4).map((s) => (
                            <span key={s} className="tag">
                              {skillName(s)}
                            </span>
                          ))}
                          {r.skills.length > 4 && <span className="tag text-pencil">+{r.skills.length - 4}</span>}
                          {r.skills.length === 0 && <span className="text-[13px] text-pencil">None listed</span>}
                        </div>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-pencil tabular-nums">{r.years_experience ? duration(r.years_experience) : "None listed"}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-pencil tabular-nums">{uploadedOn(r.uploaded_at)}</td>
                      <td className="px-5 py-4 text-right whitespace-nowrap">
                        {deleteControl(r)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function PoolStat({ term, value }: { term: string; value: string | null }) {
  return (
    <div className="grid min-w-0 gap-1.5 border-r border-rule px-4 py-4 last:border-r-0 sm:px-6">
      <dt className="eyebrow truncate">{term}</dt>
      <dd>
        {value === null ? (
          <span className="skeleton block h-7 w-16" />
        ) : (
          <span className="font-serif text-[28px] leading-none font-semibold tabular-nums">{value}</span>
        )}
      </dd>
    </div>
  );
}
