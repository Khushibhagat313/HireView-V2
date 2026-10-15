import type { CandidateProfile, ChatResponse, Health, ResumeSummary, SearchResult } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";
export const COMPANY_ID = import.meta.env.VITE_COMPANY_ID ?? "a47c623b-569d-442b-8e0d-ff4c9d8dcf07";
export const COMPANY_NAME = import.meta.env.VITE_COMPANY_NAME ?? "Test Co";

const CODE_KEY = "hireview.accessCode";
export const LOCKED_EVENT = "hireview:locked";

export function getAccessCode(): string {
  try {
    return localStorage.getItem(CODE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setAccessCode(code: string) {
  try {
    if (code) localStorage.setItem(CODE_KEY, code);
    else localStorage.removeItem(CODE_KEY);
  } catch {
    /* storage blocked: the code lives for this page load only */
  }
  memoryCode = code;
}

let memoryCode = getAccessCode();

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: a list of { loc, msg }
  if (Array.isArray(detail)) {
    return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join("; ");
  }
  return "Something went wrong.";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (memoryCode) headers.set("X-Access-Code", memoryCode);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the HireView server. Check your connection and try again.");
  }

  if (res.status === 401) window.dispatchEvent(new Event(LOCKED_EVENT));
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      message = detailText((await res.json()).detail);
    } catch {
      /* non-JSON error body (e.g. a platform timeout page) */
      if (res.status === 504) message = "The server took too long to answer. Try again.";
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** What to show the recruiter for any failed call. */
export function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503) return "The AI service is busy right now. Try again in a moment.";
    return error.message;
  }
  return "Something went wrong.";
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  health: () => request<Health>("/health"),

  search: (jd: string) =>
    request<{ results: SearchResult[] }>("/search", {
      method: "POST",
      body: json({ company_id: COMPANY_ID, jd_text: jd }),
    }).then((r) => r.results),

  chat: (jd: string, query: string) =>
    request<ChatResponse>("/chat", { method: "POST", body: json({ company_id: COMPANY_ID, jd_text: jd, query }) }),

  candidate: (candidateId: string) =>
    request<CandidateProfile>(`/candidates/${candidateId}?company_id=${COMPANY_ID}`),

  feedback: (candidateId: string, jd: string) =>
    request<{ feedback: string }>(`/candidates/${candidateId}/feedback`, {
      method: "POST",
      body: json({ company_id: COMPANY_ID, jd_text: jd }),
    }).then((r) => r.feedback),

  interviewGuide: (candidateId: string, jd: string) =>
    request<{ interview_guide: string }>(`/candidates/${candidateId}/interview-guide`, {
      method: "POST",
      body: json({ company_id: COMPANY_ID, jd_text: jd }),
    }).then((r) => r.interview_guide),

  resumes: () => request<{ resumes: ResumeSummary[] }>(`/resumes?company_id=${COMPANY_ID}`).then((r) => r.resumes),

  upload: (file: File) => {
    const form = new FormData();
    form.append("company_id", COMPANY_ID);
    form.append("file", file);
    return request<{ resume_id: string }>("/resumes/upload", { method: "POST", body: form });
  },

  deleteResume: (resumeId: string) =>
    request<void>(`/resumes/${resumeId}?company_id=${COMPANY_ID}`, { method: "DELETE" }),
};
