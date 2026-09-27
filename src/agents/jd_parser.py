import json
import hashlib
from pydantic import ValidationError
from groq import BadRequestError
from src.agents.llm_client import call_llm
from src.schemas.job import JDRequirements

JD_PROMPT = """You are given the raw text of a job description, which likely contains a mix of actual requirements and unrelated boilerplate (company culture, benefits, equal-opportunity statements).

Return ONLY a JSON object with these keys:

- "job_title": the title of the role being hired for
- "required_skills": array of skills/technologies explicitly required
- "preferred_skills": array of skills/technologies listed as preferred, nice-to-have, or a plus — not required
- "responsibilities": array of the core day-to-day responsibilities described
- "min_years_experience": minimum years of experience required, as a number, or null if not stated
- "education_requirement": the minimum education requirement described, or null if not stated
- "eligible_graduation_years": if the posting explicitly restricts eligibility to specific graduating batches/years (e.g. "open to 2025 and 2026 graduates", "Graduate Engineer Trainee 2026"), list those years as an array of numbers. Otherwise, an empty array — most postings don't state this.
- "hyde_text": write a short synthetic resume for an ideal candidate — a 1-sentence summary, a skills list, and exactly ONE job experience entry with up to 3 bullet points. Keep the entire thing under 150 words total.

Job description text:
{text}"""

_jd_cache: dict[str, JDRequirements] = {}

def parse_jd(text: str) -> JDRequirements:
    jd_hash = hashlib.sha256(text.encode()).hexdigest()
    if jd_hash in _jd_cache:
        return _jd_cache[jd_hash]

    prompt = JD_PROMPT.format(text=text)
    for attempt in range(2):
        try:
            raw = call_llm(prompt, json_mode=True)
            data = json.loads(raw)
            result = JDRequirements(**data)
            _jd_cache[jd_hash] = result
            return result
        except (json.JSONDecodeError, ValidationError, BadRequestError) as e:
            if attempt == 1:
                raise ValueError(f"JD parsing failed after retry: {e}")