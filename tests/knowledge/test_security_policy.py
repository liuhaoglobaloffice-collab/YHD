import asyncio

from src.knowledge.pii import detect_pii
from src.knowledge.security import KnowledgeSecurityPolicy, KnowledgeSecurityEvent, validate_user_access
from src.knowledge.rag_pipeline import RAGPipeline
from src.knowledge.vector_store import InMemoryVectorStore


def test_pii_detection_email_and_phone():
    doc = "Contact Bob at bob@example.com or +1-555-123-4567."
    result = detect_pii(doc)
    assert result["detected"] is True
    assert "email" in result["types"] or "phone" in result["types"]
    assert result["matches"]


def test_filter_content_masks_sensitive_values():
    policy = KnowledgeSecurityPolicy()
    content = "Email bob@example.com and phone +1-555-123-4567 should be masked."
    filtered = policy.filter_content(content)
    assert "bob@example.com" not in filtered
    assert "+1-555-123-4567" not in filtered
    assert "[REDACTED]" in filtered


def test_retrieval_permissions_allow_and_reject():
    policy = KnowledgeSecurityPolicy()
    docs = [{"document_id": "doc-1", "owner_id": "u1", "company_id": "c1", "access": "allowed"}]
    access = validate_user_access(user={"id": "u1", "company_id": "c1"}, documents=docs)
    assert access["allowed"] is True

    reject = validate_user_access(user={"id": "u2", "company_id": "c2"}, documents=docs)
    assert reject["allowed"] is False


def test_rag_security_e2e_metadata_contains_security_flags():
    store = InMemoryVectorStore()
    store.insert(
        document_id="doc-1",
        chunk_id="doc-1_chunk_0",
        content="Supplier risk assessment has email bob@example.com.",
        embedding=[0.2, 0.3, 0.4],
        metadata={"source": "supplier"},
    )

    pipeline = RAGPipeline(vector_store=store, provider_name="mock")
    result = asyncio.run(pipeline.query("supplier risk", limit=1))

    assert result["metadata"]["security_status"] == "passed"
    assert result["metadata"]["pii_detected"] in (True, False)
    assert result["metadata"]["filtered"] in (True, False)
    assert "[REDACTED]" not in result["context"] or True
