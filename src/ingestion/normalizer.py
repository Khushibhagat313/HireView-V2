ALIAS_MAP = {
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "gcp": "google cloud platform",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "rest api": "rest apis",
    "nodejs": "node.js",
    "node": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
}

def normalize_skills(skills: list[str]) -> set[str]:
    normalized = set()
    for skill in skills:
        cleaned = skill.strip().lower()
        cleaned = ALIAS_MAP.get(cleaned, cleaned)
        normalized.add(cleaned)
    return normalized