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

## Deferred — depend on later phases, not implemented yet
- GET /candidates/{id}/feedback — needs `src/agents/feedback.py` (Phase 5)
- GET /candidates/{id}/interview-guide — needs `src/agents/interview_guide.py` (Phase 5)
- POST /chat — needs `src/agents/conversation/*` (Phase 5)
- POST /emails/draft, POST /emails/send — needs `src/email/*` (Phase 7)