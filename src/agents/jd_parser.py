import json
from pydantic import ValidationError
from src.agents.llm_client import call_llm
from src.schemas.job import JDRequirements

JD_PROMPT = """You are given the raw text of a job description, which likely contains a mix of actual requirements and unrelated boilerplate (company culture, benefits, equal-opportunity statements).

Return ONLY a JSON object with these keys:

- "required_skills": array of skills/technologies explicitly required
- "preferred_skills": array of skills/technologies listed as preferred, nice-to-have, or a plus — not required
- "responsibilities": array of the core day-to-day responsibilities described
- "min_years_experience": minimum years of experience required, as a number, or null if not stated
- "education_requirement": the minimum education requirement described, or null if not stated
- "hyde_text": write a synthetic, realistic resume for an IDEAL candidate for this exact job — a few paragraphs covering summary, skills, and experience, written the way a real resume reads, not a restatement of the JD

Job description text:
{text}"""

def parse_jd(text: str) -> JDRequirements:
    prompt = JD_PROMPT.format(text=text)
    for attempt in range(2):
        raw = call_llm(prompt, json_mode=True)
        try:
            data = json.loads(raw)
            return JDRequirements(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == 1:
                raise ValueError(f"JD parsing failed after retry: {e}")