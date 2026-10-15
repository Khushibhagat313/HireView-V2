# API Contract

## Conventions (all endpoints)
- Every id (`company_id`, `candidate_id`, `resume_id`, `job_posting_id`) must be a UUID. A malformed id returns **422** before any work is done.
- Errors are JSON: `{ "detail": "human-readable message" }` (for 422 validation errors FastAPI returns `detail` as a list describing each bad field).
- **503** on any endpoint that uses the LLM means the AI service (Groq) is down or returned unusable output. Show "AI service temporarily unavailable, please try again".
- Search results are cached per company + job description; uploads and deletes clear that company's cache automatically.
- CORS: browser calls are accepted only from origins listed in `CORS_ALLOWED_ORIGINS` (`src/config.py`).

## GET /resumes
Lists every resume in a company's pool, newest first. No job description needed.

Query params:
- company_id: string (UUID), required

Response: 200 OK
{
  "resumes": [
    {
      "resume_id": "uuid",
      "candidate_id": "uuid",
      "candidate_name": "string",
      "candidate_email": "string",
      "skills": ["string"],
      "years_experience": "float or null",
      "uploaded_at": "ISO 8601 datetime"
    }
  ]
}

- A candidate who uploaded more than once appears once per resume here (this is the raw pool; search shows each candidate once).

## POST /resumes/upload
Uploads and ingests a resume PDF.

Request: multipart/form-data
- company_id: string (UUID)
- file: PDF file
- job_posting_id: string (UUID), optional

Response: 201 Created
{
  "resume_id": "uuid"
}

- Takes ~10–20 seconds (the resume is read by the LLM). Show a progress state.
- Uploading a resume whose email matches an existing candidate attaches it to that candidate.

Errors:
- 404 if the company (or the given job posting) does not exist.
- 422 if the file is not a readable PDF, is over 10 MB or 15 pages, is a scanned image with no text, or its name/email could not be read. `detail` says which.
- 503 if the AI service is unavailable.

## DELETE /resumes/{resume_id}
Deletes a resume and everything cascaded from it (embeddings, certifications, links).

Query params:
- company_id: string (UUID), required

Response: 204 No Content

Errors: 404 if the resume does not exist in this company.

## POST /search
Runs a job description against a company's resume pool, returns ranked, scored candidates.

Request: application/json
{
  "company_id": "uuid",
  "jd_text": "string",
  "job_posting_id": "uuid, optional",
  "threshold": "number, optional",
  "max_results": "integer, optional"
}

Response: 200 OK
{
  "results": [
    {
      "resume_id": "uuid",
      "candidate_id": "uuid",
      "candidate_name": "string",
      "raw_score": "float",
      "display_score": "float",
      "label": "string",
      "facet_scores": { "skills": 0.5, "...": 0.0 },
      "limited_data": "boolean",
      "skills": ["string"],
      "matched_required": ["string"],
      "missing_required": ["string"],
      "matched_preferred": ["string"],
      "work_experience": [{ "title": "string", "duration_years": "float" }]
    }
  ]
}

- `facet_scores` keys vary per candidate: a facet is omitted when the resume has no text for it.
- Skill names are normalized to lowercase (e.g. "postgres" → "postgresql"); the frontend should title-case them for display.
- `skills` is every skill on the resume; `matched_required` / `missing_required` / `matched_preferred` are relative to the JD.
- Each candidate appears at most once. If they have several resumes, the highest-scoring one is shown (`resume_id` tells you which).
- An empty `results` list is a normal answer (nobody passed eligibility or the display threshold), not an error.

## GET /candidates/{candidate_id}
Returns a candidate's basic profile.

Query params:
- company_id: string (UUID), required

Response: 200 OK
{
  "candidate_id": "uuid",
  "name": "string",
  "email": "string",
  "phone": "string or null"
}

Errors: 404 if the candidate does not exist in this company.

---
## POST /chat
Answers a recruiter's question about the ranked candidates for a job description. Each call is independent: no conversation history is sent or kept.

Request: application/json
{
  "company_id": "uuid",
  "jd_text": "string",
  "query": "string"
}

Response: 200 OK
{
  "intent": "string",
  "response_text": "string or null",
  "response_candidates": [ <same shape as one item of POST /search results> ] or null
}

- `intent` is one of: show_top_n, filter_by_skill, filter_by_experience, hidden_gems, explain_score, compare, interview_questions, general.
- show_top_n, filter_by_skill, filter_by_experience and hidden_gems fill `response_candidates` and leave `response_text` null. The other intents fill `response_text` and leave `response_candidates` null.
- When one of those four list intents finds nobody, or can't read the question, it returns a plain-language `response_text` instead (for example "No one in these results lists Kubernetes on their resume.") and `response_candidates` is null. A non-null `response_candidates` therefore always has at least one entry.
- Skill questions can name several skills: "who knows Python and Docker" (and `,` / `&`) needs all of them; "who knows Python or Go" needs any one. Leading phrases like "experience with" are ignored.
- Clarifications ("Which candidate do you mean?") and temporary AI-service failures also arrive as a normal 200 with a plain-language `response_text`.

## POST /candidates/{candidate_id}/feedback
Explains in plain language why a candidate received their match label for a job description. Leads with the label and never states a numeric score.

Request: application/json
{
  "company_id": "uuid",
  "jd_text": "string"
}

Response: 200 OK
{
  "candidate_id": "uuid",
  "feedback": "string"
}

Errors: 404 if the candidate is not among the ranked results for this job description; 503 if the AI service is unavailable.

## POST /candidates/{candidate_id}/interview-guide
Generates 3 to 5 interview questions for a candidate, each with a one-line reason, based on their resume and their gaps against the job description.

Request: application/json
{
  "company_id": "uuid",
  "jd_text": "string"
}

Response: 200 OK
{
  "candidate_id": "uuid",
  "interview_guide": "string"
}

Errors: 404 as above; 422 if no usable questions could be generated for this resume; 503 if the AI service is unavailable.

## Deferred — depend on later phases, not implemented yet
- POST /emails/draft, POST /emails/send — needs `src/email/*` (Phase 7)