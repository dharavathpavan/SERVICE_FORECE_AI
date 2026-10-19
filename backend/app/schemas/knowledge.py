from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: str
    organization_id: str
    knowledge_base_id: str
    title: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    metadata_json: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class SearchQuery(BaseModel):
    query: str
    top_k: int = 4
    knowledge_base_id: Optional[str] = None


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    similarity: float
