import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  UploadCloud,
  FileText,
  Search,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const KnowledgeDetailPage: React.FC = () => {
  const { knowledgeBaseId } = useParams<{ knowledgeBaseId: string }>();
  const navigate = useNavigate();

  const [kb, setKb] = useState<any | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Search Tester
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const fetchDetails = async () => {
    try {
      const [kbRes, docsRes] = await Promise.all([
        apiRequest<any>(`/knowledge-bases/${knowledgeBaseId}`),
        apiRequest<any[]>(`/knowledge-bases/${knowledgeBaseId}/documents`),
      ]);
      setKb(kbRes);
      setDocuments(docsRes);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (knowledgeBaseId) fetchDetails();
  }, [knowledgeBaseId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('serviceforce_token');
      const orgId = localStorage.getItem('serviceforce_org_id');

      const response = await fetch(`/api/v1/knowledge-bases/${knowledgeBaseId}/documents/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          ...(orgId ? { 'X-Organization-Id': orgId } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Upload failed');
      }

      await fetchDetails();
      e.target.value = '';
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (docId: string, title: string) => {
    if (!confirm(`Delete document "${title}" and its vector chunks?`)) return;
    try {
      await apiRequest(`/knowledge-bases/documents/${docId}`, { method: 'DELETE' });
      fetchDetails();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await apiRequest<any[]>('/knowledge-bases/search', {
        method: 'POST',
        body: JSON.stringify({
          query: searchQuery,
          knowledge_base_id: knowledgeBaseId,
          top_k: 3,
        }),
      });
      setSearchResults(res);
    } catch (err: any) {
      alert(err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/app/knowledge')}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-navy-950">{kb?.name || 'Knowledge Base'}</h1>
              <Badge variant="brand">{documents.length} Documents</Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{kb?.description || 'Semantic document collection'}</p>
          </div>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="bg-white p-6 rounded-2xl border-2 border-dashed border-slate-200 hover:border-brand-400 transition-colors text-center">
        <UploadCloud className="h-10 w-10 text-brand-500 mx-auto mb-2" />
        <h3 className="text-xs font-bold text-slate-800">Upload Reference Document for Vector Indexing</h3>
        <p className="text-[11px] text-slate-500 mt-0.5 mb-4">
          Supported formats: PDF, Microsoft Word (.docx), Plain Text (.txt), and Markdown (.md) up to 15MB.
        </p>

        {uploadError && (
          <div className="mb-4 max-w-md mx-auto p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center space-x-1.5">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        <label className="inline-block">
          <Button size="sm" isLoading={isUploading} className="pointer-events-none">
            <span>Select File to Ingest</span>
          </Button>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt,.md"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="hidden"
          />
        </label>
      </div>

      {/* Semantic Search Tester */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div>
          <h3 className="text-sm font-bold text-navy-950 flex items-center space-x-2">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <span>Semantic Vector Retrieval Tester</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Test cosine similarity search against indexed document chunks in this knowledge base.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Ask a question or enter keywords (e.g. 'What is the return policy?')..."
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <Button type="submit" size="sm" isLoading={isSearching}>
            Search Vectors
          </Button>
        </form>

        {searchResults.length > 0 && (
          <div className="space-y-2 pt-2">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Top Semantic Matches:
            </span>
            {searchResults.map((match, i) => (
              <div key={i} className="p-3 bg-purple-50/50 border border-purple-200 rounded-xl text-xs space-y-1">
                <div className="flex items-center justify-between text-purple-900 font-semibold">
                  <span>{match.document_title}</span>
                  <span className="font-mono text-[11px] bg-purple-200/60 px-1.5 py-0.5 rounded">
                    Score: {match.similarity}
                  </span>
                </div>
                <p className="text-slate-700 leading-relaxed text-[11px]">{match.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-navy-950">Indexed Documents</h3>
          <span className="text-xs text-slate-500">{documents.length} files</span>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {documents.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <FileText className="h-8 w-8 mx-auto mb-2 text-slate-300" />
              <p>No documents uploaded yet.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="p-2 rounded-lg bg-slate-100 text-slate-600">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="truncate">
                    <p className="font-semibold text-slate-900 truncate">{doc.title}</p>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span>•</span>
                      <span>{doc.chunk_count} vector chunks</span>
                      <span>•</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <Badge variant={doc.status === 'ready' ? 'success' : doc.status === 'processing' ? 'warning' : 'danger'}>
                    {doc.status}
                  </Badge>
                  <button
                    onClick={() => handleDeleteDocument(doc.id, doc.title)}
                    className="p-1.5 text-slate-400 hover:text-red-600 rounded transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
