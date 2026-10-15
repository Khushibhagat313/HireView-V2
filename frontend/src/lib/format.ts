import type { Label, SearchResult } from "./types";

// Skills arrive normalized to lowercase; show them the way people write them.
const SKILL_NAMES: Record<string, string> = {
  fastapi: "FastAPI",
  postgresql: "PostgreSQL",
  mysql: "MySQL",
  mongodb: "MongoDB",
  javascript: "JavaScript",
  typescript: "TypeScript",
  "node.js": "Node.js",
  "next.js": "Next.js",
  graphql: "GraphQL",
  html: "HTML",
  css: "CSS",
  sql: "SQL",
  aws: "AWS",
  gcp: "GCP",
  "google cloud platform": "Google Cloud",
  "rest apis": "REST APIs",
  "rest api": "REST API",
  api: "API",
  ci: "CI",
  "ci/cd": "CI/CD",
  nlp: "NLP",
  "natural language processing": "NLP",
  "machine learning": "Machine learning",
  "artificial intelligence": "AI",
  llm: "LLM",
  llms: "LLMs",
  pgvector: "pgvector",
  numpy: "NumPy",
  pytorch: "PyTorch",
  tensorflow: "TensorFlow",
  github: "GitHub",
  gitlab: "GitLab",
  "groq api": "Groq API",
  langchain: "LangChain",
  langgraph: "LangGraph",
  seo: "SEO",
  crm: "CRM",
};

export function skillName(skill: string): string {
  const known = SKILL_NAMES[skill.toLowerCase()];
  if (known) return known;
  return skill.replace(/(^|\s)\p{Ll}/gu, (m) => m.toUpperCase());
}

/** "RIYA MEHRA" -> "Riya Mehra"; names already in mixed case are left alone. */
export function personName(name: string): string {
  if (!name) return "Unnamed candidate";
  if (name !== name.toUpperCase()) return name;
  return name.toLowerCase().replace(/(^|[\s'-])\p{L}/gu, (m) => m.toUpperCase());
}

export function initials(name: string): string {
  const parts = personName(name).split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export function duration(years: number): string {
  if (years <= 0) return "under a month";
  if (years < 1) {
    const months = Math.max(1, Math.round(years * 12));
    return `${months} mo`;
  }
  const rounded = Math.round(years * 10) / 10;
  return `${rounded} yr${rounded === 1 ? "" : "s"}`;
}

export function latestRole(result: Pick<SearchResult, "work_experience">): string | null {
  const role = result.work_experience[0];
  return role ? `${role.title} · ${duration(role.duration_years)}` : null;
}

/** The JD's first non-empty line, used as its title. */
export function jdTitle(jd: string): string {
  const first = jd.split("\n").map((l) => l.trim()).find(Boolean) ?? "this role";
  return first.length > 80 ? `${first.slice(0, 77)}…` : first;
}

/** Required skills are not returned on their own, but every result lists the ones it has and lacks. */
export function requiredSkills(results: SearchResult[]): string[] {
  const all = new Set<string>();
  for (const r of results) [...r.matched_required, ...r.missing_required].forEach((s) => all.add(s));
  return [...all].sort();
}

export function labelTone(label: Label | string): "strong" | "mid" | "weak" {
  if (label === "Exceptional" || label === "Strong") return "strong";
  if (label === "Good") return "mid";
  return "weak";
}

export const FACETS: { key: string; name: string }[] = [
  { key: "skills", name: "Skills" },
  { key: "projects", name: "Projects" },
  { key: "experience", name: "Work experience" },
  { key: "achievements_publications", name: "Achievements & publications" },
  { key: "education_certifications", name: "Education & certifications" },
];

/** "just now", "5 min ago", "2 hr ago", then a date. */
export function timeAgo(ms: number, now = Date.now()): string {
  const minutes = Math.floor((now - ms) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return uploadedOn(new Date(ms).toISOString());
}

export function uploadedOn(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) });
}
