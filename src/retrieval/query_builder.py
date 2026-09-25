from src.embedding.embedder import embed_query
from src.schemas.job import JDRequirements

def build_queries(jd: JDRequirements) -> dict[str, list[float]]:
    skills_text = ", ".join(jd.required_skills + jd.preferred_skills)
    experience_text = " ".join(jd.responsibilities)
    projects_text = skills_text + ". " + experience_text

    return {
        "skills": embed_query(skills_text),
        "experience": embed_query(experience_text),
        "projects": embed_query(projects_text),
        "hyde": embed_query(jd.hyde_text),
    }