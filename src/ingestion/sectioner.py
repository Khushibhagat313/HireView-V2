import json
from pydantic import ValidationError
from src.agents.llm_client import call_llm
from src.schemas.resume import SectionedResume

SECTION_PROMPT = SECTION_PROMPT = SECTION_PROMPT = SECTION_PROMPT = """You are given the raw text of a resume, possibly with imperfect formatting from PDF extraction.

Split it into the following sections and return ONLY a JSON object with exactly these keys. If a section is not present in the resume, use null for that key. Preserve the original wording — do not summarize or rewrite.

Text section keys: summary_text, skills_text, projects_text, experience_text, achievements_text, publications_text, education_text, certifications_text

Also include a "certifications" key: a JSON array of objects, one per certification found anywhere in the resume, each with:
- "name": the certification's name
- "issuer": the issuing organization, or null if not stated
- "tier": either "assessed" or "completion"

Classify each certification's tier using these criteria:
- "assessed": there was a proctored or invigilated exam, and/or a recognized external issuing body (e.g. AWS, Google Cloud, Microsoft Azure, Linux Foundation, NPTEL with exam, PMI)
- "completion": it only required finishing course content, no proctored exam (most Coursera, Udemy, LinkedIn Learning certificates)

If no certifications are present, return an empty array for "certifications".

Also include a "links" key: a JSON array of objects for every URL found anywhere in the resume, each with:
- "link_type": one of "github", "live_demo", "portfolio", "linkedin", or "other"
- "url": the URL exactly as written
- "label": which project or context it belongs to, or null if it's a general profile link not tied to a specific project

If no links are present, return an empty array for "links".

Also include a "skills" key: a JSON array of every technology, tool, language, or framework mentioned anywhere in the resume — not just under a "Skills" heading. Read project descriptions, experience bullets, and certifications too: a project description that says "Built X using FastAPI and PostgreSQL" means FastAPI and PostgreSQL belong in this list, even if they are never listed under a Skills heading. List each one once, no duplicates, using its exact wording from the resume.

Resume text:
{text}"""

def split_sections(text: str) -> SectionedResume:
    prompt = SECTION_PROMPT.format(text=text)
    for attempt in range(2):
        raw = call_llm(prompt, json_mode=True)
        try:
            data = json.loads(raw)
            return SectionedResume(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == 1:
                raise ValueError(f"Sectioning failed after retry: {e}")