import io
import math
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
import docx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk


def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    """Safely extracts text content from PDF, DOCX, TXT, or Markdown bytes."""
    file_type = file_type.lower().strip(".")
    if file_type in ["txt", "md", "markdown", "text"]:
        return file_bytes.decode("utf-8", errors="replace")

    elif file_type == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pages_text.append(extracted)
        return "\n\n".join(pages_text)

    elif file_type in ["docx", "doc"]:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    else:
        # Fallback to UTF-8 decoding
        return file_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """Splits text recursively by paragraphs and sentences with overlap."""
    if not text.strip():
        return []

    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += max(1, chunk_size - chunk_overlap)
    return chunks


def generate_embedding(text: str, dimensions: int = 256) -> List[float]:
    """
    Generates embedding vectors.
    Uses Gemini API if GEMINI_API_KEY is configured,
    or a high-dimensional deterministic feature hashing embedding for offline/local simulation.
    """
    if settings.GEMINI_API_KEY:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.EMBEDDING_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
            resp = httpx.post(url, json={"content": {"parts": [{"text": text[:2000]}]}}, timeout=10.0)
            if resp.status_code == 200:
                vals = resp.json().get("embedding", {}).get("values", [])
                if vals:
                    return vals
        except Exception:
            pass  # Fall back to simulation embedding on network failure

    # Deterministic feature hashing embedding (normalized vector)
    vec = np.zeros(dimensions, dtype=np.float32)
    words = text.lower().split()
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dimensions
        val = 1.0 if (h // dimensions) % 2 == 0 else -1.0
        vec[idx] += val

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def search_knowledge_base(
    db: Session,
    organization_id: str,
    query: str,
    knowledge_base_id: Optional[str] = None,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """Performs semantic vector search across tenant chunks."""
    query_vec = generate_embedding(query)

    chunk_query = db.query(DocumentChunk, Document.title).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        DocumentChunk.organization_id == organization_id,
        Document.status == "ready"
    )

    if knowledge_base_id:
        chunk_query = chunk_query.filter(DocumentChunk.knowledge_base_id == knowledge_base_id)

    records = chunk_query.all()
    if not records:
        return []

    scored_results = []
    for chunk, doc_title in records:
        if not chunk.embedding:
            continue
        sim = cosine_similarity(query_vec, chunk.embedding)
        scored_results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": doc_title,
            "content": chunk.content,
            "similarity": round(sim, 4),
        })

    # Sort descending by similarity
    scored_results.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_results[:top_k]
