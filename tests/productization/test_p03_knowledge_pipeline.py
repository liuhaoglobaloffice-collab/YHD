from pathlib import Path


def test_knowledge_document_contract_exists():
    root = Path(__file__).resolve().parents[2]
    route = root / "src" / "api" / "routes" / "productization.py"
    knowledge_doc = root / "src" / "knowledge" / "documents.py"

    assert route.exists(), "Missing productization route"
    assert knowledge_doc.exists(), "Missing knowledge document implementation"

    route_text = route.read_text(encoding="utf-8")
    knowledge_text = knowledge_doc.read_text(encoding="utf-8")

    assert "DocumentMetadata" in route_text
    assert "DocumentStatus" in route_text
    assert "class DocumentService" in knowledge_text
    assert "DocumentMetadata" in knowledge_text
