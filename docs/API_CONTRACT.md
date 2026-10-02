# API Contract

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

## DELETE /resumes/{resume_id}
Deletes a resume and everything cascaded from it (embeddings, certifications, links).

Query params:
- company_id: string (UUID), required

Response: 204 No Content

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
      "limited_data": "boolean"
    }
  ]
}

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
- - POST /emails/draft, POST /emails/send — needs `src/email/*` (Phase 7)