from app.rag import KnowledgeBase


def test_knowledge_base_loads_casearium_docs() -> None:
    kb = KnowledgeBase("docs/Кейсариум")

    assert len(kb.documents) >= 100
    hits = kb.search("не приходит SMS код подтверждения", limit=3)

    assert hits
    assert any("SMS" in hit["title"] or "SMS" in hit["content"] for hit in hits)
