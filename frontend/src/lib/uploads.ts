import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, messageFor } from "./api";

// Vercel caps a request body at 4.5 MB, below the backend's own 10 MB limit.
export const MAX_BYTES = 4 * 1024 * 1024;

export type Upload = {
  id: number;
  file: File;
  status: "waiting" | "uploading" | "done" | "failed";
  error?: string;
  /** A busy AI, a timeout or a dropped connection; worth another go, unlike a bad PDF. */
  retryable?: boolean;
  startedAt?: number;
};

const isRetryable = (err: unknown) => err instanceof ApiError && [0, 502, 503, 504].includes(err.status);

/** The upload queue lives above the Pool screen, so switching to Rank mid-batch doesn't drop the files still waiting. */
export function useUploadQueue(onPoolChanged: () => void) {
  const queryClient = useQueryClient();
  const [uploads, setUploads] = useState<Upload[]>([]);
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

  const retry = useCallback(
    (id: number) => setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, status: "waiting", error: undefined, retryable: undefined } : u))),
    [],
  );
  const clear = useCallback(() => setUploads([]), []);

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
        setUploads((prev) =>
          prev.map((u) => (u.id === next.id ? { ...u, status: "failed", error: messageFor(err), retryable: isRetryable(err) } : u)),
        );
      });
  }, [uploads, queryClient, onPoolChanged]);

  return { uploads, addFiles, retry, clear };
}

export type UploadQueue = ReturnType<typeof useUploadQueue>;
