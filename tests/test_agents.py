from src.agents.conversation.router import classify_intent


def test_classify_intent_keyword_matches():
    assert classify_intent({"query": "show me the top 5"})["intent"] == "show_top_n"
    assert classify_intent({"query": "who knows react"})["intent"] == "filter_by_skill"
    assert classify_intent({"query": "compare Priya and Raj"})["intent"] == "compare"
    assert classify_intent({"query": "what's the weather"})["intent"] == "general"