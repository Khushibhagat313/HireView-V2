import pytest
from src.agents.conversation.router import classify_intent
from types import SimpleNamespace
from src.agents.conversation.graph import build_graph
from src.agents import feedback, interview_guide
from src.agents.conversation import handlers


def test_classify_intent_keyword_matches():
    assert classify_intent({"query": "show me the top 5"})["intent"] == "show_top_n"
    assert classify_intent({"query": "who knows react"})["intent"] == "filter_by_skill"
    assert classify_intent({"query": "compare Priya and Raj"})["intent"] == "compare"
    assert classify_intent({"query": "what's the weather"})["intent"] == "general"

def make_state(query: str) -> dict:
    return {
        "query": query,
        "company_id": "test-company",
        "jd_hash": "test-hash",
        "jd": SimpleNamespace(job_title="Backend Developer", required_skills=["python"], preferred_skills=[]),
        "candidates": [
            {
                "candidate_id": "a",
                "candidate_name": "Priya Sharma",
                "label": "Strong",
                "skills": ["python", "react"],
                "matched_required": ["python"],
                "missing_required": [],
                "matched_preferred": [],
                "facet_scores": {"skills": 0.9, "projects": 0.8},
                "work_experience": [SimpleNamespace(title="Backend Developer", duration_years=2.5)],
            },
            {
                "candidate_id": "b",
                "candidate_name": "Arjun Mehta",
                "label": "Partial",
                "skills": ["java"],
                "matched_required": [],
                "missing_required": ["python"],
                "matched_preferred": [],
                "facet_scores": {"skills": 0.5, "projects": 0.4},
                "work_experience": [SimpleNamespace(title="Marketing Intern", duration_years=5.0)],
            },
        ],
        "below_threshold": [],
        "feedback_cache": {},
        "llm_calls": 0,
        "errors": [],
        "intent": None,
        "response_text": None,
        "response_candidates": None,
    }


def test_router_accuracy_five_question_types(monkeypatch):
    monkeypatch.setattr(
        "src.agents.conversation.handlers.call_llm",
        lambda prompt, json_mode=False: "stubbed answer",
    )
    app = build_graph()

    top_n = app.invoke(make_state("show me the top 1"))
    assert len(top_n["response_candidates"]) == 1

    skill = app.invoke(make_state("who knows python"))
    assert [c["candidate_id"] for c in skill["response_candidates"]] == ["a"]

    experience = app.invoke(make_state("who has 2+ years as a backend developer"))
    assert [c["candidate_id"] for c in experience["response_candidates"]] == ["a"]

    gems = app.invoke(make_state("hidden gems"))
    assert gems["response_candidates"] is None
    assert gems["response_text"].startswith("No hidden gems")

    fallback = app.invoke(make_state("what is the weather"))
    assert fallback["response_text"] == "stubbed answer"


def test_skill_questions_with_several_skills():
    app = build_graph()

    both = app.invoke(make_state("who knows Python and React?"))
    assert [c["candidate_id"] for c in both["response_candidates"]] == ["a"]

    either = app.invoke(make_state("who has experience with Java or Rust"))
    assert [c["candidate_id"] for c in either["response_candidates"]] == ["b"]

    listed = app.invoke(make_state("who knows python, react & java"))
    assert listed["response_candidates"] is None
    assert listed["response_text"] == "No one in these results lists all of python, react and java."


def test_empty_answers_explain_themselves():
    app = build_graph()

    nobody = app.invoke(make_state("who knows Kubernetes"))
    assert nobody["response_candidates"] is None
    assert nobody["response_text"] == "No one in these results lists Kubernetes on their resume."

    no_skill = app.invoke(make_state("who has"))
    assert no_skill["response_text"].startswith("Which skill?")

    no_role = app.invoke(make_state("who has 9 years as a pilot"))
    assert no_role["response_text"] == "No one in these results has 9+ years as pilot."

    state = make_state("show me the top 3")
    state["candidates"] = []
    assert app.invoke(state)["response_text"].startswith("No candidates passed")

JD = SimpleNamespace(
    job_title="Backend Developer",
    required_skills=["python", "fastapi", "postgresql"],
    preferred_skills=["docker"],
)


def make_candidate(**overrides) -> dict:
    candidate = {
        "resume_id": "r1",
        "candidate_id": "cand-1",
        "candidate_name": "Priya Sharma",
        "label": "Strong",
        "limited_data": False,
        "skills": ["python", "fastapi"],
        "facet_scores": {"skills": 0.731, "projects": 0.652},
        "matched_required": ["python", "fastapi"],
        "missing_required": ["postgresql"],
        "matched_preferred": [],
        "work_experience": [SimpleNamespace(title="Backend Developer Intern", duration_years=0.5)],
    }
    candidate.update(overrides)
    return candidate


def recording_llm(prompts: list):
    def fake_llm(prompt, json_mode=False):
        prompts.append(prompt)
        n = len(prompts)
        return f"1. Question {n}?\n2. Question {n}?\n3. Question {n}?"
    return fake_llm


def stub_resume(monkeypatch):
    monkeypatch.setattr(
        interview_guide,
        "get_resume",
        lambda company_id, resume_id: SimpleNamespace(projects_text="Built an API.", experience_text="Wrote tests."),
    )


def test_feedback_cache_key(monkeypatch):
    prompts = []
    monkeypatch.setattr(feedback, "call_llm", recording_llm(prompts))
    monkeypatch.setattr(feedback, "_feedback_cache", {})
    candidate = make_candidate()

    first = feedback.generate_feedback("c1", "jdA", JD, candidate)
    again = feedback.generate_feedback("c1", "jdA", JD, candidate)
    other_jd = feedback.generate_feedback("c1", "jdB", JD, candidate)
    other_company = feedback.generate_feedback("c2", "jdA", JD, candidate)

    assert again == first
    assert other_jd != first
    assert other_company != first
    assert len(prompts) == 3


def test_interview_guide_cache_key(monkeypatch):
    prompts = []
    monkeypatch.setattr(interview_guide, "call_llm", recording_llm(prompts))
    monkeypatch.setattr(interview_guide, "_guide_cache", {})
    stub_resume(monkeypatch)
    candidate = make_candidate()

    first = interview_guide.generate_interview_guide("c1", "jdA", JD, candidate)
    again = interview_guide.generate_interview_guide("c1", "jdA", JD, candidate)
    other_jd = interview_guide.generate_interview_guide("c1", "jdB", JD, candidate)

    assert again == first
    assert other_jd != first
    assert len(prompts) == 2


def test_prompts_never_contain_candidate_names(monkeypatch):
    prompts = []
    fake_llm = recording_llm(prompts)
    monkeypatch.setattr(feedback, "call_llm", fake_llm)
    monkeypatch.setattr(feedback, "_feedback_cache", {})
    monkeypatch.setattr(interview_guide, "call_llm", fake_llm)
    monkeypatch.setattr(interview_guide, "_guide_cache", {})
    monkeypatch.setattr(handlers, "call_llm", fake_llm)
    stub_resume(monkeypatch)

    priya = make_candidate()
    arjun = make_candidate(resume_id="r2", candidate_id="cand-2", candidate_name="Arjun Mehta", label="Partial")
    state = {"company_id": "c1", "jd_hash": "jdA", "jd": JD, "candidates": [priya, arjun], "errors": []}

    feedback.generate_feedback("c1", "jdA", JD, priya)
    interview_guide.generate_interview_guide("c1", "jdA", JD, priya)
    handlers.compare({**state, "query": "compare Priya and Arjun"})
    handlers.general({**state, "query": "is Priya stronger than Arjun?"})

    assert len(prompts) == 4
    for prompt in prompts:
        for name in ("Priya", "Sharma", "Arjun", "Mehta"):
            assert name not in prompt

def test_feedback_prompt_carries_label_but_no_scores(monkeypatch):
    prompts = []
    monkeypatch.setattr(feedback, "call_llm", recording_llm(prompts))
    monkeypatch.setattr(feedback, "_feedback_cache", {})

    feedback.generate_feedback("c1", "jdA", JD, make_candidate(label="Weak"))

    assert "Match label: Weak" in prompts[0]
    assert "0.731" not in prompts[0]
    assert "0.652" not in prompts[0]


def test_interview_guide_refusal_is_not_cached(monkeypatch):
    monkeypatch.setattr(
        interview_guide,
        "call_llm",
        lambda prompt, json_mode=False: "I'm sorry, but I can't help with that.",
    )
    monkeypatch.setattr(interview_guide, "_guide_cache", {})
    stub_resume(monkeypatch)

    with pytest.raises(interview_guide.GuideUnavailable):
        interview_guide.generate_interview_guide("c1", "jdA", JD, make_candidate())

    assert interview_guide._guide_cache == {}

def test_same_candidate_with_two_resumes_resolves_to_best_ranked():
    first = make_candidate(resume_id="r1", candidate_id="cand-1")
    other = make_candidate(resume_id="r2", candidate_id="cand-2", candidate_name="Arjun Mehta")
    second = make_candidate(resume_id="r9", candidate_id="cand-1")

    matches = handlers.find_candidates_in_query("why is Priya Sharma ranked first?", [first, other, second])

    assert [m["resume_id"] for m in matches] == ["r1"]


def test_name_labels_survive_non_breaking_spaces(monkeypatch):
    priya = make_candidate()
    arjun = make_candidate(resume_id="r2", candidate_id="cand-2", candidate_name="Arjun Mehta")
    state = {"company_id": "c1", "jd_hash": "jdA", "jd": JD, "candidates": [priya, arjun], "errors": []}

    monkeypatch.setattr(handlers, "call_llm", lambda prompt, json_mode=False: "Candidate\u00a01 is stronger than Candidate\u202f2.")
    general = handlers.general({**state, "query": "who is stronger?"})
    assert general["response_text"] == "Priya Sharma is stronger than Arjun Mehta."

    monkeypatch.setattr(handlers, "call_llm", lambda prompt, json_mode=False: "Candidate\u00a0A leads Candidate\u202fB.")
    compare = handlers.compare({**state, "query": "compare Priya and Arjun"})
    assert compare["response_text"] == "Priya Sharma leads Arjun Mehta."


def test_general_prompt_has_exact_counts_for_distinct_candidates(monkeypatch):
    prompts = []
    monkeypatch.setattr(handlers, "call_llm", recording_llm(prompts))
    holder = make_candidate(resume_id="r1", candidate_id="cand-1", matched_required=["python"], missing_required=[])
    duplicate = make_candidate(resume_id="r9", candidate_id="cand-1", matched_required=["python"], missing_required=[])
    lacking = make_candidate(
        resume_id="r2", candidate_id="cand-2", candidate_name="Arjun Mehta", label="Partial",
        matched_required=[], missing_required=["python"],
    )
    state = {"company_id": "c1", "jd_hash": "jdA", "jd": JD, "candidates": [holder, duplicate, lacking], "errors": []}

    handlers.general({**state, "query": "which skills are missing?"})

    assert "2 candidates in total." in prompts[0]
    assert "python (missing for 1 of 2)" in prompts[0]


def test_feedback_is_regenerated_when_the_label_changes(monkeypatch):
    prompts = []
    monkeypatch.setattr(feedback, "call_llm", recording_llm(prompts))
    monkeypatch.setattr(feedback, "_feedback_cache", {})

    feedback.generate_feedback("c1", "jdA", JD, make_candidate(label="Strong"))
    feedback.generate_feedback("c1", "jdA", JD, make_candidate(label="Good"))
    assert len(prompts) == 2


def test_empty_ai_reply_gives_a_friendly_chat_answer(monkeypatch):
    from src.agents.llm_client import AIServiceError

    def empty_reply(prompt, json_mode=False):
        raise AIServiceError("The model returned an empty reply")

    monkeypatch.setattr(handlers, "call_llm", empty_reply)
    result = handlers.general(make_state("how many candidates know python?"))
    assert result["response_text"] == "I couldn't answer that right now. Please try again."


def test_empty_model_reply_is_an_ai_error(monkeypatch):
    from src.agents import llm_client

    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])
    monkeypatch.setattr(llm_client.client.chat.completions, "create", lambda **kw: reply)
    with pytest.raises(llm_client.AIServiceError):
        llm_client.call_llm("hi")
