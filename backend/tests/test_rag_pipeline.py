import io
from app.services.rag import chunk_text, generate_embedding, cosine_similarity


def test_chunking_and_embedding_math():
    text = "The quick brown fox jumps over the lazy dog. " * 30
    chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)
    assert len(chunks) > 1

    vec1 = generate_embedding("Apex Medical warranty covers parts for 3 years.")
    vec2 = generate_embedding("Apex Medical warranty covers parts for 3 years.")
    vec3 = generate_embedding("Italian pasta cooking recipe with olive oil.")

    assert len(vec1) == 256
    # Identical texts must have cosine similarity ~ 1.0
    sim_identical = cosine_similarity(vec1, vec2)
    assert sim_identical > 0.99

    # Unrelated texts must have substantially lower similarity
    sim_unrelated = cosine_similarity(vec1, vec3)
    assert sim_unrelated < sim_identical


def test_rag_upload_and_semantic_search(client):
    reg = client.post("/api/v1/auth/register", json={
        "email": "kb-admin@apexmed.com",
        "full_name": "KB Manager",
        "password": "Password123!",
        "organization_name": "Apex Med Global"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Knowledge Base
    kb_resp = client.post("/api/v1/knowledge-bases", headers=headers, json={
        "name": "Clinical FAQs & Policies",
        "description": "Hospital customer care documentation"
    })
    assert kb_resp.status_code == 201
    kb_id = kb_resp.json()["id"]

    # 2. Upload text document
    sample_doc_text = """
    Apex Care Return and Exchange Policy:
    Customers can return unopened surgical kits within 30 calendar days of delivery for a 100% full refund.
    All diagnostic monitors include a standard 3-year manufacturer hardware warranty.
    For technical support emergency escalations, dial extension 409 or request a senior medical engineer.
    """
    file_bytes = io.BytesIO(sample_doc_text.encode("utf-8"))
    upload_resp = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        headers=headers,
        files={"file": ("warranty_policy.txt", file_bytes, "text/plain")}
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["status"] == "ready"
    assert upload_resp.json()["chunk_count"] > 0

    # 3. Perform Semantic Search
    search_resp = client.post("/api/v1/knowledge-bases/search", headers=headers, json={
        "query": "How long is the manufacturer warranty on surgical diagnostic monitors?",
        "knowledge_base_id": kb_id,
        "top_k": 2
    })
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) > 0
    assert "warranty" in results[0]["content"].lower()

    # 4. Agent Playground Turn
    agent_resp = client.post("/api/v1/agents", headers=headers, json={
        "name": "Apex Support Assistant",
        "purpose": "Customer Care",
        "language": "en-US",
        "voice": "Puck",
        "greeting": "Thank you for contacting Apex Medical. How can I help you?",
        "system_prompt": "You are a courteous clinical customer care agent.",
        "fallback_behavior": "Transfer to human specialist."
    })
    agent_id = agent_resp.json()["id"]

    test_resp = client.post(f"/api/v1/agents/{agent_id}/test", headers=headers, json={
        "message": "What is the warranty policy on diagnostic monitors?",
        "knowledge_base_ids": [kb_id]
    })
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert test_data["simulated_speech_ready"] is True
    assert len(test_data["retrieved_sources"]) > 0
    assert "warranty" in test_data["reply"].lower()
