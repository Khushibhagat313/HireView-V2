// Shapes returned by the HireView API (see docs/API_CONTRACT.md).

export type Label = "Exceptional" | "Strong" | "Good" | "Partial" | "Weak";
export const LABELS: Label[] = ["Exceptional", "Strong", "Good", "Partial", "Weak"];

export interface WorkExperience {
  title: string;
  duration_years: number;
}

export interface SearchResult {
  resume_id: string;
  candidate_id: string;
  candidate_name: string;
  raw_score: number;
  display_score: number;
  label: Label;
  facet_scores: Record<string, number>;
  limited_data: boolean;
  skills: string[];
  matched_required: string[];
  missing_required: string[];
  matched_preferred: string[];
  work_experience: WorkExperience[];
}

export interface ChatResponse {
  intent: string;
  response_text: string | null;
  response_candidates: SearchResult[] | null;
}

export interface ResumeSummary {
  resume_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  skills: string[];
  years_experience: number | null;
  uploaded_at: string;
}

export interface CandidateProfile {
  candidate_id: string;
  name: string;
  email: string;
  phone: string | null;
}

export interface Health {
  status: string;
  access_code_required?: boolean;
}

/** A finished ranking: the JD it was made for and its results. */
export interface Ranking {
  jd: string;
  results: SearchResult[];
  /** When the ranking was made (ms since epoch). */
  at: number;
}

export interface ChatTurn {
  id: number;
  query: string;
  status: "pending" | "done" | "error";
  response?: ChatResponse;
  error?: string;
}
