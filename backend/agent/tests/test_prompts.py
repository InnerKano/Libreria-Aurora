from agent.prompts import build_llm_prompt
from agent.retrieval import RetrievalResult


def test_build_llm_prompt_includes_query_and_message():
    retrieval = RetrievalResult(
        query="realismo mágico",
        k=3,
        source="vector",
        degraded=False,
        results=[{"libro_id": 1, "titulo": "Cien años de soledad"}],
        warnings=[],
    )

    prompt = build_llm_prompt(user_message="Busco novelas", retrieval=retrieval)

    assert "Busco novelas" in prompt
    assert "realismo mágico" in prompt
    assert "Cien años de soledad" in prompt
