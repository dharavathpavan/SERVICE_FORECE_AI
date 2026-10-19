from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentResponse,
    SearchQuery,
    SearchResult,
)
from app.services.rag import (
    extract_text_from_file,
    chunk_text,
    generate_embedding,
    search_knowledge_base,
)

router = APIRouter(prefix="/knowledge-bases", tags=["RAG Knowledge Bases"])


@router.get("", response_model=List[KnowledgeBaseResponse])
def list_knowledge_bases(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists all knowledge bases in the organization."""
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == ctx.organization_id).all()
    results = []
    for kb in kbs:
        doc_count = db.query(Document).filter(Document.knowledge_base_id == kb.id).count()
        results.append(KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=doc_count,
        ))
    return results


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    kb_in: KnowledgeBaseCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Creates a new knowledge base container."""
    kb = KnowledgeBase(
        organization_id=ctx.organization_id,
        name=kb_in.name,
        description=kb_in.description,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        document_count=0,
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    kb_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Retrieves knowledge base details."""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.organization_id == ctx.organization_id
    ).first()

    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    doc_count = db.query(Document).filter(Document.knowledge_base_id == kb.id).count()
    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        document_count=doc_count,
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    kb_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Deletes a knowledge base and all associated documents and vector chunks."""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.organization_id == ctx.organization_id
    ).first()

    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    db.delete(kb)
    db.commit()
    return None


@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    kb_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists all documents within a knowledge base."""
    # Verify KB belongs to tenant
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.organization_id == ctx.organization_id
    ).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    return db.query(Document).filter(
        Document.knowledge_base_id == kb_id,
        Document.organization_id == ctx.organization_id
    ).all()


@router.post("/{kb_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Uploads, extracts, chunks, and vector-indexes a document (PDF, TXT, MD, DOCX).
    Enforces tenant scoping and file validation.
    """
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.organization_id == ctx.organization_id
    ).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    filename = file.filename or "uploaded_document.txt"
    ext = filename.split(".")[-1].lower()
    allowed_exts = ["txt", "md", "markdown", "pdf", "docx"]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type .{ext}. Allowed types: {', '.join(allowed_exts)}"
        )

    file_bytes = await file.read()
    max_size = 15 * 1024 * 1024  # 15MB
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 15MB limit")

    # Create Document record
    doc = Document(
        organization_id=ctx.organization_id,
        knowledge_base_id=kb.id,
        title=filename,
        file_type=ext,
        file_size=len(file_bytes),
        status="processing",
    )
    db.add(doc)
    db.flush()

    try:
        # Extract text
        extracted_text = extract_text_from_file(file_bytes, ext)
        if not extracted_text.strip():
            doc.status = "failed"
            doc.error_message = "No readable text extracted from document"
            db.commit()
            return doc

        # Chunk text
        chunks = chunk_text(extracted_text, chunk_size=200, chunk_overlap=30)
        for idx, chunk_str in enumerate(chunks):
            embedding_vec = generate_embedding(chunk_str)
            chunk_record = DocumentChunk(
                organization_id=ctx.organization_id,
                knowledge_base_id=kb.id,
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_str,
                embedding=embedding_vec,
                metadata_json={"title": filename, "chunk_index": idx, "char_count": len(chunk_str)},
            )
            db.add(chunk_record)

        doc.chunk_count = len(chunks)
        doc.status = "ready"

        audit = AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            action="document.indexed",
            entity_type="document",
            entity_id=doc.id,
            details={"title": filename, "chunks": doc.chunk_count}
        )
        db.add(audit)
        db.commit()
        db.refresh(doc)
        return doc

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        db.commit()
        db.refresh(doc)
        return doc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Deletes a document and all of its vector chunks."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == ctx.organization_id
    ).first()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    db.delete(doc)
    db.commit()
    return None


@router.post("/search", response_model=List[SearchResult])
def search_knowledge(
    search_q: SearchQuery,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Semantic vector search across organization documents."""
    results = search_knowledge_base(
        db=db,
        organization_id=ctx.organization_id,
        query=search_q.query,
        knowledge_base_id=search_q.knowledge_base_id,
        top_k=search_q.top_k,
    )
    return results
